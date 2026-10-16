"""Judge all 19 saved complete training responses once per template; no answers generated."""
import argparse
import copy
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
from metamem_pilot.client import Client, CallError, RunStopped
from metamem_pilot.data import read, write_atomic, file_hash, digest
from metamem_pilot.judge import ORIGINAL, CLARIFIED, judge_prompt
from metamem_pilot.pipeline import parse_judge_label, JUDGE_PARSER_VERSION
from evening_smoke import api
from run_pilot import usage_summary, fingerprint, call_events

SOURCES = [ROOT / "output/evening-smoke-20261015-1454", ROOT / "output/budget-diagnostic-20261015-2038"]


def save_comparison(path, items):
    # A Windows reader briefly holding the destination can block atomic replacement.
    # Retry only this local write, never a completed model request.
    for attempt in range(5):
        try:
            write_atomic(path, items)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.05)


def restore_judgments(items, prior):
    """Recover this fixed calibration only from its fsynced call journal."""
    restored = 0
    for event in call_events(prior / "calls.jsonl"):
        if event["stage"] != "judge":
            continue
        source, qid, version = event["question_id"].split(":")
        item = next(r for r in items if (r["source"], r["question_id"], r["attempt"]) == (source, qid, event["attempt"]))
        expected = judge_prompt(item["task"], item["question"], item["reference"], item["response"], qid.endswith("_abs"), version)
        if expected != event["prompt"] or version in item["judgments"]:
            raise ValueError("Prior prompt mismatch or duplicate calibration call")
        raw = event.get("response")
        parsed = parse_judge_label(raw) if event["status"] == "ok" else None
        item["judgments"][version] = {"raw": raw, "correct": parsed,
            "status": ("valid" if parsed is not None else "judge_parse_failed") if event["status"] == "ok" else "judge_failed",
            "recovered_from": str(prior / "calls.jsonl")}
        restored += 1
    return restored


def fixed_responses():
    items, excluded, hashes = [], [], {}
    for source in SOURCES:
        inputs = {r["question_id"]: r for r in read(source / "review-inputs.json")}
        calls = [json.loads(line) for line in (source / "smoke/calls.jsonl").read_text(encoding="utf-8").splitlines()]
        for name in ("review-inputs.json", "smoke/rollouts-00.json", "smoke/calls.jsonl"):
            hashes[str(source / name)] = file_hash(source / name)
        for row in read(source / "smoke/rollouts-00.json"):
            key = row["question_id"], row["attempt"]
            answer = next(c for c in calls if c["stage"] == "answer_train" and (c["question_id"], c["attempt"]) == key)
            if answer["status"] != "ok" or answer.get("finish_reason") != "stop":
                excluded.append({"source": source.name, "question_id": key[0], "attempt": key[1], "reason": answer.get("finish_reason")})
                continue
            assert answer["response"] == row["response"]
            inp = inputs[key[0]]
            items.append({"source": source.name, "question_id": key[0], "attempt": key[1],
                          "task": row["task"], "question": inp["question"], "reference": inp["reference_answer"],
                          "facts": inp["facts"], "response": row["response"], "response_sha256": digest(row["response"]),
                          "historical": {"raw": row.get("judge_response"), "status": row["status"], "correct": row["correct"]},
                          "judgments": {}, "human_review": None})
    if len(items) != 19 or len(excluded) != 1:
        raise ValueError("Expected the fixed 19 complete answers and one excluded truncation")
    return items, excluded, hashes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--deadline-epoch", type=float, required=True)
    p.add_argument("--stop-file", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    config = read(args.config)
    items, excluded, hashes = fixed_responses()
    recovered = 0
    if config.get("calibration_prior"):
        prior = Path(config["calibration_prior"])
        prior_run = read(prior / "run.json")
        if prior_run["source_hashes"] != hashes or prior_run["config"] != {k: v for k, v in config.items() if k != "calibration_prior"}:
            raise ValueError("Prior calibration sources/config differ")
        recovered = restore_judgments(items, prior)
    state = {"command": "calibrate", "status": "running", "simulated": False,
             "started_utc": datetime.now(timezone.utc).isoformat(), "config": config,
             "fingerprint": fingerprint(config, ROOT / "data/pilot"),
             "source_hashes": hashes, "excluded": excluded, "max_requests": 39 - recovered,
             "recovered_judgments": recovered,
             "seed": None, "seed_note": "Not sent; interface documents support, no determinism claim",
             "parser_version": JUDGE_PARSER_VERSION, "argv": sys.argv}
    write_atomic(args.out / "run.json", state)
    save_comparison(args.out / "comparison.json", items)
    client = Client(config, args.out / "calls.jsonl", args.deadline_epoch, args.stop_file, max_requests=39 - recovered)
    started = time.monotonic()
    try:
        saved = copy.deepcopy(config["stages"]["answer_eval"])
        config["stages"]["answer_eval"]["max_tokens"] = 8
        try:
            client.call("answer_eval", "Reply with just OK.", "__warmup__")
        finally:
            config["stages"]["answer_eval"] = saved
        loaded = api("/api/ps")
        write_atomic(args.out / "loaded-after-warmup.json", loaded)
        if len(loaded["models"]) != 1 or loaded["models"][0].get("context_length") != 8192:
            raise ValueError("Unexpected loaded context")
        for index, item in enumerate(items):
            # Counterbalance order without selecting answers or repeating any judgment.
            order = (ORIGINAL, CLARIFIED) if index % 2 == 0 else (CLARIFIED, ORIGINAL)
            item["call_order"] = order
            for version in order:
                if version in item["judgments"]:
                    continue
                result = {"status": "not_started", "correct": None, "raw": None}
                item["judgments"][version] = result
                save_comparison(args.out / "comparison.json", items)
                try:
                    prompt = judge_prompt(item["task"], item["question"], item["reference"], item["response"],
                                          item["question_id"].endswith("_abs"), version)
                    raw = client.call("judge", prompt, f"{item['source']}:{item['question_id']}:{version}", item["attempt"])
                    value = parse_judge_label(raw)
                    result.update(raw=raw, correct=value, status="valid" if value is not None else "judge_parse_failed")
                except CallError as exc:
                    result.update(status="judge_failed", error=str(exc))
                except (RunStopped, KeyboardInterrupt):
                    result["status"] = "interrupted"
                    raise
                finally:
                    save_comparison(args.out / "comparison.json", items)
        state["status"] = "completed"
    except (RunStopped, KeyboardInterrupt) as exc:
        state.update(status="interrupted", error=str(exc))
    except Exception as exc:
        state.update(status="failed", error=str(exc))
        raise
    finally:
        state["source_hashes_unchanged"] = all(file_hash(Path(path)) == sha for path, sha in hashes.items())
        state["elapsed_seconds"] = time.monotonic() - started
        state["usage"] = usage_summary(args.out / "calls.jsonl")
        write_atomic(args.out / "run.json", state)


if __name__ == "__main__":
    main()
