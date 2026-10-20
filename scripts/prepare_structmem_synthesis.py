"""Capture native synthesis calls on a private copy, using explicitly synthetic replies only."""
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
from structmem_retrieve import UPSTREAM_REVISION, file_hash, read_json, summarize_memory


def run(bundle, sample_id, upstream, model_path, out):
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
                    "embedding_model_dims": 384, "path": str(out / "SYNTHETIC-summaries"), "on_disk": True}},
                "update": "offline", "logging": {"level": "WARNING", "file_enabled": False}})
            memory.manager.client.close()
            memory.text_embedder.model.encode = partial(memory.text_embedder.model.encode, normalize_embeddings=True)

            def capture(messages, **kwargs):
                call = {"sample_id": sample_id, "window_index": len(calls), "stage": "offline_synthesis_preparation",
                        "proposed_request": {"model": "deepseek-flash", "messages": messages,
                                             "thinking": {"type": "disabled"}, "stream": False,
                                             "temperature": 0, "top_p": 1, "max_tokens": 8192},
                        "real_request_sent": False, "usage": None}
                calls.append(call)
                with (out / "proposed-calls.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
                    stream.write(json.dumps(call, ensure_ascii=False) + "\n")
                return "SYNTHETIC OFFLINE PLACEHOLDER: no summarization model was called.", {}

            memory.manager.generate_response = capture
            result = summarize_memory(memory)
            points = memory.summary_retriever.get_all(with_vectors=True, with_payload=True)
            if len(points) != len(calls) or any("SYNTHETIC OFFLINE PLACEHOLDER" not in p["payload"]["summary"] for p in points):
                raise ValueError("Unexpected offline synthesis output")
            report = {"status": "offline_native_synthesis_prepared", "sample_id": sample_id,
                      "upstream_revision": revision, "time_window": 3600, "top_k_seeds": 15,
                      "retrieval_scope": "global", "process_all": True, "synthetic": True,
                      "proposed_calls": len(calls), "placeholder_summaries": len(points),
                      "covered_event_count": sum(p["payload"]["entry_count"] for p in points),
                      "actual_api_calls": 0, "usage": None, "accuracy": None,
                      "proposal_sha256": file_hash(out / "proposed-calls.jsonl"),
                      "code_sha256": file_hash(Path(__file__)),
                      "official_summary_result": result}
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
    args = parser.parse_args()
    print(json.dumps(run(args.bundle, args.sample_id, args.upstream, args.model_path, args.out), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
