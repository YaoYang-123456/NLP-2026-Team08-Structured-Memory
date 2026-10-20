"""Prepare native calls offline, or materialize recorded real responses on a fresh copy."""
import argparse
from functools import partial
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from structmem_retrieve import UPSTREAM_REVISION, file_hash, load_points, read_json, summarize_memory


def run(bundle, sample_id, upstream, model_path, out, responses=None):
    revision = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    if revision != UPSTREAM_REVISION:
        raise ValueError("Upstream revision mismatch")
    changes = subprocess.check_output(["git", "-C", str(upstream), "status", "--porcelain", "--", "src"], text=True)
    if changes.strip():
        raise ValueError("Upstream source modified")
    out = Path(out).resolve()
    if out.exists():
        raise FileExistsError(out)
    handoff = read_json(bundle / "handoff.json")
    collection = handoff["conversations"][sample_id]["collection"]
    hashes = read_json(bundle / "files.sha256.json")
    for name, digest in hashes.items():
        source = (bundle / name).resolve()
        if not source.is_relative_to(bundle.resolve()) or file_hash(source) != digest:
            raise ValueError("Received bundle changed")
    recorded = []
    if responses is not None:
        for line in responses.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event["sample_id"] == sample_id:
                if (event["window_index"] != len(recorded) or event["status"] != "ok" or
                        event["simulated"] is not False or event["finish_reason"] != "stop" or
                        not isinstance(event["prediction"], str) or not event["prediction"].strip() or
                        not isinstance(event["usage"], dict)):
                    raise ValueError("Expected ordered successful real synthesis responses")
                recorded.append(event)
        if not recorded:
            raise ValueError("No real responses for this sample")
    out.mkdir(parents=True, exist_ok=False)
    shutil.copytree(bundle / sample_id / "qdrant", out / "events-private")
    sys.path.insert(0, str(upstream / "src"))
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from lightmem.memory.lightmem import LightMemory
    memory, calls = None, []
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "OPENAI_API_KEY": "offline-preflight-only"}), \
            patch("httpx.Client.send", side_effect=AssertionError("Network forbidden during offline synthesis preparation")):
        try:
            memory = LightMemory.from_config({
                "pre_compress": False, "topic_segment": False, "messages_use": "user_only",
                "metadata_generate": True, "text_summary": True, "extraction_mode": "event",
                "memory_manager": {"model_name": "openai", "configs": {
                    "model": "deepseek-flash", "api_key": "offline-preflight-only",
                    "openai_base_url": "http://127.0.0.1:9"}},
                "index_strategy": "embedding", "retrieve_strategy": "embedding",
                "text_embedder": {"model_name": "huggingface", "configs": {
                    "model": str(model_path.resolve()), "embedding_dims": 384,
                    "model_kwargs": {"device": "cpu", "local_files_only": True}}},
                "embedding_retriever": {"model_name": "qdrant", "configs": {
                    "collection_name": collection, "embedding_model_dims": 384,
                    "path": str(out / "events-private"), "on_disk": True}},
                "summary_retriever": {"model_name": "qdrant", "configs": {
                    "collection_name": sample_id.replace("-", "_") + "_summary",
                    "embedding_model_dims": 384,
                    "path": str(out / ("summaries" if responses is not None else "SYNTHETIC-summaries")), "on_disk": True}},
                "update": "offline", "logging": {"level": "WARNING", "file_enabled": False}})
            memory.manager.client.close()
            memory.text_embedder.model.encode = partial(memory.text_embedder.model.encode, normalize_embeddings=True)

            def capture(messages, **kwargs):
                request = {"model": "deepseek-flash", "messages": messages,
                           "thinking": {"type": "disabled"}, "stream": False,
                           "temperature": 0, "top_p": 1, "max_tokens": 8192}
                if responses is not None:
                    position = len(calls)
                    if position >= len(recorded) or recorded[position]["request"] != request:
                        raise ValueError("Recorded request differs from the freshly reconstructed native prompt")
                    event = recorded[position]
                    calls.append(event)
                    return event["prediction"], event["usage"]
                call = {"sample_id": sample_id, "window_index": len(calls), "stage": "offline_synthesis_preparation",
                        "proposed_request": request,
                        "real_request_sent": False, "usage": None}
                calls.append(call)
                with (out / "proposed-calls.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
                    stream.write(json.dumps(call, ensure_ascii=False) + "\n")
                return "SYNTHETIC OFFLINE PLACEHOLDER: no summarization model was called.", {}

            memory.manager.generate_response = capture
            result = summarize_memory(memory)
            points = memory.summary_retriever.get_all(with_vectors=True, with_payload=True)
            if len(points) != len(calls) or (responses is None and any(
                    "SYNTHETIC OFFLINE PLACEHOLDER" not in p["payload"]["summary"] for p in points)):
                raise ValueError("Unexpected offline synthesis output")
            if responses is not None and len(calls) != len(recorded):
                raise ValueError("Not all real responses were used")
            report = {"status": "real_native_synthesis_materialized" if responses is not None else "offline_native_synthesis_prepared",
                      "sample_id": sample_id,
                      "upstream_revision": revision, "time_window": 3600, "top_k_seeds": 15,
                      "retrieval_scope": "global", "process_all": True, "synthetic": responses is None,
                      "covered_event_count": sum(p["payload"]["entry_count"] for p in points),
                      "actual_api_calls_in_this_process": 0, "accuracy": None,
                      "code_sha256": file_hash(Path(__file__)),
                      "official_summary_result": result}
            if responses is None:
                report.update(proposed_calls=len(calls), placeholder_summaries=len(points), actual_api_calls=0,
                              usage=None, proposal_sha256=file_hash(out / "proposed-calls.jsonl"))
            else:
                events = memory.embedding_retriever.get_all(with_vectors=True, with_payload=True)
                event_ids = {str(p["id"]) for p in events}
                covered = [str(pid) for p in points for pid in p["payload"]["covered_entry_ids"]]
                if len(covered) != len(set(covered)) or set(covered) != event_ids or any(
                        str(pid) not in event_ids for p in points for pid in p["payload"].get("seed_entry_ids", [])):
                    raise ValueError("Real summaries do not cover exactly the received events")
                exports = {}
                for kind, values in (("event", events), ("synthesis", points)):
                    path = out / ("events.json" if kind == "event" else "summaries.json")
                    path.write_text(json.dumps(values, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
                    load_points(path, kind)
                    exports[kind] = {"path": str(path.resolve()), "sha256": file_hash(path), "points": len(values)}
                report.update(recorded_real_api_calls=len(calls), real_summaries=len(points),
                              responses_sha256=file_hash(responses), exports=exports,
                              usage={key: sum(event["usage"][key] for event in calls)
                                     for key in ("prompt_tokens", "completion_tokens", "total_tokens")})
            with (out / "preparation.json").open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        finally:
            if memory is not None:
                memory.embedding_retriever.client.close()
                memory.summary_retriever.client.close()
    if any(file_hash(bundle / name) != digest for name, digest in hashes.items()):
        raise ValueError("Received bundle changed during offline preparation")
    return {key: value for key, value in report.items() if key != "official_summary_result"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--sample-id", choices=("conv-48", "conv-42", "conv-41"), required=True)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--responses", type=Path, help="Replay successful real call records; no new API calls")
    args = parser.parse_args()
    print(json.dumps(run(args.bundle, args.sample_id, args.upstream, args.model_path, args.out, args.responses), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
