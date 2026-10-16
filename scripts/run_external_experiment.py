"""One bounded local training/validation experiment with file-based external AI review."""
import argparse
import copy
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
from metamem_pilot.data import read, write_atomic, digest, file_hash
from metamem_pilot.external_review import ExternalClient, STANDARD
from metamem_pilot.client import RunStopped
from metamem_pilot.pipeline import learn, evaluate, load_split, load_labels, load_rules, summarize
from run_pilot import usage_summary, fingerprint
from evening_smoke import api


def choose_candidate(candidates, scores, count):
    eligible = [c for c in candidates if scores[c["reuses_condition"]]["valid_scores"] == count]
    return max(eligible, key=lambda c: scores[c["reuses_condition"]]["correct"]) if eligible else None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--deadline-epoch", type=float, required=True)
    p.add_argument("--stop-file", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    config = read(args.config)
    data = ROOT / "data/pilot"
    diagnostic = ROOT / "output/external-ai-diagnostic-20261015-2138/adoption.json"
    if read(diagnostic).get("proceed_exploratory") is not True:
        raise ValueError("External diagnostic has not permitted exploration")
    manifest = read(data / "manifest.json")
    if file_hash(ROOT / "configs/rules-b1.json") != manifest["manual_rules_sha256"]:
        raise ValueError("Manual rules changed")
    state = {"command": "external-ai-exploration", "protocol": "external-ai-file-v1", "status": "running",
             "stage": "warmup", "simulated": False, "started_utc": datetime.now(timezone.utc).isoformat(),
             "config": config, "fingerprint": fingerprint(config, data), "standard_version": STANDARD,
             "diagnostic_decision_sha256": file_hash(diagnostic), "max_local_requests": 300,
             "planned_worst_case_local_requests": 165, "human_acceptance": None,
             "selection_protocol": "full coverage only; max correct; earliest checkpoint on tie; no retraining"}
    write_atomic(args.out / "run.json", state)
    client = ExternalClient(config, args.out / "calls.jsonl", args.deadline_epoch, args.stop_file,
                            args.out / "review", 300)
    started = time.monotonic()
    try:
        options = copy.deepcopy(config["stages"]["answer_eval"])
        config["stages"]["answer_eval"]["max_tokens"] = 8
        try:
            client.call("answer_eval", "Reply with just OK.", "__warmup__")
        finally:
            config["stages"]["answer_eval"] = options
        loaded = api("/api/ps")
        write_atomic(args.out / "loaded-after-warmup.json", loaded)
        if len(loaded["models"]) != 1 or loaded["models"][0].get("context_length") != 8192:
            raise ValueError("Unexpected loaded context")
        state["stage"] = "training"
        write_atomic(args.out / "run.json", state)
        training = args.out / "training"
        training.mkdir()
        learning = learn(data, training, client)
        state.update(stage="rule_audit", training_outcome=learning["outcome"])
        write_atomic(args.out / "run.json", state)
        candidates = [{**c, "rules": read(training / c["file"])["rules"]} for c in learning["candidates"]]
        write_atomic(args.out / "rule-audit-request.json", candidates)
        audit = client.wait_file(args.out / "rule-audit.json")
        if audit.get("candidates_sha256") != digest(candidates):
            raise ValueError("Rule audit input hash mismatch")
        entries = audit["results"]
        if len(entries) != len(candidates) or {r["file"] for r in entries} != {c["file"] for c in candidates}:
            raise ValueError("Missing/duplicate rule audits")
        if any(r.get("decision") not in ("include", "exclude") or not r.get("reason") for r in entries):
            raise ValueError("Explicit rule exclusion/inclusion reasons required")
        if args.deadline_epoch - time.time() < 600:
            state.update(status="incomplete", stage="validation_not_started", reason="less than ten minutes active time remains")
            return
        allowed = {r["file"] for r in entries if r["decision"] == "include"}
        conditions = [{"name": "B0", "rules": load_rules(ROOT / "configs/rules-b0.json", "baseline", config["rule_max_bytes"])["rules"]},
                      {"name": "B1", "rules": load_rules(ROOT / "configs/rules-b1.json", "manual-fixed", config["rule_max_bytes"])["rules"]}]
        by_hash = {digest(c["rules"]): c["name"] for c in conditions}
        b2 = []
        for c in candidates:
            if c["file"] not in allowed:
                continue
            if file_hash(training / c["file"]) != c["sha256"]:
                raise ValueError("Training rules changed")
            sha = digest(c["rules"])
            if sha not in by_hash:
                by_hash[sha] = "B2-" + c["file"]
                conditions.append({"name": by_hash[sha], "rules": c["rules"]})
            b2.append({**c, "reuses_condition": by_hash[sha]})
        plan = {"conditions": conditions, "B2_candidates": b2, "standard_version": STANDARD,
                "selection": state["selection_protocol"], "frozen_before_validation": True,
                "max_remaining_local_requests": len(conditions) * 10}
        if client.dispatched + plan["max_remaining_local_requests"] > 300:
            raise RunStopped("Insufficient remaining local request budget")
        write_atomic(args.out / "validation-plan.frozen.json", plan)
        state["stage"] = "validation_generation"
        write_atomic(args.out / "run.json", state)
        validation = args.out / "validation"
        validation.mkdir()
        rows = load_split(data, "validation")
        outputs = []
        client.generate_only = True
        for condition in conditions:
            results = evaluate(rows, condition["rules"], client, lambda: {}, condition=condition["name"],
                               progress_path=validation / (condition["name"] + ".json"))
            outputs.extend(results)
        client.generate_only = False
        state["stage"] = "validation_review"
        write_atomic(args.out / "run.json", state)
        outputs = client.review(rows, outputs, load_labels(data, "validation"))
        scores = {}
        for condition in conditions:
            name = condition["name"]
            results = [r for r in outputs if r["condition"] == name]
            write_atomic(validation / (name + ".json"), results)
            scores[name] = summarize(results, False)
        winner = choose_candidate(b2, scores, len(rows))
        selection = {"scores": scores, "B2_candidates": b2, "selected": winner,
                     "status": "selected" if winner else "no_full_coverage_candidate",
                     "human_acceptance": None, "standard_version": STANDARD}
        if winner:
            write_atomic(args.out / "selected-rules.frozen.json", {"kind": "learned", "rules": winner["rules"],
                         "source": winner["file"], "config": config, "standard_version": STANDARD})
        write_atomic(args.out / "selection.json", selection)
        state.update(status="completed", stage="finished", selection_status=selection["status"])
    except (RunStopped, KeyboardInterrupt) as exc:
        state.update(status="interrupted", error=str(exc))
    except Exception as exc:
        state.update(status="failed", error=str(exc))
        raise
    finally:
        state["elapsed_seconds"] = time.monotonic() - started
        state["usage"] = usage_summary(args.out / "calls.jsonl")
        state["external_ai_reviews"] = client.review_count
        write_atomic(args.out / "run.json", state)


if __name__ == "__main__":
    main()
