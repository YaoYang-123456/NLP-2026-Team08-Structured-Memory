"""Consume native StructMem point exports; emit the existing F input contract."""
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

UPSTREAM_REVISION = "8449d574df6bae1bdf3314a1564da65e2f37e046"
EMBEDDING = {
    "model_id": "sentence-transformers/all-MiniLM-L6-v2",
    "revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
    "dimensions": 384,
    "normalize_embeddings": True,
    "max_seq_length": 256,
}
QUESTION_FIELDS = {"sample_id", "qa_index", "question", "category"}
LABEL_FIELDS = {"answer", "adversarial_answer", "evidence", "qa", "labels"}


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def reject_labels(value):
    if isinstance(value, dict):
        if LABEL_FIELDS.intersection(value):
            raise ValueError("Labels must not enter memory or retrieval inputs")
        for item in value.values():
            reject_labels(item)
    elif isinstance(value, list):
        for item in value:
            reject_labels(item)


def load_questions(path):
    rows = read_json(path)
    seen = set()
    if not isinstance(rows, list) or not rows:
        raise ValueError("Expected a nonempty A question array")
    for row in rows:
        if not isinstance(row, dict) or set(row) != QUESTION_FIELDS:
            raise ValueError("Questions must contain exactly the four A input fields")
        key = (row["sample_id"], row["qa_index"])
        if (not isinstance(key[0], str) or not key[0].strip() or
                type(key[1]) is not int or key[1] < 0 or
                type(row["category"]) is not int or row["category"] not in (1, 2, 3, 4) or
                not isinstance(row["question"], str) or not row["question"].strip() or key in seen):
            raise ValueError("Malformed or duplicate question identity")
        seen.add(key)
    return rows


def validate_vector(vector):
    if (not isinstance(vector, list) or len(vector) != EMBEDDING["dimensions"] or
            any(type(x) not in (int, float) or not math.isfinite(x) for x in vector)):
        raise ValueError("Expected a finite 384-dimensional vector")
    norm = math.hypot(*vector)
    if not math.isfinite(norm) or norm == 0:
        raise ValueError("Zero or invalid vector norm")
    return norm


def memory_text(point, kind):
    payload = point["payload"]
    if kind == "event":
        text = next((payload.get(key) for key in ("memory", "original_memory", "compressed_memory")
                     if payload.get(key)), None)
        speaker = payload.get("speaker_name")
        timestamp = payload.get("time_stamp")
        if not all(isinstance(x, str) and x.strip() for x in (text, speaker, timestamp)):
            raise ValueError("Event needs memory, speaker_name and time_stamp")
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return f"Speaker: {speaker}\nRecorded: {timestamp}, {payload.get('weekday', '')}\n{text}"
    text = payload.get("summary") or payload.get("memory")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Synthesis needs summary text")
    if not isinstance(payload.get("covered_entry_ids"), list) or not payload["covered_entry_ids"]:
        raise ValueError("Synthesis needs native covered_entry_ids")
    time_range = payload.get("time_range")
    if not isinstance(time_range, dict):
        raise ValueError("Synthesis needs native time_range")
    for key in ("start", "end"):
        datetime.fromisoformat(time_range[key].replace("Z", "+00:00"))
    return f"Time range: {time_range['start']} — {time_range['end']}\n{text}"


def load_points(path, kind):
    points = read_json(path)
    if not isinstance(points, list) or not points:
        raise ValueError(f"Empty {kind} export; this is not a completed S2 handoff")
    seen = set()
    for point in points:
        if not isinstance(point, dict) or not {"id", "payload", "vector"}.issubset(point):
            raise ValueError("Expected native get_all(with_vectors=True, with_payload=True) points")
        if type(point["id"]) not in (int, str) or not str(point["id"]).strip():
            raise ValueError("Invalid point ID")
        pid = str(point["id"])
        if pid in seen or not isinstance(point["payload"], dict):
            raise ValueError("Duplicate point ID or malformed payload")
        seen.add(pid)
        reject_labels(point)
        validate_vector(point["vector"])
        memory_text(point, kind)
    return points


def load_memory_index(path, sample_ids, allow_synthetic=False):
    path = Path(path)
    index = read_json(path)
    if index.get("upstream_revision") != UPSTREAM_REVISION or index.get("embedding") != EMBEDDING:
        raise ValueError("Upstream or embedding contract differs from the fixed A version")
    if type(index.get("synthetic")) is not bool or (index["synthetic"] and not allow_synthetic):
        raise ValueError("Synthetic memory is permitted only for the explicit offline fixture check")
    result, hashes = {}, {}
    for sid in sample_ids:
        files = index["conversations"][sid]
        result[sid], hashes[sid] = {}, {}
        for kind in ("event", "synthesis"):
            spec = files[kind]
            source = path.parent / spec["path"]
            actual = file_hash(source)
            if actual != spec["sha256"]:
                raise ValueError(f"Changed {kind} export for {sid}")
            result[sid][kind] = load_points(source, kind)
            hashes[sid][kind] = actual
        event_ids = {str(p["id"]) for p in result[sid]["event"]}
        for point in result[sid]["event"]:
            original_source_ids(sid, point)
        for point in result[sid]["synthesis"]:
            payload = point["payload"]
            references = payload["covered_entry_ids"] + payload.get("seed_entry_ids", [])
            if any(str(pid) not in event_ids for pid in references):
                raise ValueError(f"Synthesis refers to an event outside the {sid} snapshot")
    return result, hashes


def original_source_ids(sample_id, point):
    payload = point["payload"]
    fields = ("source_sample_id", "source_message_id", "source_key")
    if not any(field in payload for field in fields):
        return []
    if (any(not isinstance(payload.get(field), str) or not payload[field].strip() for field in fields) or
            payload["source_sample_id"] != sample_id or
            payload["source_key"] != f"{sample_id}/{payload['source_message_id']}"):
        raise ValueError("Event source binding does not match its conversation")
    return [payload["source_key"]]


def rank_points(points, query_vector, limit):
    """Port of upstream VectorRetriever cosine ordering, with errors exposed at input."""
    query_norm = validate_vector(query_vector)
    ranked = []
    for point in points:
        norm = validate_vector(point["vector"])
        score = math.fsum((a / query_norm) * (b / norm) for a, b in zip(query_vector, point["vector"]))
        ranked.append({"id": str(point["id"]), "score": score, "payload": point["payload"]})
    return sorted(ranked, key=lambda p: p["score"], reverse=True)[:limit]


def prepare_inputs(questions, memories, embed):
    rows, traces = [], []
    for question in questions:
        sid = question["sample_id"]
        events = {str(point["id"]): point for point in memories[sid]["event"]}
        vector = embed(question["question"])
        contexts, hits = [], {}
        for kind, limit in (("event", 60), ("synthesis", 5)):
            selected = rank_points(memories[sid][kind], vector, limit)
            hits[kind] = selected
            for point in selected:
                ids = [f"{sid}/{kind}/{point['id']}"]
                if kind == "synthesis":
                    for pid in point["payload"]["covered_entry_ids"] + point["payload"].get("seed_entry_ids", []):
                        ids.append(f"{sid}/event/{pid}")
                        ids.extend(original_source_ids(sid, events[str(pid)]))
                else:
                    ids.extend(original_source_ids(sid, point))
                contexts.append({"source_ids": list(dict.fromkeys(ids)), "kind": kind,
                                 "text": memory_text(point, kind)})
        rows.append({**question, "contexts": contexts})
        traces.append({"sample_id": sid, "qa_index": question["qa_index"], "retrieved": hits})
    return rows, traces


def load_local_model(cache):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBEDDING["model_id"], revision=EMBEDDING["revision"],
                                cache_folder=str(cache), device="cpu", local_files_only=True)
    if model.get_sentence_embedding_dimension() != 384 or model.max_seq_length != 256:
        raise ValueError("Local embedding model dimensions or maximum sequence length changed")
    return model


def local_embedder(cache):
    model = load_local_model(cache)

    def embed(text):
        return model.encode(text, normalize_embeddings=True, convert_to_numpy=True).tolist()
    return embed


def summarize_memory(memory):
    """Call only on D's private Qdrant copy, in a fresh process per conversation."""
    return memory.summarize(retrieval_scope="global", time_window=3600,
                            top_k_seeds=15, process_all=True, enable_cross_event=True)
