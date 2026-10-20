#!/usr/bin/env python3
"""Join frozen QA predictions with private E judgments and report fixed-denominator metrics."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def read_json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def keyed(rows, label):
    out = {}
    for row in rows:
        key = (row["sample_id"], row["qa_index"])
        if key in out:
            raise ValueError(f"Duplicate {label} key: {key}")
        out[key] = row
    return out


def evaluate(prediction_paths, labels_path, judgments_path):
    labels = keyed(read_json(labels_path), "label")
    if not labels:
        raise ValueError("The frozen label file is empty")
    judgment_document = read_json(judgments_path)
    judgments = keyed(judgment_document["items"], "judgment")
    if set(judgments) != set(labels):
        raise ValueError("Judgment keys must exactly match the frozen label keys")

    predictions = {}
    for method, path in prediction_paths.items():
        rows = read_jsonl(path)
        by_key = keyed(rows, method)
        if any(row.get("method") != method for row in rows):
            raise ValueError(f"Prediction method field does not match {method}")
        if not set(by_key).issubset(labels):
            raise ValueError(f"{method} contains keys outside the frozen label set")
        predictions[method] = by_key

    merged = []
    for method, by_key in predictions.items():
        for key, label in labels.items():
            prediction = by_key.get(key)
            judgment = judgments[key]["methods"].get(method)
            if judgment is None:
                raise ValueError(f"Missing {method} judgment for {key}")
            generation_status = prediction.get("status", "missing") if prediction else "missing"
            scored = generation_status == "ok" and judgment.get("status") == "scored"
            correct = judgment.get("correct") if scored else None
            if scored and type(correct) is not bool:
                raise ValueError(f"Scored judgment must have boolean correct value for {method} {key}")
            if generation_status != "ok" and correct is not None:
                raise ValueError(f"Failed generation cannot have a correctness score for {method} {key}")
            merged.append({
                "method": method,
                "sample_id": key[0],
                "qa_index": key[1],
                "category": label["category"],
                "question": label.get("question", prediction.get("question") if prediction else ""),
                "gold_answer": label["answer"],
                "prediction": prediction.get("prediction") if prediction else None,
                "generation_status": generation_status,
                "score_status": judgment.get("status", "not_scored") if generation_status == "ok" else "not_scored_generation_failed",
                "correct": correct,
                "judgment": judgment.get("judgment"),
                "rationale": judgment.get("rationale"),
                "usage": prediction.get("usage") if prediction else None,
                "seconds": prediction.get("seconds") if prediction else None,
            })

    summaries = {}
    for method in predictions:
        rows = [row for row in merged if row["method"] == method]
        valid = [row for row in rows if row["correct"] is not None]
        correct = sum(row["correct"] is True for row in valid)
        per_category = {}
        for category in sorted({row["category"] for row in rows}):
            group = [row for row in rows if row["category"] == category]
            scored_group = [row for row in group if row["correct"] is not None]
            category_correct = sum(row["correct"] is True for row in scored_group)
            per_category[str(category)] = {
                "correct": category_correct,
                "planned": len(group),
                "scored": len(scored_group),
                "accuracy_on_scored": category_correct / len(scored_group) if scored_group else None,
                "scoring_coverage": len(scored_group) / len(group) if group else None,
            }
        usage_rows = [row["usage"] for row in rows if isinstance(row["usage"], dict)]
        seconds = [row["seconds"] for row in rows if isinstance(row["seconds"], (int, float))]
        summaries[method] = {
            "planned": len(rows),
            "generated_successfully": sum(row["generation_status"] == "ok" for row in rows),
            "generation_failed_or_missing": sum(row["generation_status"] != "ok" for row in rows),
            "scored": len(valid),
            "judge_failed_or_missing": sum(row["generation_status"] == "ok" and row["correct"] is None for row in rows),
            "correct": correct,
            "accuracy_on_scored": correct / len(valid) if valid else None,
            "correct_over_planned": correct / len(rows) if rows else None,
            "scoring_coverage": len(valid) / len(rows) if rows else None,
            "usage": {
                "prompt_tokens": sum(item.get("prompt_tokens", 0) or 0 for item in usage_rows),
                "completion_tokens": sum(item.get("completion_tokens", 0) or 0 for item in usage_rows),
                "total_tokens": sum(item.get("total_tokens", 0) or 0 for item in usage_rows),
                "calls_with_usage": len(usage_rows),
                "calls_without_usage": len(rows) - len(usage_rows),
            },
            "sum_answer_call_seconds": sum(seconds) if seconds else None,
            "by_category": per_category,
        }
    return {"judgment_metadata": judgment_document.get("metadata", {}),
            "planned_category_counts": {str(k): v for k, v in sorted(Counter(row["category"] for row in labels.values()).items())},
            "methods": summaries}, merged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s0", type=Path, required=True, help="S0 predictions JSONL")
    parser.add_argument("--s2", type=Path, required=True, help="S2 predictions JSONL")
    parser.add_argument("--labels", type=Path, required=True, help="A frozen labels JSON (keep local; do not commit)")
    parser.add_argument("--judgments", type=Path, required=True, help="E's local per-question judgments JSON")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    args = parser.parse_args()
    summary, rows = evaluate({"S0": args.s0, "S2": args.s2}, args.labels, args.judgments)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = list(rows[0])
    with (args.out / "per-question.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                             for key, value in row.items()})
    print(json.dumps(summary["methods"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
