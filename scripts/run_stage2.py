"""Run frozen oracle then factorial answers with saved outputs and a shared request cap."""
import argparse
import copy
import os
import sys
import time
import uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
from metamem_pilot.data import read, write_atomic, file_hash, digest
from metamem_pilot.pipeline import answer_prompt, load_labels
from metamem_pilot.external_review import make_item
from metamem_pilot.client import Client, CallError, RunStopped
from run_pilot import usage_summary, call_events
from evening_smoke import api


def recover_logged_answers(slots, events, by, learned):
    recovered=[]
    for row in slots:
        if row['status'] not in ('not_started','generating'):
            continue
        matches=[e for e in events if e['question_id']==row['sample_id']]
        if len(matches)>1:
            raise ValueError('Multiple calls for one sample; manual audit required')
        if matches:
            event=matches[0]
            expected=answer_prompt(by[row['retrieval']][row['question_id']],learned if row['learned'] else [])
            if event['prompt']!=expected:
                raise ValueError('Logged response belongs to another input')
            if event['status']=='ok' and event.get('finish_reason')=='stop':
                row.update(status='generated',response=event['response'],recovered_from_call_log=True)
                recovered.append(row['sample_id'])
            else:
                row.update(status='generation_failed',error='Preserved non-successful dispatched call')
        elif row['status']=='generating':
            row['status']='generation_interrupted'
    return recovered


def prepare_slots(original, improved, oracle):
    slots = []
    by = {"original": original, "role-balanced": improved, "oracle": oracle}
    for phase, orders, ids in [("oracle", [["original", "oracle"], ["oracle", "original"], ["original", "oracle"]], list(oracle)),
                               ("main", [["A", "B", "C", "D"], ["D", "C", "B", "A"], ["C", "A", "D", "B"]], list(original))]:
        for repeat, order in enumerate(orders):
            for qid in ids:
                for condition in order:
                    retrieval = condition if phase == "oracle" else "original" if condition in ("A", "B") else "role-balanced"
                    learned = phase == "main" and condition in ("B", "D")
                    row = by[retrieval][qid]
                    slots.append({"sample_id": uuid.uuid4().hex, "phase": phase, "round": repeat, "condition": condition,
                                  "question_id": qid, "retrieval": retrieval, "learned": learned, "facts_sha256": digest(row["facts"]), "status": "not_started"})
    return slots, by


def export_queue(slots, by, policy, out):
    labels = load_labels(ROOT / "data/pilot", "validation")
    queue = []
    for r in slots:
        if r["status"] != "generated":
            continue
        row = by[r["retrieval"]][r["question_id"]]
        item = make_item(row["question"], labels[r["question_id"]], r["response"], row["task"], r["question_id"].endswith("_abs"))
        item.update(sample_id=r["sample_id"], standard_version=policy["version"], applicable_strict_abstention=r["question_id"].endswith("_abs"), policy_sha256=digest(policy))
        item.pop("input_sha256")
        item["input_sha256"] = digest(item)
        queue.append(item)
    queue.sort(key=lambda x: x["sample_id"])
    write_atomic(out / "queue.hidden.json", queue)
    return queue


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--deadline-epoch", type=float, required=True)
    p.add_argument("--stop-file", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    plan_path = ROOT / "configs/metamem-stage2-plan.json"
    plan, config = read(plan_path), read(args.config)
    if file_hash(args.config) != plan["generation_config_sha256"]:
        raise ValueError("Config changed")
    policy = read(ROOT / plan["policy_file"])
    if digest(policy) != plan["policy_sha256"] or file_hash(ROOT / plan["rules_file"]) != plan["rules_file_sha256"]:
        raise ValueError("Policy/rules changed")
    if file_hash(ROOT / "output/stage2-retrieval/inputs.frozen.json") != plan["inputs_manifest_sha256"]:
        raise ValueError("Input manifest changed")
    if file_hash(ROOT / plan["dinner_quality"]["policy_file"]) != plan["dinner_quality"]["policy_sha256"]:
        raise ValueError("Quality policy changed")
    frozen = read(ROOT / "output/stage2-retrieval/inputs.frozen.json")
    for path, expected in frozen.items():
        if file_hash(ROOT / path) != expected:
            raise ValueError("Frozen input changed: " + path)
    def indexed(path):
        return {r["question_id"]: r for r in read(ROOT / path)}
    original = indexed("data/pilot/validation.inputs.json")
    improved = indexed("output/stage2-retrieval/validation.improved.inputs.json")
    oracle = indexed("output/stage2-preparation/oracle.inputs.json")
    if len(original) != 10 or set(improved) != set(original) or set(oracle) != set(plan["oracle"]["questions"]):
        raise ValueError("Unexpected input IDs")
    if plan["main"]["round_orders"] != [["A","B","C","D"],["D","C","B","A"],["C","A","D","B"]] or plan["main"]["repeats"] != 3 or plan["oracle"]["repeats"] != 3:
        raise ValueError("Plan differs from implemented order")
    slots, by = prepare_slots(original, improved, oracle)
    if len(slots) != plan["planned_answers"]:
        raise ValueError("Planned answer count differs")
    learned = read(ROOT / plan["rules_file"])["rules"]
    for s in slots:
        s["rules_sha256"] = digest(learned if s["learned"] else [])
    resume = os.environ.get("METAMEM_STAGE2_RESUME_FROM")
    consumed = 0
    if resume:
        previous = Path(resume)
        if read(previous / "plan.frozen.json") != plan or read(previous / "inputs.frozen.json") != frozen:
            raise ValueError("Cannot resume a different frozen experiment")
        old = read(previous / "answers.json")
        coordinates = lambda rows: [(r["phase"], r["round"], r["condition"], r["question_id"], r["facts_sha256"], r["rules_sha256"]) for r in rows]
        if coordinates(slots) != coordinates(old):
            raise ValueError("Resume coordinates changed")
        slots = old
        inherited = call_events(previous / "calls.inherited.jsonl") + call_events(previous / "calls.jsonl")
        recovered = recover_logged_answers(slots, inherited, by, learned)
        with (args.out / "calls.inherited.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
            import json
            for event in inherited:
                stream.write(json.dumps(event,ensure_ascii=False)+"\n")
        prior_usage = usage_summary(previous / "calls.jsonl")
        consumed = read(previous / "run.json").get("inherited_requests", 0) + prior_usage["real_requests"] + prior_usage["possibly_inflight_requests"]
        write_atomic(args.out / "resume-source.json", {"path": str(previous.resolve()), "consumed": consumed, "recovered_sample_ids": recovered})
    for name, obj in [("plan.frozen.json",plan), ("inputs.frozen.json",frozen), ("policy.frozen.json",policy), ("answers.json",slots)]:
        write_atomic(args.out / name, obj)
    deadline = min(args.deadline_epoch, plan["inference_deadline_epoch"])
    client = Client(config, args.out / "calls.jsonl", deadline, args.stop_file, plan["max_local_requests"])
    client.dispatched = consumed
    state = {"status": "running", "inherited_requests": consumed, "started_epoch": time.time(), "human_acceptance": None}
    write_atomic(args.out / "run.json", state)
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
            raise ValueError("Unexpected context/model")
        for slot in slots:
            if slot["status"] != "not_started":
                continue
            slot["status"] = "generating"
            write_atomic(args.out / "answers.json", slots)
            try:
                row = by[slot["retrieval"]][slot["question_id"]]
                prompt = answer_prompt(row, learned if slot["learned"] else [])
                slot["response"] = client.call("answer_eval", prompt, slot["sample_id"], slot["round"])
                slot["status"] = "generated"
            except CallError as exc:
                slot.update(status="generation_failed", error=str(exc))
            except (RunStopped, KeyboardInterrupt):
                slot["status"] = "generation_interrupted"
                raise
            finally:
                write_atomic(args.out / "answers.json", slots)
            # Export each completed response so an abrupt stop retains a usable review queue.
            export_queue(slots, by, policy, args.out)
        state.update(status="completed", phase="generation_finished_review_pending")
    except (RunStopped, KeyboardInterrupt) as exc:
        state.update(status="interrupted", error=str(exc))
    except Exception as exc:
        state.update(status="failed", error=str(exc))
        raise
    finally:
        queue = export_queue(slots, by, policy, args.out)
        state.update(usage=usage_summary(args.out / "calls.jsonl"), queued=len(queue), elapsed_seconds=time.monotonic()-started,
                     total_real_requests=client.dispatched)
        write_atomic(args.out / "run.json",state)


if __name__ == "__main__":
    main()
