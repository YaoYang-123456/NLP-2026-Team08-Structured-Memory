"""Plan, checkpoint and assemble C's three complete development conversations.

Only A's hash-verified development.conversations.json is an extraction input.
No raw dataset, questions, labels, evidence or summaries are opened here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from types import SimpleNamespace

from structmem_build import (UPSTREAM_REV, build, prepare_session, read_json,
                            sha256, validate_prepared, write_json)

DEVELOPMENT = ["conv-48", "conv-42", "conv-41"]


def exact_write(path, value):
    content = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path = Path(path)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"Existing plan/input differs: {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)


def load_development(data_path, selection_path):
    data_path = Path(data_path).resolve()
    if data_path.name != "development.conversations.json":
        raise ValueError("Only development.conversations.json may be used")
    selection = read_json(selection_path)
    if (selection["splits"]["development"] != DEVELOPMENT or
            selection["lightmem"]["revision"] != UPSTREAM_REV):
        raise ValueError("Development split/upstream differs from A's handoff")
    if sha256(data_path) != selection["output_sha256"][data_path.name]:
        raise ValueError("Development conversation file hash differs from A's freeze")
    rows = read_json(data_path)
    if not isinstance(rows, list) or [row.get("sample_id") for row in rows] != DEVELOPMENT:
        raise ValueError("Unexpected conversation IDs/order")
    for row in rows:
        if set(row) != {"sample_id", "conversation"}:
            raise ValueError("Unexpected top-level field in extraction input")
        conversation = row["conversation"]
        session_keys = [k for k in conversation if re.fullmatch(r"session_\d+", k)]
        expected = {"speaker_a", "speaker_b"}
        seen = set()
        for session_key in session_keys:
            expected.update((session_key, session_key + "_date_time"))
            for message in conversation[session_key]:
                if (not {"dia_id", "speaker", "text"} <= set(message) or
                        set(message) - {"dia_id", "speaker", "text", "blip_caption"}):
                    raise ValueError("Unexpected message fields")
                if message["dia_id"] in seen:
                    raise ValueError("Duplicate message ID within a conversation")
                seen.add(message["dia_id"])
        if not session_keys or set(conversation) != expected:
            raise ValueError("Unexpected conversation fields, summary, or missing timestamp")
    return rows


def make_plan(data_path, selection_path, profile_path, destination):
    rows = load_development(data_path, selection_path)
    profile = read_json(profile_path)
    if profile.get("normalize_embeddings") is not True or profile["embedding_dims"] != 384:
        raise ValueError("Development profile must use normalized 384-dimensional embeddings")
    destination = Path(destination).resolve()
    sessions = []
    for row in rows:
        numbers = sorted(int(k.split("_")[1]) for k in row["conversation"] if re.fullmatch(r"session_\d+", k))
        for number in numbers:
            prepared = prepare_session(rows, row["sample_id"], number)
            validate_prepared(prepared)
            relative = f"{row['sample_id']}/inputs/session-{number:03d}.json"
            sessions.append({"sample_id": row["sample_id"], "session_number": number,
                             "input": relative, "message_count": len(prepared["messages"]),
                             "prepared": prepared})
    plan = {"schema_version": 1, "development": DEVELOPMENT,
            "source": str(Path(data_path).resolve()), "source_sha256": sha256(data_path),
            "selection_config": str(Path(selection_path).resolve()),
            "selection_sha256": sha256(selection_path), "upstream_revision": UPSTREAM_REV,
            "profile": profile, "session_count": len(sessions),
            "message_count": sum(s["message_count"] for s in sessions), "sessions": []}
    # Complete all validation before any plan/input write.
    for session in sessions:
        path = destination / session["input"]
        exact_write(path, session["prepared"])
        plan["sessions"].append({k: v for k, v in session.items() if k != "prepared"} | {"sha256": sha256(path)})
    exact_write(destination / "profile.json", profile)
    exact_write(destination / "plan.json", plan)
    return plan


def validate_plan(plan_path):
    plan_path = Path(plan_path).resolve()
    plan = read_json(plan_path)
    root = plan_path.parent
    if plan["development"] != DEVELOPMENT or plan["upstream_revision"] != UPSTREAM_REV:
        raise ValueError("Invalid plan identity")
    if sha256(plan["selection_config"]) != plan["selection_sha256"]:
        raise ValueError("Selection config changed")
    rows = load_development(plan["source"], plan["selection_config"])
    if sha256(plan["source"]) != plan["source_sha256"] or read_json(root / "profile.json") != plan["profile"]:
        raise ValueError("Plan source/profile changed")
    expected_sessions = [(row["sample_id"], number) for row in rows
                         for number in sorted(int(k.split("_")[1]) for k in row["conversation"] if re.fullmatch(r"session_\d+", k))]
    if ([(s["sample_id"], s["session_number"]) for s in plan["sessions"]] != expected_sessions or
            plan["session_count"] != len(expected_sessions) or
            plan["message_count"] != sum(s["message_count"] for s in plan["sessions"])):
        raise ValueError("Plan omits, duplicates or reorders sessions")
    for session in plan["sessions"]:
        path = (root / session["input"]).resolve()
        if not path.is_relative_to(root) or sha256(path) != session["sha256"]:
            raise ValueError("Prepared input path/hash changed")
        prepared = read_json(path)
        validate_prepared(prepared)
        if prepared["sample_id"] != session["sample_id"] or prepared["session_id"] != f"session_{session['session_number']}":
            raise ValueError("Session identity changed")
        if prepared != prepare_session(rows, session["sample_id"], session["session_number"]):
            raise ValueError("Prepared input differs from A's source conversation")
    return root, plan


def completed_attempt(root, session):
    attempts = root / session["sample_id"] / f"session-{session['session_number']:03d}"
    if not attempts.exists():
        return None
    successful = []
    for attempt in sorted(attempts.glob("attempt-*")):
        summary_path = attempt / "summary.json"
        if not summary_path.is_file():
            continue
        summary = read_json(summary_path)
        if summary["status"] == "success":
            if (summary["input_sha256"] != session["sha256"] or
                    summary.get("synthetic") is not False or summary.get("execution") != "live" or
                    summary.get("sample_id") != session["sample_id"] or
                    summary.get("session_id") != f"session_{session['session_number']}" or
                    summary.get("upstream_revision") != UPSTREAM_REV or
                    summary.get("config") != read_json(root / "profile.json") or
                    not summary.get("disk_readback_verified") or
                    summary.get("memories_sha256") != sha256(attempt / "memories.json")):
                raise ValueError("Completed checkpoint hash/identity mismatch")
            successful.append(attempt)
    if len(successful) > 1:
        raise ValueError("Multiple successful attempts; resolve before reuse")
    return successful[0] if successful else None


def run_plan(args):
    if args.limit < 0:
        raise ValueError("Session limit cannot be negative")
    root, plan = validate_plan(args.plan)
    if args.conversation and args.conversation not in DEVELOPMENT:
        raise ValueError("Conversation outside frozen development split")
    import tiktoken
    encoder = tiktoken.get_encoding("o200k_base")
    # Preflight all sessions before the first paid call.
    for session in plan["sessions"]:
        value = read_json(root / session["input"])
        count = sum(len(encoder.encode(m["content"])) for m in value["messages"])
        if count > plan["profile"]["max_input_tokens"]:
            raise ValueError("A complete session exceeds input cap; no truncation allowed")
    ran = skipped = 0
    for session in plan["sessions"]:
        if args.conversation and session["sample_id"] != args.conversation:
            continue
        if completed_attempt(root, session):
            skipped += 1
            continue
        attempts = root / session["sample_id"] / f"session-{session['session_number']:03d}"
        existing = list(attempts.glob("attempt-*")) if attempts.exists() else []
        if existing and not args.retry_failed:
            raise RuntimeError("Unfinished/failed session exists; inspect logs, then explicitly use --retry-failed")
        number = max([int(p.name.split("-")[1]) for p in existing] + [0]) + 1
        attempt = attempts / f"attempt-{number:03d}"
        build(SimpleNamespace(input=str(root / session["input"]), config=str(root / "profile.json"),
                              upstream=args.upstream, embedding_model=args.embedding_model,
                              output=str(attempt), env_file=args.env_file, synthetic=False,
                              replay=None, topic_id=session["session_number"]))
        ran += 1
        if args.limit and ran >= args.limit:
            break
    return {"new_sessions_built": ran, "completed_sessions_skipped": skipped,
            "planned_sessions": plan["session_count"]}


def collect_conversation(root, plan, sample_id):
    records = []
    for session in plan["sessions"]:
        if session["sample_id"] != sample_id:
            continue
        attempt = completed_attempt(root, session)
        if attempt is None:
            raise ValueError("Incomplete conversation; refusing to assemble partial memories")
        for point in read_json(attempt / "memories.json"):
            payload = point["payload"]
            if (payload["source_sample_id"] != sample_id or
                    payload["source_session_id"] != f"session_{session['session_number']}"):
                raise ValueError("Cross-conversation memory detected")
            payload["source_key"] = f"{sample_id}/{payload['source_message_id']}"
            stable_id = hashlib.sha256(f"{sample_id}/{session['session_number']}/{point['id']}".encode()).hexdigest()
            # Valid UUID with stable identity across assembly retries.
            import uuid
            point["id"] = str(uuid.UUID(stable_id[:32]))
            records.append(point)
    if not records:
        raise ValueError("No memories to assemble")
    return records


def assemble(args):
    from qdrant_client import QdrantClient, models
    root, plan = validate_plan(args.plan)
    # Check all selected conversations before writing any assembled output.
    selected = [args.conversation] if args.conversation else DEVELOPMENT
    if any(cid not in DEVELOPMENT for cid in selected):
        raise ValueError("Conversation outside development split")
    groups = {cid: collect_conversation(root, plan, cid) for cid in selected}
    destination = Path(args.output).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    results = {}
    for cid, records in groups.items():
        path = destination / cid
        path.mkdir()
        collection = cid.replace("-", "_") + "_events"
        client = QdrantClient(path=str(path / "qdrant"))
        try:
            client.create_collection(collection, vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE))
            for start in range(0, len(records), 128):
                client.upsert(collection, points=[models.PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in records[start:start+128]], wait=True)
        finally:
            client.close()
        reopened = QdrantClient(path=str(path / "qdrant"))
        try:
            actual, offset = reopened.scroll(collection, limit=len(records)+1, with_vectors=True)
            expected = {p["id"]: p for p in records}
            if offset is not None or len(actual) != len(records):
                raise RuntimeError("Assembled collection count mismatch")
            for point in actual:
                vector_ok = (len(point.vector) == len(expected[point.id]["vector"]) and
                             all(abs(a-b) <= 1e-6 for a,b in zip(point.vector, expected[point.id]["vector"])))
                if point.payload != expected[point.id]["payload"] or not vector_ok:
                    raise RuntimeError("Assembled payload/vector mismatch")
        finally:
            reopened.close()
        results[cid] = {"collection": collection, "entry_count": len(records), "disk_readback_verified": True}
    write_json(destination / "handoff.json", {"status": "success", "plan_sha256": sha256(args.plan),
               "profile": plan["profile"], "conversations": results,
               "method_difference": "No compression/topic segmentation; requires team acceptance before formal S2 comparison"})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--data", default="data/locomo/development.conversations.json")
    plan.add_argument("--selection-config", default="configs/locomo-smoke.json")
    plan.add_argument("--profile", default="configs/structmem-development.json")
    plan.add_argument("--output", required=True)
    run = sub.add_parser("run")
    run.add_argument("--plan", required=True)
    run.add_argument("--upstream", required=True)
    run.add_argument("--embedding-model", required=True)
    run.add_argument("--env-file", default=".env")
    run.add_argument("--conversation", choices=DEVELOPMENT)
    run.add_argument("--limit", type=int, default=0, help="Build at most N new sessions; zero means all")
    run.add_argument("--retry-failed", action="store_true")
    finish = sub.add_parser("assemble")
    finish.add_argument("--plan", required=True)
    finish.add_argument("--conversation", choices=DEVELOPMENT)
    finish.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "plan":
        result = make_plan(args.data, args.selection_config, args.profile, args.output)
        print(json.dumps({k: result[k] for k in ("session_count", "message_count")}, ensure_ascii=False))
    else:
        print(json.dumps(run_plan(args) if args.command == "run" else assemble(args), ensure_ascii=False))


if __name__ == "__main__":
    main()
