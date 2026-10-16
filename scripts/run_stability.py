"""Generate a predeclared 60-answer sampling diagnostic, then stop the GPU service."""
import argparse
import copy
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
from metamem_pilot.client import Client, CallError, RunStopped
from metamem_pilot.data import read, write_atomic, digest, file_hash
from metamem_pilot.pipeline import load_split, load_labels, answer_prompt
from metamem_pilot.external_review import make_item
from run_pilot import usage_summary
from evening_smoke import api


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--deadline-epoch", type=float, required=True)
    p.add_argument("--stop-file", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    config = read(args.config)
    plan = read(ROOT / "configs/metamem-stability-plan.json")
    if file_hash(args.config) != plan["generation_config_sha256"]:
        raise ValueError("Generation configuration changed after freeze")
    rows = load_split(ROOT / "data/pilot", "validation")
    if file_hash(ROOT / "data/pilot/validation.inputs.json") != plan["validation_inputs_sha256"]:
        raise ValueError("Frozen inputs changed")
    policy = read(ROOT / "configs/external-ai-strict-abstention-v2.json")
    if digest(policy) != plan["policy_sha256"]:
        raise ValueError("Frozen policy changed")
    rules = {}
    for name, spec in plan["conditions"].items():
        path = ROOT / spec["file"]
        if file_hash(path) != spec["file_sha256"]:
            raise ValueError("Frozen rules changed")
        rules[name] = read(path)["rules"]
    write_atomic(args.out / "plan.frozen.json", plan)
    write_atomic(args.out / "policy.frozen.json", policy)
    outputs = [{"question_id": row["question_id"], "round": repeat, "condition": name,
                "status": "not_started", "sample_id": uuid.uuid4().hex,
                "facts_sha256": digest(row["facts"]), "rules_sha256": digest(rules[name])}
               for repeat in range(3) for row in rows
               for name in (["B0", "B2"] if repeat % 2 == 0 else ["B2", "B0"])]
    write_atomic(args.out / "answers.json", outputs)
    state = {"status": "running", "phase": "generation", "started_utc": datetime.now(timezone.utc).isoformat(),
             "max_requests": 70, "planned_requests": 61, "human_acceptance": None}
    write_atomic(args.out / "run.json", state)
    client = Client(config, args.out / "calls.jsonl", args.deadline_epoch, args.stop_file, 70)
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
        by_id = {r["question_id"]: r for r in rows}
        for result in outputs:
            result["status"] = "generating"
            write_atomic(args.out / "answers.json", outputs)
            try:
                result["response"] = client.call("answer_eval", answer_prompt(by_id[result["question_id"]], rules[result["condition"]]),
                                                  result["question_id"], result["round"])
                result["status"] = "generated"
            except CallError as exc:
                result.update(status="generation_failed", error=str(exc))
            except (RunStopped, KeyboardInterrupt):
                result["status"] = "generation_interrupted"
                raise
            finally:
                write_atomic(args.out / "answers.json", outputs)
        state.update(status="completed", phase="generation_complete_review_pending")
    except (RunStopped, KeyboardInterrupt) as exc:
        state.update(status="interrupted", reason=str(exc))
    except Exception as exc:
        state.update(status="failed", reason=str(exc))
        raise
    finally:
        # Only export completed answers; absent/failed answers never become No.
        labels = load_labels(ROOT / "data/pilot", "validation")
        queue = []
        for r in outputs:
            if r["status"] != "generated":
                continue
            row = next(x for x in rows if x["question_id"] == r["question_id"])
            item = make_item(row["question"], labels[r["question_id"]], r["response"], row["task"], r["question_id"].endswith("_abs"))
            item.update(sample_id=r["sample_id"], standard_version=policy["version"],
                        applicable_strict_abstention=r["question_id"].endswith("_abs"), policy_sha256=digest(policy))
            item.pop("input_sha256")
            item["input_sha256"] = digest(item)
            queue.append(item)
        queue.sort(key=lambda r: r["sample_id"])
        write_atomic(args.out / "queue.hidden.json", queue)
        state.update(elapsed_seconds=time.monotonic() - started, usage=usage_summary(args.out / "calls.jsonl"),
                     queued=len(queue), queue_sha256=digest(queue))
        write_atomic(args.out / "run.json", state)


if __name__ == "__main__":
    main()
