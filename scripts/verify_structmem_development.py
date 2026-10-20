"""Accept C's complete event snapshot and prepare event-only retrieval; no synthesis or QA API."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib import metadata
import json
import math
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from structmem_retrieve import (EMBEDDING, UPSTREAM_REVISION, file_hash, load_local_model,
                               load_points, load_questions, prepare_inputs, rank_points, read_json)
from verify_structmem_session import verify_source


def compare_hits(expected, actual, points, vector):
    actual_ids = [str(point.id) for point in actual]
    same_order = [point["id"] for point in expected] == actual_ids
    maximum = 0.0
    for expected_point, actual_point in zip(expected, actual):
        score = rank_points([points[str(actual_point.id)]], vector, 1)[0]["score"]
        maximum = max(maximum, abs(score - actual_point.score))
        if abs(score - actual_point.score) > 2e-5:
            raise ValueError("Qdrant and D cosine scores differ")
        # The received databases contain duplicate memory texts; equal-score IDs need not have identical order.
        if expected_point["id"] != str(actual_point.id) and abs(expected_point["score"] - score) > 1e-7:
            raise ValueError("Qdrant and D order differs beyond equal-score ties")
    if len(expected) != len(actual):
        raise ValueError("Qdrant and D retrieval lengths differ")
    return {"same_order": same_order, "same_id_set": {p["id"] for p in expected} == set(actual_ids),
            "valid_cosine_order_including_ties": True, "max_score_difference": maximum}


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def run(bundle, frozen_config, source_conversations, model_cache, out):
    import numpy as np
    from qdrant_client import QdrantClient
    if metadata.version("qdrant-client") != "1.15.1":
        raise ValueError("Use C's qdrant-client==1.15.1")
    bundle, out = Path(bundle).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError(out)
    hashes = read_json(bundle / "files.sha256.json")
    for name, expected in hashes.items():
        path = (bundle / name).resolve()
        if not path.is_relative_to(bundle) or file_hash(path) != expected:
            raise ValueError(f"Received file changed: {name}")
    config, record, handoff = read_json(frozen_config), read_json(bundle / "run-record.json"), read_json(bundle / "handoff.json")
    if (file_hash(source_conversations) != record["source_sha256"] or
            record["source_sha256"] != config["output_sha256"]["development.conversations.json"] or
            record["upstream_revision"] != UPSTREAM_REVISION or record["synthetic"] is not False or
            record["execution"] != "live" or handoff["plan_sha256"] != record["plan_sha256"]):
        raise ValueError("C snapshot identity differs from the A freeze")
    if any(config["embedding"][key] != value for key, value in EMBEDDING.items()):
        raise ValueError("A embedding contract changed")
    sample_ids = config["splits"]["development"]
    if set(handoff["conversations"]) != set(sample_ids) or record["completed_sessions"] != record["planned_sessions"]:
        raise ValueError("Development snapshot is incomplete")
    conversations = read_json(source_conversations)
    checkpoints = {(c["sample_id"], c["session_id"]): c for c in record["checkpoints"]}
    if len(checkpoints) != record["completed_sessions"]:
        raise ValueError("Duplicate/missing checkpoint identity")
    questions_path = Path(source_conversations).parent / "development.inputs.json"
    questions = load_questions(questions_path)
    if file_hash(questions_path) != config["output_sha256"]["development.inputs.json"]:
        raise ValueError("Question text/identity differs from A")
    out.mkdir(parents=True, exist_ok=False)
    memories, clients, summaries = {}, {}, {}
    try:
        for sid in sample_ids:
            info, declared = handoff["conversations"][sid], record["conversations"][sid]
            shutil.copytree(bundle / sid / "qdrant", out / sid / "qdrant-work")
            client = QdrantClient(path=str(out / sid / "qdrant-work"))
            clients[sid] = client
            points, offset = [], None
            while True:
                batch, offset = client.scroll(info["collection"], offset=offset, limit=256, with_vectors=True, with_payload=True)
                points.extend(point.model_dump() for point in batch)
                if offset is None:
                    break
            export = out / sid / "events.json"
            save(export, points)
            points = load_points(export, "event")
            if len(points) != info["entry_count"] or len(points) != declared["entry_count"]:
                raise ValueError(f"Entry count mismatch for {sid}")
            grouped = defaultdict(list)
            for point in points:
                grouped[point["payload"]["source_session_id"]].append(point)
                if point["payload"].get("consolidated") is not False:
                    raise ValueError("Expected unsummarized event snapshot")
                if abs(math.hypot(*point["vector"]) - 1) > 1e-5:
                    raise ValueError("Stored vector is not normalized")
            actual_sessions = {key for key in next(c["conversation"] for c in conversations if c["sample_id"] == sid)
                               if key.startswith("session_") and not key.endswith("_date_time")}
            if set(grouped) != actual_sessions or len(grouped) != declared["session_count"]:
                raise ValueError("Missing or unexpected source sessions")
            message_count = 0
            for session_id, session_points in grouped.items():
                number = int(session_id.split("_")[1])
                prepared = read_json(bundle / "inputs" / sid / f"session-{number:03d}.json")
                if prepared["sample_id"] != sid or prepared["session_id"] != session_id:
                    raise ValueError("Session file identity mismatch")
                verify_source(prepared, conversations, session_points)
                if len(session_points) != checkpoints[sid, session_id]["entry_count"]:
                    raise ValueError("Session entry count differs from checkpoint")
                message_count += len(prepared["messages"])
            source_count = len({p["payload"]["source_key"] for p in points})
            types = dict(Counter(p["payload"]["entry_type"] for p in points))
            if (message_count != declared["message_count"] or source_count != declared["source_messages_referenced"] or
                    types != declared["entry_types"]):
                raise ValueError("Source or type statistics differ from C record")
            memories[sid] = {"event": points, "synthesis": []}
            summaries[sid] = {"collection": info["collection"], "entry_count": len(points), "entry_types": types,
                              "session_count": len(grouped), "message_count": message_count,
                              "source_messages_referenced": source_count, "source_messages_without_direct_entry": message_count - source_count,
                              "events_sha256": file_hash(export), "database_count": client.count(info["collection"], exact=True).count}
        if sum(s["entry_count"] for s in summaries.values()) != record["entry_count"]:
            raise ValueError("Total entry count mismatch")
        model = load_local_model(model_cache)
        flat = [p for sid in sample_ids for p in memories[sid]["event"]]
        encoded = model.encode([p["payload"]["memory"] for p in flat], batch_size=64,
                               normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=True)
        delta = float(np.max(np.abs(encoded - np.asarray([p["vector"] for p in flat]))))
        if not np.isfinite(encoded).all() or delta > 2e-5:
            raise ValueError(f"Re-embedded memories differ from C: {delta}")
        query_vectors = model.encode([q["question"] for q in questions], batch_size=32,
                                     normalize_embeddings=True, convert_to_numpy=True)
        vectors = {q["question"]: vector.tolist() for q, vector in zip(questions, query_vectors)}
        rows, traces = prepare_inputs(questions, memories, lambda text: vectors[text])
        comparisons = []
        for question, trace in zip(questions, traces):
            sid = question["sample_id"]
            db_hits = clients[sid].query_points(handoff["conversations"][sid]["collection"],
                                              query=vectors[question["question"]], limit=60, with_payload=True).points
            check = compare_hits(trace["retrieved"]["event"], db_hits,
                                 {str(p["id"]): p for p in memories[sid]["event"]}, vectors[question["question"]])
            comparisons.append({"sample_id": sid, "qa_index": question["qa_index"], **check})
        with (out / "event-retrieval30.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        save(out / "provenance.json", traces)
    finally:
        for client in clients.values():
            client.close()
    if any(file_hash(bundle / name) != expected for name, expected in hashes.items()):
        raise ValueError("Received snapshot changed during validation")
    result = {"status": "complete_event_snapshot_verified", "date": datetime.now(timezone.utc).astimezone().date().isoformat(),
              "conversations": summaries, "declared_files_verified": len(hashes), "received_bundle_unchanged": True,
              "A_source_sha256": file_hash(source_conversations), "frozen_config_sha256": file_hash(frozen_config),
              "event_count": len(flat), "session_count": sum(s["session_count"] for s in summaries.values()),
              "message_count": sum(s["message_count"] for s in summaries.values()),
              "source_messages_without_direct_entry": sum(s["source_messages_without_direct_entry"] for s in summaries.values()),
              "memory_reembedding_max_difference": delta, "embedding": EMBEDDING, "device": "cpu", "embedding_batch_size": 64,
              "retrieval_questions": len(questions), "events_per_question": 60, "summaries_per_question": 0,
              "retrieval_stage": "event_only_preparation_not_complete_S2", "comparisons": comparisons,
              "synthesis_api_calls": 0, "answer_api_calls": 0, "scoring_api_calls": 0, "accuracy": None,
              "runtime": {"python": sys.version.split()[0], **{n: metadata.version(n) for n in
                          ("torch", "sentence-transformers", "transformers", "qdrant-client", "numpy")}},
              "code_sha256": {p.name: file_hash(p) for p in (Path(__file__), ROOT / "src/structmem_retrieve.py",
                                                           ROOT / "scripts/verify_structmem_session.py")}}
    save(out / "receipt.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--frozen-config", type=Path, required=True)
    parser.add_argument("--source-conversations", type=Path, default=ROOT / "data/locomo/development.conversations.json")
    parser.add_argument("--model-cache", type=Path, default=ROOT / "data/model-cache")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.bundle, args.frozen_config, args.source_conversations, args.model_cache, args.out)
    print(json.dumps({k: v for k, v in result.items() if k != "comparisons"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
