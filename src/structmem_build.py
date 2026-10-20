"""C-task smoke builder: fixed upstream extraction with explicit provenance.

This profile disables compression/topic segmentation to validate a complete
session before integrating the team's final preprocessing configuration.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import math
from functools import partial
from datetime import datetime

UPSTREAM_REV = "8449d574df6bae1bdf3314a1564da65e2f37e046"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare_session(data, sample_id, session_number):
    """Allowlist conversation fields; QA/answers never enter the build input."""
    matches = [s for s in data if s.get("sample_id") == sample_id]
    if len(matches) != 1:
        raise ValueError("Expected exactly one matching sample_id")
    conv = matches[0]["conversation"]
    session_key = f"session_{session_number}"
    raw_time = conv[f"{session_key}_date_time"]
    try:
        timestamp = datetime.strptime(raw_time.strip("()"), "%I:%M %p on %d %B, %Y").isoformat()
    except ValueError:
        timestamp = datetime.fromisoformat(raw_time).isoformat()
    names = [conv["speaker_a"], conv["speaker_b"]]
    if names[0] == names[1]:
        raise ValueError("Speakers must be distinct")
    messages = []
    seen = set()
    for turn in conv[session_key]:
        message_id = turn["dia_id"]
        if not isinstance(message_id, str) or not message_id or message_id in seen:
            raise ValueError("Missing or duplicate dia_id")
        seen.add(message_id)
        if turn["speaker"] not in names or not isinstance(turn["text"], str) or not turn["text"].strip():
            raise ValueError("Invalid speaker or empty message")
        content = turn["text"]
        if turn.get("blip_caption"):
            content += f" (image description: {turn['blip_caption']})"
        messages.append({"message_id": message_id, "content": content,
                         "speaker_name": turn["speaker"],
                         "speaker_id": "speaker_a" if turn["speaker"] == names[0] else "speaker_b"})
    if not messages:
        raise ValueError("Empty session")
    return {"sample_id": sample_id, "session_id": session_key,
            "original_timestamp": raw_time, "timestamp": timestamp, "messages": messages}


def validate_prepared(value):
    if set(value) != {"sample_id", "session_id", "original_timestamp", "timestamp", "messages"}:
        raise ValueError("Unexpected build-input fields; prepare conversation-only input first")
    datetime.fromisoformat(value["timestamp"])
    if not value["messages"]:
        raise ValueError("Empty session")
    ids = set()
    for msg in value["messages"]:
        if set(msg) != {"message_id", "content", "speaker_name", "speaker_id"}:
            raise ValueError("Unexpected message fields")
        if not all(isinstance(v, str) and v.strip() for v in msg.values()):
            raise ValueError("Empty or invalid message field")
        if msg["message_id"] in ids:
            raise ValueError("Duplicate message ID")
        ids.add(msg["message_id"])


def entry_text(entry):
    return entry.get("fact") or entry.get("relation")


def validate_extraction(content, message_count):
    parsed = json.loads(content)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("data"), list):
        raise ValueError("Extraction must contain a data list")
    for item in parsed["data"]:
        if not isinstance(item, dict):
            raise ValueError("Invalid extracted entry")
        sid = item.get("source_id")
        if type(sid) is not int or not 0 <= sid < message_count:
            raise ValueError("Invalid source_id; refusing upstream's silent correction")
        text = entry_text(item)
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Missing extracted fact/relation")
    return parsed["data"]


def upstream_check(root):
    root = Path(root).resolve()
    revision = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if revision != UPSTREAM_REV:
        raise ValueError("Upstream revision mismatch")
    changes = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain", "--", "src", "experiments/locomo/prompts.py"], text=True)
    if changes.strip():
        raise ValueError("Upstream source/prompts have local modifications")
    return root


def load_key(path):
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key and Path(path).is_file():
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("\"'")
    if not key:
        raise ValueError("Set DEEPSEEK_API_KEY or provide an ignored local .env file")
    if os.environ.get("OPENROUTER_API_KEY"):
        raise ValueError("Unset OPENROUTER_API_KEY to prevent upstream routing changes")
    return key


def build(args):
    prepared = read_json(args.input)
    validate_prepared(prepared)
    config = read_json(args.config)
    if config["model"] != "deepseek-flash" or config["embedding_dims"] != 384:
        raise ValueError("Smoke profile requires deepseek-flash and a 384-dimensional embedder")
    embedding_path = Path(args.embedding_model).resolve()
    if not embedding_path.is_dir():
        raise ValueError("Provide an existing local sentence-transformers embedding model directory")
    root = upstream_check(args.upstream)
    key = "replay-no-network" if args.replay else load_key(args.env_file)
    sys.path.insert(0, str(root / "src"))
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from lightmem.memory.lightmem import LightMemory
    import lightmem.memory.lightmem as upstream_memory
    from openai import OpenAI
    from qdrant_client import QdrantClient
    import tiktoken
    upstream_memory.GLOBAL_TOPIC_IDX = args.topic_id

    # Bound the smoke input before any paid request; never silently truncate it.
    tokenizer = tiktoken.get_encoding("o200k_base")
    if sum(len(tokenizer.encode(m["content"])) for m in prepared["messages"]) > config["max_input_tokens"]:
        raise ValueError("Session exceeds smoke input cap; choose another whole session")
    prompt_path = root / "experiments/locomo/prompts.py"
    spec = importlib.util.spec_from_file_location("structmem_locomo_prompts", prompt_path)
    prompts_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prompts_module)
    prompts = {"factual": prompts_module.LoCoMo_Event_Binding_factual,
               "relational": prompts_module.LoCoMo_Event_Binding_relational}
    replay_dir = Path(args.replay) if args.replay else None
    if replay_dir:
        replay_summary = read_json(replay_dir / "summary.json")
        if (replay_summary["input_sha256"] != sha256(args.input) or
                replay_summary["prompt_sha256"] != sha256(prompt_path) or
                replay_summary["upstream_revision"] != UPSTREAM_REV or
                replay_summary["config"] != config):
            raise ValueError("Replay input, prompts, upstream revision or config mismatch")
    destination = Path(args.output).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    collection = "structmem_events"
    store = destination / "qdrant"
    started = time.monotonic()
    calls, provenance = [], []
    summary = {"status": "running", "profile": config.get("profile", "session-smoke-no-compression-no-topic-segmentation"),
               "execution": "replay" if replay_dir else "live",
               "replay_source": str(replay_dir.resolve()) if replay_dir else None,
               "synthetic": args.synthetic, "upstream_revision": UPSTREAM_REV,
               "prompt_sha256": sha256(prompt_path), "input_sha256": sha256(args.input),
               "config": config, "embedding_model": str(embedding_path),
               "sample_id": prepared["sample_id"], "session_id": prepared["session_id"],
               "message_count": len(prepared["messages"]), "collection": collection,
               "api_calls": calls}
    write_json(destination / "input.json", prepared)
    write_json(destination / "summary.json", summary)
    memory = None
    client = OpenAI(api_key=key, base_url="https://api.deepseek.com/v1", timeout=90, max_retries=0)
    try:
        memory = LightMemory.from_config({
            "pre_compress": False, "topic_segment": False, "messages_use": "user_only",
            "metadata_generate": True, "text_summary": True, "extraction_mode": "event",
            "memory_manager": {"model_name": "openai", "configs": {
                "model": config["model"], "api_key": key,
                "openai_base_url": "https://api.deepseek.com/v1"}},
            "index_strategy": "embedding", "retrieve_strategy": "embedding",
            "text_embedder": {"model_name": "huggingface", "configs": {
                "model": str(embedding_path), "embedding_dims": 384,
                "model_kwargs": {"device": "cpu", "local_files_only": True}}},
            "embedding_retriever": {"model_name": "qdrant", "configs": {
                "collection_name": collection, "embedding_model_dims": 384,
                "path": str(store), "on_disk": True}}, "update": "offline"})
        # Replace the upstream client (which disables TLS verification) before calls.
        memory.manager.client.close()
        memory.manager.client = client
        model = memory.text_embedder.model
        if model.get_sentence_embedding_dimension() != config["embedding_dims"]:
            raise ValueError("Embedding dimensions differ from the frozen config")
        if config.get("normalize_embeddings", False):
            model.encode = partial(model.encode, normalize_embeddings=True)

        def generate(messages, response_format=None, **kwargs):
            kind = next((k for k, p in prompts.items() if p == messages[0]["content"]), None)
            if kind is None or len(calls) >= 2:
                raise RuntimeError("Unexpected prompt or extra API request")
            record = {"entry_type": kind, "status": "started"}
            calls.append(record)
            began = time.monotonic()
            try:
                if replay_dir:
                    from openai.types.chat import ChatCompletion
                    if read_json(replay_dir / f"{kind}-prompt.json") != messages:
                        raise ValueError("Replay prompt differs from current request")
                    response = ChatCompletion.model_validate(read_json(replay_dir / f"{kind}-response.json"))
                else:
                    response = client.chat.completions.create(
                        model=config["model"], messages=messages,
                        temperature=config["temperature"], top_p=config["top_p"],
                        max_tokens=config["max_tokens"], response_format={"type": "json_object"},
                        extra_body={"thinking": {"type": "disabled"}})
                record["new_model_request"] = not bool(replay_dir)
                record["actual_model"] = response.model
                record["request_id"] = response.id
                record["usage"] = response.usage.model_dump() if response.usage else None
                write_json(destination / f"{kind}-response.json", response.model_dump())
                write_json(destination / f"{kind}-prompt.json", messages)
                if response.choices[0].finish_reason != "stop":
                    raise ValueError("Incomplete model response")
                content = response.choices[0].message.content
                facts = validate_extraction(content, len(prepared["messages"]))
                provenance.extend({**f, "entry_type": kind} for f in facts)
                if record["usage"] is None:
                    raise ValueError("API usage missing")
                record["status"] = "success"
                return content, {k: getattr(response.usage, k) for k in
                                 ("prompt_tokens", "completion_tokens", "total_tokens")}
            except Exception as exc:
                # Provider exception strings may include request headers or secrets.
                record["status"] = "failed"
                record["error_type"] = type(exc).__name__
                raise RuntimeError(f"Extraction failed ({type(exc).__name__})") from None
            finally:
                record["elapsed_seconds"] = round(time.monotonic() - began, 3)
                write_json(destination / "summary.json", summary)

        memory.manager.generate_response = generate
        original_extract = memory.manager.meta_text_extract

        def checked_extract(*a, **kw):
            if len(kw["extract_list"]) != 1:
                raise ValueError("Smoke profile requires one complete-session extraction batch")
            result = original_extract(*a, **kw)
            if len(calls) != 2 or any(c["status"] != "success" for c in calls):
                raise RuntimeError("One or more extraction calls failed; no insertion allowed")
            if not provenance:
                raise ValueError("No extracted entries; not a successful build")
            return result

        memory.manager.meta_text_extract = checked_extract
        original_insert = memory.offline_update

        def insert_with_sources(entries, **kw):
            if len(entries) != len(provenance) or any(m.memory != entry_text(f) for m, f in zip(entries, provenance)):
                raise ValueError("Upstream conversion lost or reordered facts")
            if any(len(model.tokenizer.encode(entry.memory, add_special_tokens=True)) > model.max_seq_length for entry in entries):
                raise ValueError("Extracted memory exceeds embedding model length; refusing silent truncation")
            original_insert(entries, **kw)
            for entry, fact in zip(entries, provenance):
                source = prepared["messages"][fact["source_id"]]
                memory.embedding_retriever.client.set_payload(
                    collection_name=collection, points=[entry.id], wait=True,
                    payload={"entry_type": fact["entry_type"], "source_id": fact["source_id"],
                             "source_message_id": source["message_id"],
                             "source_key": f"{prepared['sample_id']}/{source['message_id']}",
                             "source_sample_id": prepared["sample_id"],
                             "source_session_id": prepared["session_id"]})

        memory.offline_update = insert_with_sources
        messages = []
        for message in prepared["messages"]:
            base = {k: message[k] for k in ("content", "speaker_id", "speaker_name")}
            base["time_stamp"] = prepared["timestamp"]
            messages.extend([{**base, "role": "user"}, {**base, "role": "assistant", "content": ""}])
        memory.add_memory(messages=messages, METADATA_GENERATE_PROMPT=prompts,
                          force_segment=True, force_extract=True)
        before = memory.embedding_retriever.get_all(with_vectors=True)
        memory.embedding_retriever.client.close()
        # Reopen from disk independently; a successful in-memory insert is insufficient.
        reopened = QdrantClient(path=str(store))
        try:
            points, offset = reopened.scroll(collection, limit=len(before) + 1, with_vectors=True)
            after = [p.model_dump() for p in points]
            if offset is not None or len(before) != len(after) or not after:
                raise RuntimeError("Persistent collection readback failed")
            expected = {p["id"]: (p["payload"], p["vector"]) for p in before}
            if any(expected[p["id"]] != (p["payload"], p["vector"]) for p in after):
                raise RuntimeError("Persisted payload/vector mismatch")
        finally:
            reopened.close()
        write_json(destination / "memories.json", after)
        if config.get("normalize_embeddings", False):
            if any(abs(math.sqrt(sum(x*x for x in point["vector"])) - 1) > 1e-5 for point in after):
                raise ValueError("Non-unit embedding vector")
        summary.update(status="success", entry_count=len(after),
                       entry_types={k: sum(p["payload"]["entry_type"] == k for p in after) for k in prompts},
                       disk_readback_verified=True, memories_sha256=sha256(destination / "memories.json"))
    except Exception as exc:
        summary.update(status="failed", error_type=type(exc).__name__)
        raise
    finally:
        if memory is not None:
            memory.embedding_retriever.client.close()
        client.close()
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        write_json(destination / "summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("status", "entry_count", "entry_types", "elapsed_seconds")}, ensure_ascii=False))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Prepare exactly one whole LoCoMo session without QA")
    prepare.add_argument("--data", required=True)
    prepare.add_argument("--sample-id", required=True)
    prepare.add_argument("--session", required=True, type=int)
    prepare.add_argument("--output", required=True)
    run = commands.add_parser("build", help="Make two real DeepSeek extraction calls and persist memory")
    run.add_argument("--input", required=True)
    run.add_argument("--config", required=True)
    run.add_argument("--upstream", required=True)
    run.add_argument("--embedding-model", required=True)
    run.add_argument("--output", required=True, help="New, nonexistent run directory")
    run.add_argument("--env-file", default=".env")
    run.add_argument("--synthetic", action="store_true", help="Mark self-authored input as synthetic")
    run.add_argument("--replay", help="Rebuild from saved raw responses with identical inputs/prompts; no API requests")
    run.add_argument("--topic-id", type=int, default=0, help="Stable session topic ID within a conversation")
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare_session(read_json(args.data), args.sample_id, args.session)
        validate_prepared(result)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise FileExistsError("Refusing to overwrite prepared input")
        write_json(output, result)
        print(f"Prepared {len(result['messages'])} messages; QA excluded")
    else:
        build(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Build stopped: {type(error).__name__}. Check local summary.json and inputs.", file=sys.stderr)
        sys.exit(1)
