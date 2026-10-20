"""Execute the frozen native synthesis proposals, stopping at the first failed request."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from llm_client import Client
from structmem_retrieve import file_hash, read_json


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def load_proposals(preparations):
    proposals, hashes, seen = [], {}, set()
    for directory in preparations:
        report = read_json(directory / "preparation.json")
        source = directory / "proposed-calls.jsonl"
        if (report["status"] != "offline_native_synthesis_prepared" or report["synthetic"] is not True or
                file_hash(source) != report["proposal_sha256"]):
            raise ValueError("Native preparation does not match its receipt")
        rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
        if len(rows) != report["proposed_calls"]:
            raise ValueError("Native proposal count changed")
        for position, row in enumerate(rows):
            identity = row["sample_id"], row["window_index"]
            request = row["proposed_request"]
            if (identity in seen or identity != (report["sample_id"], position) or
                    row["stage"] != "offline_synthesis_preparation" or row["real_request_sent"] is not False or
                    row["usage"] is not None or set(request) != {
                        "model", "messages", "thinking", "stream", "temperature", "top_p", "max_tokens"} or
                    {k: v for k, v in request.items() if k != "messages"} != {
                        "model": "deepseek-flash", "thinking": {"type": "disabled"}, "stream": False,
                        "temperature": 0, "top_p": 1, "max_tokens": 8192} or
                    not isinstance(request["messages"], list) or len(request["messages"]) != 2 or
                    any(set(m) != {"role", "content"} or not isinstance(m["content"], str) or not m["content"].strip()
                        for m in request["messages"]) or
                    [m["role"] for m in request["messages"]] != ["system", "user"]):
                raise ValueError("Unexpected native synthesis proposal")
            seen.add(identity)
            proposals.append(row)
        hashes[str(source.resolve())] = file_hash(source)
    if not proposals:
        raise ValueError("No synthesis proposals")
    return proposals, hashes


def run(preparations, out, recorded_calls=None):
    proposals, hashes = load_proposals(preparations)
    previous = {}
    if recorded_calls is not None:
        for line in recorded_calls.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event["status"] == "ok" and event["simulated"] is False:
                identity = event["sample_id"], event["window_index"]
                if identity in previous:
                    raise ValueError("Duplicate successful recorded call")
                previous[identity] = event
        expected = {(p["sample_id"], p["window_index"]): p["proposed_request"] for p in proposals}
        if any(key not in expected or event["request"] != expected[key] or
               not isinstance(event["prediction"], str) or not event["prediction"].strip() or
               event["finish_reason"] != "stop" or not isinstance(event["usage"], dict)
               for key, event in previous.items()):
            raise ValueError("Recorded successful calls differ from the frozen proposals")
    config = read_json(ROOT / "configs/qa-structmem-candidate.json")
    config.update(max_tokens=8192, timeout_seconds=120)
    client = Client(config)
    out.mkdir(parents=True, exist_ok=False)
    manifest = {"status": "running", "synthetic": False, "started_utc": datetime.now(timezone.utc).isoformat(),
                "planned_windows": len(proposals), "proposal_sha256": hashes,
                "code_sha256": {str(p.relative_to(ROOT)): file_hash(p) for p in (Path(__file__), ROOT / "src/llm_client.py")},
                "max_tokens": 8192, "timeout_seconds": 120, "automatic_retries": 0,
                "new_requests": 0, "reused_successful_calls": 0, "successful_windows": 0, "usage": {}}
    counts, usage = Counter(), Counter()
    try:
        with (out / "calls.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
            for proposal in proposals:
                identity = proposal["sample_id"], proposal["window_index"]
                reused = identity in previous
                event = previous[identity] if reused else client.call(proposal["proposed_request"]["messages"])
                event = {**event, "sample_id": identity[0], "window_index": identity[1], "reused": reused}
                stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
                stream.flush()
                counts["reused" if reused else "sent"] += 1
                if isinstance(event["usage"], dict):
                    usage.update({k: v for k, v in event["usage"].items() if type(v) is int})
                if event["status"] != "ok" or not isinstance(event["usage"], dict):
                    manifest["status"] = "stopped_on_failed_call"
                    break
                if event["request"] != proposal["proposed_request"]:
                    raise ValueError("Sent request differs from the native proposal")
                counts["ok"] += 1
                print(json.dumps({"sample_id": identity[0], "window_index": identity[1], "status": event["status"],
                                  "reused": reused, "usage": event["usage"]}, ensure_ascii=False), flush=True)
            else:
                manifest["status"] = "completed"
    finally:
        if manifest["status"] == "running":
            manifest["status"] = "failed"
        manifest.update(new_requests=counts["sent"], reused_successful_calls=counts["reused"],
                        successful_windows=counts["ok"], usage=dict(usage),
                        finished_utc=datetime.now(timezone.utc).isoformat())
        write_json(out / "run.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False), flush=True)
    return 0 if manifest["status"] == "completed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparation", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--recorded-calls", type=Path, help="Reuse matching successful calls without sending them again")
    parser.add_argument("--execute", action="store_true", required=True)
    args = parser.parse_args()
    return run(args.preparation, args.out, args.recorded_calls)


if __name__ == "__main__":
    sys.exit(main())
