"""Answer an explicit B/D retrieval JSONL and leave prediction/call records for E."""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from llm_client import Client, METHODS, build_messages
from metamem_pilot.data import digest, file_hash, read, write


def load_inputs(path):
    rows = []
    seen = set()
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            if not isinstance(row, dict) or set(row) != {"sample_id", "qa_index", "question", "category", "contexts"}:
                raise ValueError(f"Line {line_number}: expected only QA identity, question, category and contexts; no labels")
            if (not isinstance(row["sample_id"], str) or not row["sample_id"].strip() or
                    type(row["qa_index"]) is not int or row["qa_index"] < 0 or
                    not isinstance(row["question"], str) or not row["question"].strip() or
                    type(row["category"]) is not int or row["category"] not in (1, 2, 3, 4)):
                raise ValueError(f"Line {line_number}: invalid QA identity, question or category")
            identity = row["sample_id"], row["qa_index"]
            if identity in seen:
                raise ValueError(f"Line {line_number}: duplicate (sample_id, qa_index)")
            seen.add(identity)
            if not isinstance(row["contexts"], list):
                raise ValueError(f"Line {line_number}: contexts must be a list")
            for context in row["contexts"]:
                if (not isinstance(context, dict) or set(context) != {"source_ids", "kind", "text"} or
                        context["kind"] not in ("raw", "event", "synthesis") or
                        not isinstance(context["text"], str) or not context["text"].strip() or
                        not isinstance(context["source_ids"], list) or not context["source_ids"] or
                        any(not isinstance(sid, str) or not sid.strip() for sid in context["source_ids"])):
                    raise ValueError(f"Line {line_number}: malformed context or unexpected annotation")
            rows.append(row)
    if not rows:
        raise ValueError("Input JSONL is empty")
    return rows


def run(inputs, config_path, method, out, mock):
    # Validate the complete batch before the first request, including duplicate IDs and label fields.
    rows = load_inputs(inputs)
    config = read(config_path)
    client = Client(config, mock=mock)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    manifest = {"method": method, "simulated": mock, "status": "running",
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "input_file": str(Path(inputs).resolve()), "input_sha256": file_hash(inputs),
                "config_file": str(Path(config_path).resolve()), "config": config, "config_sha256": digest(config),
                "question_set_sha256": digest([{key: row[key] for key in
                                               ("sample_id", "qa_index", "question", "category")} for row in rows]),
                "code_sha256": {str(path.relative_to(ROOT)): file_hash(path) for path in
                                (Path(__file__), ROOT / "src/llm_client.py", ROOT / "src/metamem_pilot/data.py")},
                "planned_questions": len(rows), "processed_questions": 0,
                "successful_questions": 0, "failed_questions": 0, "simulated_questions": 0,
                "interrupted_questions": 0}
    write(out / "run.json", manifest)
    counts = Counter()
    exit_code = 1
    try:
        with (out / "calls.jsonl").open("x", encoding="utf-8", newline="\n") as calls, \
                (out / "predictions.jsonl").open("x", encoding="utf-8", newline="\n") as predictions:
            for row in rows:
                event = client.call(build_messages(config, method, row))
                identity = {"method": method, "sample_id": row["sample_id"], "qa_index": row["qa_index"]}
                calls.write(json.dumps({**identity, **event}, ensure_ascii=False) + "\n")
                calls.flush()
                result = {**identity, "question": row["question"], "category": row["category"],
                          "contexts": row["contexts"],
                          "source_ids": list(dict.fromkeys(sid for context in row["contexts"] for sid in context["source_ids"])),
                          **{key: event[key] for key in ("prediction", "status", "simulated", "usage", "seconds",
                                                       "started_utc", "returned_model", "finish_reason", "error", "http_status")}}
                predictions.write(json.dumps(result, ensure_ascii=False) + "\n")
                predictions.flush()
                counts[event["status"]] += 1
                if event["status"] == "interrupted":
                    manifest["status"] = "interrupted"
                    break
            else:
                manifest["status"] = "simulated" if mock else ("completed_with_failures" if counts["failed"] else "completed")
            exit_code = 130 if counts["interrupted"] else int(bool(counts["failed"]))
    except KeyboardInterrupt:
        manifest["status"] = "interrupted"
        exit_code = 130
    finally:
        if manifest["status"] == "running":
            manifest["status"] = "failed"
        manifest.update(processed_questions=sum(counts.values()), successful_questions=counts["ok"],
                        failed_questions=counts["failed"], simulated_questions=counts["simulated"],
                        interrupted_questions=counts["interrupted"],
                        finished_utc=datetime.now(timezone.utc).isoformat())
        write(out / "run.json", manifest)
    print(json.dumps({key: manifest[key] for key in ("status", "planned_questions", "processed_questions",
                                                    "successful_questions", "failed_questions", "simulated_questions")},
                     ensure_ascii=False))
    return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Explicit frozen retrieval JSONL; never auto-discover data")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/qa.example.json")
    parser.add_argument("--method", choices=METHODS, required=True)
    parser.add_argument("--out", type=Path, required=True, help="New output directory; existing paths are refused")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--mock", action="store_true", help="Offline flow check only; no requests or experimental results")
    mode.add_argument("--execute", action="store_true", help="One paid POST per input row; no retries")
    args = parser.parse_args()
    return run(args.input, args.config, args.method, args.out, mock=args.mock)


if __name__ == "__main__":
    sys.exit(main())
