"""Offline policy sensitivity: export hidden labels, then join explicit AI reviews."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from metamem_pilot.data import read, write, digest, file_hash

VERSION = "external-ai-strict-abstention-v2"


def snapshot(root):
    return {str(p.relative_to(root)): file_hash(p) for p in root.rglob("*") if p.is_file()}


def export(source, out, policy):
    if out.resolve().is_relative_to(source.resolve()):
        raise ValueError("Derived output must be outside the original run")
    out.mkdir(parents=True, exist_ok=False)
    frozen = read(policy)
    if frozen["version"] != VERSION:
        raise ValueError("Wrong policy version")
    # Freeze before exporting any answer for a new assessment.
    write(out / "policy.frozen.json", frozen)
    write(out / "freeze.json", {"version": VERSION, "policy_sha256": digest(frozen),
                               "frozen_utc": datetime.now(timezone.utc).isoformat()})
    write(out / "source-hashes.before.json", snapshot(source))
    queue, private = [], []
    review_dir = source / "smoke/review"
    for batch in range(5):
        original = read(review_dir / f"queue-{batch:03d}.json")
        old = {r["sample_id"]: r for r in read(review_dir / f"accepted-{batch:03d}.json")["results"]}
        mapping = {r["sample_id"]: r for r in read(review_dir / f"mapping-{batch:03d}.private.json")}
        if set(old) != set(mapping) or set(old) != {r["sample_id"] for r in original}:
            raise ValueError("Original review IDs inconsistent")
        for item in original:
            meta = mapping[item["sample_id"]]
            applicable = item["standard"].startswith("I will give you an unanswerable question,")
            if applicable != meta["question_id"].endswith("_abs"):
                raise ValueError("Abstention type disagrees with source rubric")
            if digest({k: v for k, v in item.items() if k != "input_sha256"}) != item["input_sha256"]:
                raise ValueError("Original input hash mismatch")
            new = {"sample_id": uuid.uuid4().hex, "question": item["question"],
                   "reference": item["reference"], "response": item["response"],
                   "original_standard": item["standard"], "applicable": applicable,
                   "scoring_version": VERSION, "policy_sha256": digest(frozen)}
            new["input_sha256"] = digest(new)
            queue.append(new)
            private.append({"sample_id": new["sample_id"], "original_sample_id": item["sample_id"],
                            "original_input_sha256": item["input_sha256"], "old_label": old[item["sample_id"]]["label"],
                            "batch": batch, **meta})
            private[-1]["sample_id"] = new["sample_id"]
    if len(queue) != 70 or len({r["sample_id"] for r in queue}) != 70:
        raise ValueError("Expected exactly 70 unique answers")
    queue.sort(key=lambda r: r["sample_id"])
    write(out / "queue.hidden.json", queue)
    write(out / "mapping.private.json", private)
    write(out / "source.json", {"path": str(source.resolve()), "queue_sha256": digest(queue)})


def validate(queue, document, policy_hash):
    if (document.get("version") != VERSION or document.get("queue_sha256") != digest(queue)
            or document.get("policy_sha256") != policy_hash):
        raise ValueError("Review version or hash mismatch")
    if document.get("reviewer", {}).get("type") != "external_ai_app" or document["reviewer"].get("human_gold") is not False:
        raise ValueError("AI provenance required")
    expected = {r["sample_id"]: r for r in queue if r["applicable"]}
    results = {}
    for r in document["results"]:
        sid = r["sample_id"]
        if sid not in expected or sid in results:
            raise ValueError("Unknown/non-applicable/duplicate ID")
        item = expected[sid]
        if (r["input_sha256"] != item["input_sha256"] or
                item["input_sha256"] != digest({k: v for k, v in item.items() if k != "input_sha256"})):
            raise ValueError("Input hash mismatch")
        if r["label"] not in ("Yes", "No", "uncertain") or not r.get("reason", "").strip():
            raise ValueError("Explicit label and reason required")
        if not r.get("clauses") or not set(r["clauses"]) <= {"S1", "S2", "S3", "S4"}:
            raise ValueError("Applicable clause required")
        results[sid] = r
    if set(results) != set(expected):
        raise ValueError("Missing applicable reviews")
    return results


def counts(rows, key):
    c = Counter(r[key] for r in rows)
    return {"Yes": c["Yes"], "No": c["No"], "uncertain": c["uncertain"],
            "valid": c["Yes"] + c["No"], "total": len(rows)}


def mixed(labels):
    return len(labels) == 2 and set(labels) == {"Yes", "No"}


def paired(rows, key):
    result = {k: [] for k in ("both_correct", "only_B2", "only_B0", "both_wrong", "incomparable")}
    grouped = defaultdict(dict)
    for r in rows:
        grouped[r["question_id"]][r["condition"]] = r[key]
    for qid, labels in grouped.items():
        a, b = labels["B0"], labels["B2-rules-01.json"]
        category = ("incomparable" if "uncertain" in (a, b) else
                    "both_correct" if a == b == "Yes" else "only_B2" if b == "Yes" else
                    "only_B0" if a == "Yes" else "both_wrong")
        result[category].append(qid)
    return result


def summarize(out):
    source = Path(read(out / "source.json")["path"])
    if snapshot(source) != read(out / "source-hashes.before.json"):
        raise ValueError("Historical source changed")
    queue = read(out / "queue.hidden.json")
    if digest(queue) != read(out / "source.json")["queue_sha256"]:
        raise ValueError("Queue changed")
    policy_hash = digest(read(out / "policy.frozen.json"))
    if policy_hash != read(out / "freeze.json")["policy_sha256"]:
        raise ValueError("Frozen policy changed")
    reviews = validate(queue, read(out / "reviews.json"), policy_hash)
    mapping = {r["sample_id"]: r for r in read(out / "mapping.private.json")}
    validation_rows = [r for c in read(source / "smoke/validation-plan.frozen.json")["conditions"]
                       for r in read(source / "smoke/validation" / (c["name"] + ".json"))]
    derived = []
    for item in queue:
        m = mapping[item["sample_id"]]
        review = reviews.get(item["sample_id"])
        condition = validation_rows[m["output_index"]]["condition"] if m["batch"] == 4 else "training"
        derived.append({**item, "question_id": m["question_id"], "attempt": m["attempt"], "condition": condition,
                        "original_input_sha256": m["original_input_sha256"], "old_label": m["old_label"],
                        "new_label": review["label"] if review else m["old_label"],
                        "clauses": review["clauses"] if review else ["S5"],
                        "reason": review["reason"] if review else "非适用项：沿用v1判分，未重新评审答案质量。",
                        "assessment": "new_external_ai_review" if review else "carried_forward_v1",
                        "human_acceptance": None})
    train = [r for r in derived if r["condition"] == "training"]
    val = [r for r in derived if r["condition"] != "training"]
    groups = defaultdict(list)
    for r in train:
        groups[r["question_id"]].append(r)
    eligibility = [{"question_id": q, "old": mixed([r["old_label"] for r in rs]),
                    "new": mixed([r["new_label"] for r in rs]),
                    "old_labels": [r["old_label"] for r in sorted(rs, key=lambda r: r["attempt"])],
                    "new_labels": [r["new_label"] for r in sorted(rs, key=lambda r: r["attempt"])]} for q, rs in groups.items()]
    scores = {c: {v: counts([r for r in val if r["condition"] == c], key)
                  for v, key in (("v1", "old_label"), ("v2", "new_label"))} for c in sorted({r["condition"] for r in val})}
    candidates = read(source / "smoke/selection.json")["B2_candidates"]
    eligible = [c for c in candidates if scores[c["reuses_condition"]]["v2"]["valid"] == 10]
    winner = max(eligible, key=lambda c: scores[c["reuses_condition"]]["v2"]["Yes"]) if eligible else None
    summary = {"version": VERSION, "analysis_only": True, "local_requests": 0,
               "applicable": len(reviews), "carried_forward": len(derived) - len(reviews),
               "training": {v: counts(train, k) for v, k in (("v1", "old_label"), ("v2", "new_label"))},
               "training_group_eligibility": eligibility, "validation": scores,
               "paired": {v: paired(val, k) for v, k in (("v1", "old_label"), ("v2", "new_label"))},
               "changes": [{k: r[k] for k in ("question_id", "attempt", "condition", "old_label", "new_label")} for r in derived if r["old_label"] != r["new_label"]],
               "hypothetical_selection": {"file": winner["file"] if winner else None, "not_official": True,
                                          "reason": "full coverage; max correct; earliest checkpoint on tie"},
               "original_selection": read(source / "smoke/selection.json")["status"],
               "human_acceptance": None}
    # Refuse a second analysis write; a new review requires a new derived directory.
    if (out / "derived.json").exists() or (out / "summary.json").exists():
        raise FileExistsError("Derived results already exist")
    write(out / "derived.json", derived)
    write(out / "summary.json", summary)
    write(out / "source-hashes.after.json", snapshot(source))
    print({k: summary[k] for k in ("applicable", "carried_forward", "training", "validation", "paired", "hypothetical_selection")})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("export", "summarize"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--source", type=Path)
    args = p.parse_args()
    if args.mode == "export":
        if args.source is None:
            p.error("export requires --source")
        export(args.source, args.out, ROOT / "configs/external-ai-strict-abstention-v2.json")
    else:
        summarize(args.out)
