"""Validate explicit file AI reviews and summarize paired repeated answers offline."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from metamem_pilot.data import read, write_atomic, digest, file_hash


def validate_outputs(rows, queue, inputs, conditions):
    expected = {(r['question_id'], repeat, c) for r in inputs for repeat in range(3) for c in conditions}
    actual = [(r['question_id'], r['round'], r['condition']) for r in rows]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("Missing/duplicate/unexpected planned coordinates")
    if len({r['sample_id'] for r in rows}) != len(rows):
        raise ValueError("Duplicate output sample ID")
    by_id = {r['question_id']: r for r in inputs}
    queued = {r['sample_id']: r for r in queue}
    if len(queued) != len(queue) or {r['sample_id'] for r in rows if r['status'] == 'generated'} != set(queued):
        raise ValueError("Generated outputs and queue disagree")
    for row in rows:
        original = by_id[row['question_id']]
        if (row['facts_sha256'] != digest(original['facts']) or
                row['rules_sha256'] != conditions[row['condition']]['rules_sha256']):
            raise ValueError("Output facts/rules changed")
        if row['status'] != 'generated':
            continue
        item = queued[row['sample_id']]
        if (row['response'] != item['response'] or item['question'] != original['question'] or
                item['applicable_strict_abstention'] != row['question_id'].endswith('_abs')):
            raise ValueError("Queue no longer matches generated answer/question")


def validate_review(queue, review, policy):
    if review.get("version") != policy["version"] or review.get("queue_sha256") != digest(queue):
        raise ValueError("Scoring version/queue mismatch")
    if review.get("policy_sha256") != digest(policy):
        raise ValueError("Policy mismatch")
    provenance = review.get("reviewer", {})
    if (provenance.get("type") != "external_ai_app" or provenance.get("human_gold") is not False or
            not provenance.get("identity") or not provenance.get("exact_model_version")):
        raise ValueError("Explicit AI reviewer provenance required")
    expected = {r["sample_id"]: r for r in queue}
    if len(expected) != len(queue):
        raise ValueError("Duplicate queue ID")
    results = {}
    for row in review.get("results", []):
        sid = row.get("sample_id")
        if sid not in expected or sid in results:
            raise ValueError("Unknown or duplicate review ID")
        item = expected[sid]
        if (digest({k: v for k, v in item.items() if k != "input_sha256"}) != item["input_sha256"] or
                row.get("input_sha256") != item["input_sha256"]):
            raise ValueError("Input hash mismatch")
        if row.get("label") not in ("Yes", "No", "uncertain") or not row.get("reason", "").strip():
            raise ValueError("Explicit label/reason required")
        if row.get("unsupported_expansion") not in ("yes", "no", "unknown") or not row.get("quality_reason", "").strip():
            raise ValueError("Separate quality field required")
        results[sid] = row
    if set(results) != set(expected):
        raise ValueError("Missing review; never fill as No")
    return results


def score(rows):
    c = Counter(r.get("label", "missing") for r in rows)
    return {"planned": len(rows), "Yes": c["Yes"], "No": c["No"], "uncertain": c["uncertain"],
            "missing_or_failed": c["missing"], "valid": c["Yes"] + c["No"]}


def pair_category(a, b):
    if a not in ("Yes", "No") or b not in ("Yes", "No"):
        return "incomparable"
    return "both_correct" if a == b == "Yes" else "both_wrong" if a == b == "No" else "only_B2" if b == "Yes" else "only_B0"


def statistics(linked):
    rounds, questions = {}, defaultdict(dict)
    for repeat in range(3):
        rs = [r for r in linked if r["round"] == repeat]
        pair = defaultdict(list)
        for qid in dict.fromkeys(r["question_id"] for r in rs):
            labels = {r["condition"]: r.get("label") for r in rs if r["question_id"] == qid}
            category = pair_category(labels.get("B0"), labels.get("B2"))
            pair[category].append(qid)
            questions[qid][str(repeat)] = {**labels, "pair": category}
        rounds[str(repeat)] = {"scores": {c: score([r for r in rs if r["condition"] == c]) for c in ("B0", "B2")},
                              "paired": dict(pair),
                              "abstention": {c: score([r for r in rs if r["condition"] == c and r["question_id"].endswith("_abs")]) for c in ("B0", "B2")}}
    return {"rounds": rounds, "per_question": dict(questions),
            "overall": {c: score([r for r in linked if r["condition"] == c]) for c in ("B0", "B2")}}


def summarize(out):
    if (out / "summary.json").exists():
        raise FileExistsError("Summary already exists; preserve previous assessments")
    queue, policy = read(out / "queue.hidden.json"), read(out / "policy.frozen.json")
    document = read(out / "reviews.json")
    reviewed = validate_review(queue, document, policy)
    rows = read(out / "answers.json")
    plan = read(out / 'plan.frozen.json')
    input_path = ROOT / 'data/pilot/validation.inputs.json'
    if file_hash(input_path) != plan['validation_inputs_sha256']:
        raise ValueError('Validation inputs changed')
    inputs = read(input_path)
    if len(inputs) != 10:
        raise ValueError('This frozen diagnostic requires ten questions')
    validate_outputs(rows, queue, inputs, plan['conditions'])
    linked = [{**r, **({"label": reviewed[r["sample_id"]]["label"], "assessment": reviewed[r["sample_id"]]} if r["sample_id"] in reviewed else {}),
               "human_acceptance": None} for r in rows]
    summary = {"experiment": "sampling-stability-v1", "scoring_version": policy["version"], "independent_questions": len(inputs),
               "repeats": 3, **statistics(linked),
               "usage": read(out / "run.json")["usage"], "external_ai_reviews": len(reviewed),
               "reviewer": document["reviewer"], "human_acceptance": None, "candidate_selection": "not performed"}
    write_atomic(out / "assessed-answers.json", linked)
    write_atomic(out / "summary.json", summary)
    print(summary)


def conservative_label(primary, audit):
    return primary if primary == audit else "uncertain"


def merge_audit(out, audit):
    targets = [out / name for name in ("assessed-answers.reviewed.json", "summary.reviewed.json", "review-comparison.json")]
    if any(p.exists() for p in targets):
        raise FileExistsError("Preserve existing derived audit")
    queue, policy = read(out / "queue.hidden.json"), read(out / "policy.frozen.json")
    document, audit_doc = read(out / "reviews.json"), read(audit / "reviews.json")
    primary = validate_review(queue, document, policy)
    audit_queue = read(audit / "queue.hidden.json")
    secondary = validate_review(audit_queue, audit_doc, policy)
    originals = {r["sample_id"]: r for r in queue}
    if any(r != originals.get(r["sample_id"]) for r in audit_queue):
        raise ValueError("Audit is not an exact subset of the original queue")
    scope = read(audit / "audit-scope.json")
    if scope["queue_sha256"] != digest(audit_queue):
        raise ValueError("Audit scope changed")
    rows, plan = read(out / "answers.json"), read(out / "plan.frozen.json")
    path = ROOT / "data/pilot/validation.inputs.json"
    if file_hash(path) != plan["validation_inputs_sha256"]:
        raise ValueError("Validation inputs changed")
    validate_outputs(rows, queue, read(path), plan["conditions"])
    linked, changes = [], []
    for row in rows:
        sid = row["sample_id"]
        item = {**row, "human_acceptance": None}
        if sid in primary:
            item.update(label=primary[sid]["label"], assessment=primary[sid])
        if sid in secondary:
            item["audit_assessment"] = secondary[sid]
            item["primary_label"] = item["label"]
            item["label"] = conservative_label(item["label"], secondary[sid]["label"])
            if primary[sid]["label"] != secondary[sid]["label"]:
                changes.append({k: item[k] for k in ("sample_id", "question_id", "round", "condition", "primary_label", "label", "assessment", "audit_assessment")})
        linked.append(item)
    summary = {**read(out / "summary.json"), **statistics(linked),
               "analysis": "conservative independent audit; primary files preserved",
               "primary_reviews_sha256": file_hash(out / "reviews.json"),
               "audit_reviews_sha256": file_hash(audit / "reviews.json"),
               "audit_scope": scope, "audit_reviewer": audit_doc["reviewer"],
               "external_ai_reviews": len(primary) + len(secondary),
               "primary_review_count": len(primary), "targeted_review_count": len(secondary),
               "disagreements": len(changes)}
    write_atomic(targets[0], linked)
    write_atomic(targets[1], summary)
    write_atomic(targets[2], changes)
    print({"overall": summary["overall"], "disagreements": len(changes)})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--audit", type=Path)
    args = p.parse_args()
    merge_audit(args.out, args.audit) if args.audit else summarize(args.out)
