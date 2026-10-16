"""Offline derived judge labels. Never calls a service or writes into source runs."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from metamem_pilot.data import file_hash, read
from metamem_pilot.pipeline import JUDGE_PARSER_VERSION, parse_judge_label


def derive(run):
    path = run / "smoke/rollouts-00.json"
    records = []
    for row in read(path):
        raw = row.get("judge_response")
        # A failed/interrupted generation is never recovered by parsing partial text.
        eligible = row["status"] in ("valid", "judge_parse_failed") and raw is not None
        parsed = parse_judge_label(raw) if eligible else None
        status = ("valid" if parsed is not None else "judge_parse_failed") if eligible else row["status"]
        records.append({"question_id": row["question_id"], "attempt": row["attempt"],
                        "judge_raw": raw, "original_status": row["status"],
                        "original_correct": row["correct"], "derived_status": status,
                        "derived_correct": parsed,
                        "changed": status != row["status"] or parsed != row["correct"]})
    valid = [r for r in records if r["derived_status"] == "valid"]
    return {"source": str(path), "source_sha256": file_hash(path), "records": records,
            "planned": len(records), "valid": len(valid),
            "yes": sum(r["derived_correct"] is True for r in valid),
            "no": sum(r["derived_correct"] is False for r in valid),
            "changed": [r for r in records if r["changed"]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="+", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    runs = [p.resolve() for p in args.runs]
    out = args.out.resolve()
    if any(out.is_relative_to(run) for run in runs):
        parser.error("Derived output must be outside all source runs")
    before = {p: file_hash(p) for run in runs for p in run.rglob("*") if p.is_file()}
    result = {"parser_version": JUDGE_PARSER_VERSION,
              "created_utc": datetime.now(timezone.utc).isoformat(), "model_calls": 0,
              "purpose": "format-only; no semantic relabeling or rule learning",
              "runs": [derive(run) for run in runs]}
    if any(file_hash(p) != sha for p, sha in before.items()):
        raise RuntimeError("Source artifacts changed during offline parsing")
    result["source_files_verified_unchanged"] = len(before)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"output": str(out), "source_files_unchanged": len(before),
                      "runs": [{k: r[k] for k in ("planned", "valid", "yes", "no", "changed")} for r in result["runs"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
