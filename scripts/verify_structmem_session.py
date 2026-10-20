"""Verify C's session snapshot and inspect local retrieval; no answering or synthesis API."""
import argparse
from collections import Counter
from datetime import datetime, timedelta
from importlib import metadata
import json
import math
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from structmem_retrieve import (EMBEDDING, UPSTREAM_REVISION, file_hash, load_points,
                               local_embedder, original_source_ids, rank_points, read_json)

INSPECTION_QUERIES = (
    "What reminds Deborah of her mother?",
    "Where and when did Jolene's mother give her the pendant?",
    "How does Deborah want to support her community?",
)


def verify_source(prepared, conversations, points):
    sid = prepared["sample_id"]
    conversation = next(row["conversation"] for row in conversations if row["sample_id"] == sid)
    session = prepared["session_id"]
    expected = []
    for message in conversation[session]:
        content = message["text"]
        if message.get("blip_caption"):
            content += f" (image description: {message['blip_caption']})"
        expected.append({"message_id": message["dia_id"], "content": content,
                         "speaker_name": message["speaker"],
                         "speaker_id": "speaker_a" if message["speaker"] == conversation["speaker_a"] else "speaker_b"})
    if prepared["messages"] != expected or prepared["original_timestamp"] != conversation[f"{session}_date_time"]:
        raise ValueError("C input differs from A's original session messages/time")
    base = datetime.strptime(prepared["original_timestamp"], "%I:%M %p on %d %B, %Y")
    if datetime.fromisoformat(prepared["timestamp"]) != base:
        raise ValueError("Session timestamp parsing differs")
    for point in points:
        payload = point["payload"]
        index = payload["source_id"]
        if type(index) is not int or not 0 <= index < len(expected):
            raise ValueError("Source index outside the original session")
        source = expected[index]
        original_source_ids(sid, point)
        if (payload["source_message_id"] != source["message_id"] or
                payload["source_session_id"] != session or
                payload["speaker_name"] != source["speaker_name"] or
                payload["speaker_id"] != source["speaker_id"] or
                datetime.fromisoformat(payload["time_stamp"]) != base + timedelta(seconds=index)):
            raise ValueError("Source/speaker/bound-time mapping differs from original input")


def run(bundle, conversations, cache, out):
    from qdrant_client import QdrantClient
    if metadata.version("qdrant-client") != "1.15.1":
        raise ValueError("Use C's qdrant-client==1.15.1")
    bundle, out = Path(bundle).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError(out)
    handoff = read_json(bundle / "handoff.json")
    if handoff["upstream_revision"] != UPSTREAM_REVISION:
        raise ValueError("Upstream revision mismatch")
    if any(handoff["embedding"][key] != EMBEDDING[key] for key in
           ("model_id", "revision", "dimensions", "normalize_embeddings")):
        raise ValueError("Embedding contract mismatch")
    for name, expected in handoff["file_sha256"].items():
        path = (bundle / name).resolve()
        if not path.is_relative_to(bundle) or file_hash(path) != expected:
            raise ValueError(f"Bundle file changed: {name}")
    prepared = read_json(bundle / "input.json")
    points = load_points(bundle / "memories.json", "event")
    if len(points) != handoff["entry_count"] or dict(Counter(p["payload"]["entry_type"] for p in points)) != handoff["entry_types"]:
        raise ValueError("Entry count/type mismatch")
    verify_source(prepared, read_json(conversations), points)
    if len({p["payload"]["source_key"] for p in points}) != handoff["message_count"]:
        raise ValueError("Not all session messages are represented")
    if any(abs(math.hypot(*p["vector"]) - 1) > 1e-5 for p in points):
        raise ValueError("Stored vectors are not normalized")
    # Never open the received database in place: Qdrant can update its local storage on close.
    out.mkdir(parents=True, exist_ok=False)
    shutil.copytree(bundle / "qdrant", out / "qdrant-work")
    client = QdrantClient(path=str(out / "qdrant-work"))
    try:
        stored, offset = client.scroll(handoff["collection"], limit=len(points) + 1, with_vectors=True, with_payload=True)
        if offset is not None or {p.id: p.model_dump() for p in stored} != {p["id"]: p for p in points}:
            raise ValueError("Independent database read differs from the full JSON export")
        embed = local_embedder(cache)
        reproduced = [embed(p["payload"]["memory"]) for p in points]
        delta = max(abs(a - b) for point, vector in zip(points, reproduced) for a, b in zip(point["vector"], vector))
        if delta > 2e-5:
            raise ValueError(f"Re-embedded memories differ from C's vectors: max difference {delta}")
        cases = []
        for query in INSPECTION_QUERIES:
            vector = embed(query)
            hits = rank_points(points, vector, 5)
            db_hits = client.query_points(handoff["collection"], query=vector, limit=5, with_payload=True).points
            if [h["id"] for h in hits] != [str(p.id) for p in db_hits]:
                raise ValueError("D cosine order differs from Qdrant top-5")
            score_delta = max(abs(h["score"] - p.score) for h, p in zip(hits, db_hits))
            if score_delta > 2e-5:
                raise ValueError("D cosine scores differ from Qdrant")
            cases.append({"query": query, "qdrant_order_matches": True, "max_score_difference": score_delta,
                          "hits": [{"point_id": h["id"], "score": h["score"],
                                    "source_key": h["payload"]["source_key"], "memory": h["payload"]["memory"],
                                    "entry_type": h["payload"]["entry_type"], "time_stamp": h["payload"]["time_stamp"]}
                                   for h in hits]})
    finally:
        client.close()
    if any(file_hash(bundle / name) != expected for name, expected in handoff["file_sha256"].items()):
        raise ValueError("Received immutable bundle changed during validation")
    result = {"status": "single_session_receipt_verified", "sample_id": handoff["sample_id"],
              "session_id": handoff["session_id"], "conversation_complete": handoff["conversation_complete"],
              "completed_sessions": handoff["completed_sessions_in_conversation"],
              "total_sessions": handoff["total_sessions_in_conversation"],
              "entry_count": len(points), "entry_types": handoff["entry_types"],
              "source_messages": handoff["message_count"], "bundle_handoff_sha256": file_hash(bundle / "handoff.json"),
              "manifest_files_verified": len(handoff["file_sha256"]), "received_bundle_unchanged": True,
              "database_matches_export": True, "A_source_conversations_sha256": file_hash(conversations),
              "all_source_bindings_match_A": True, "memory_reembedding_max_difference": delta,
              "embedding": EMBEDDING, "device": "cpu", "query_count": len(cases), "top_k": 5,
              "formal_dataset_questions": 0, "generation_api_calls": 0, "synthesis_api_calls": 0,
              "scoring_api_calls": 0, "accuracy": None,
              "runtime": {"python": sys.version.split()[0], **{name: metadata.version(name) for name in
                          ("qdrant-client", "sentence-transformers", "transformers", "torch", "numpy", "huggingface-hub")}},
              "code_sha256": {p.name: file_hash(p) for p in (Path(__file__), ROOT / "src/structmem_retrieve.py")},
              "cases": cases}
    with (out / "receipt.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--source-conversations", type=Path, default=ROOT / "data/locomo/development.conversations.json")
    parser.add_argument("--model-cache", type=Path, default=ROOT / "data/model-cache")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.bundle, args.source_conversations, args.model_cache, args.out)
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
