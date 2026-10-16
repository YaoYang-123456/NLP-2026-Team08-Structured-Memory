"""Freeze a development-only prompt comparison offline; never start a model."""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from metamem_pilot.client import validate_config
from metamem_pilot.data import digest, file_hash, read, write
from metamem_pilot.pipeline import answer_prompt, load_rules, load_split


def prepare(root, out):
    root, out = Path(root), Path(out)
    if out.exists():
        raise FileExistsError("Keep existing frozen artifacts; choose a new output directory")
    spec_path = root / "configs/metamem-prompt-diagnostic.json"
    spec = read(spec_path)
    inputs_path = root / "data/pilot/validation.inputs.json"
    if file_hash(inputs_path) != spec["expected_validation_inputs_sha256"]:
        raise ValueError("Development inputs differ from the stage-two baseline")
    available = {r["question_id"]: r for r in load_split(root / "data/pilot", "validation")}
    ids = spec["question_ids"]
    if len(ids) != 4 or len(set(ids)) != 4 or not set(ids) <= available.keys():
        raise ValueError("Expected four distinct questions from the frozen development split")
    orders = spec["round_orders"]
    if spec["repeats"] != 3 or len(orders) != 3 or any(
            len(order) != 2 or set(order) != {"original", "evidence-bound"} for order in orders):
        raise ValueError("Expected three predeclared rounds of the two prompt conditions")
    if not isinstance(spec["instructions"], str) or not spec["instructions"].strip():
        raise ValueError("Evidence-bound instructions must be explicit")
    config_path = root / spec["generation_config"]
    config = read(config_path)
    validate_config(config)
    rules_path = root / spec["rules_file"]
    rules = load_rules(rules_path, "learned", config["rule_max_bytes"])
    policy_path = root / spec["policy_file"]
    policy = read(policy_path)
    rows = [available[qid] for qid in ids]
    requests = []
    for repeat, order in enumerate(orders):
        for row in rows:
            original = answer_prompt(row, rules["rules"])
            for condition in order:
                prompt = original
                if condition == "evidence-bound":
                    prompt += "\n\n**Evidence and answer requirements:**\n" + spec["instructions"]
                coordinate = {"question_id": row["question_id"], "round": repeat, "condition": condition}
                payload = {"model": config["answer"]["model"],
                           "messages": [{"role": "user", "content": prompt}],
                           **config["stages"]["answer_eval"], "stream": False}
                requests.append({**coordinate, "sample_id": digest({"protocol": spec["version"], **coordinate}),
                                 "facts_sha256": digest(row["facts"]), "rules_sha256": digest(rules["rules"]),
                                 "payload": payload, "payload_sha256": digest(payload),
                                 "status": "not_started", "response": None, "correct": None})
    artifacts = {"inputs.frozen.json": rows, "requests.frozen.json": requests,
                 "generation-config.frozen.json": config, "rules.frozen.json": rules,
                 "policy.frozen.json": policy, "protocol.frozen.json": spec}
    for name, obj in artifacts.items():
        write(out / name, obj)
    plan = {"protocol": spec["version"], "prepared_utc": datetime.now(timezone.utc).isoformat(),
            "status": "prepared_offline_not_run", "real_requests": 0, "planned_answers": len(requests),
            "planned_requests_with_one_warmup": len(requests) + 1,
            "independent_questions": len(rows), "repeats": spec["repeats"],
            "rules_identical_between_conditions": True, "retrieval_identical_between_conditions": True,
            "reference_answers_read": False, "test_inputs_or_labels_read": False,
            "model_installation_verified": False, "human_acceptance": None,
            "execution": "No inference entrypoint in this offline preparation. A new bounded session must verify the local model, service and payloads before generation.",
            "review": "After generation, export hidden-condition reviews under strict-v2; record correctness, cited evidence validity and unsupported assertions separately. Preserve uncertain and missing states; do not count them as No.",
            "interpretation": "All four questions informed prompt design; report only development diagnostics. Added instructions change input length; no claim of isolated semantic causality.",
            "implementation_sha256": {str(p.relative_to(ROOT)): file_hash(p) for p in (
                Path(__file__), ROOT / "src/metamem_pilot/pipeline.py", ROOT / "src/metamem_pilot/client.py",
                ROOT / "third_party/metamem_templates.py")},
            "source_sha256": {str(p.relative_to(root)): file_hash(p) for p in (
                spec_path, inputs_path, root / "data/pilot/manifest.json", config_path, rules_path, policy_path)},
            "artifacts_sha256": {name: file_hash(out / name) for name in artifacts}}
    write(out / "plan.frozen.json", plan)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    plan = prepare(ROOT, args.out)
    print({key: plan[key] for key in ("status", "planned_answers", "real_requests", "reference_answers_read")})


if __name__ == "__main__":
    main()
