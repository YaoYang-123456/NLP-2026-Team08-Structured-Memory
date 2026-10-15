"""Export only the five training questions for manual review, including interrupted runs."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
from metamem_pilot.data import read, write_atomic
from metamem_pilot.pipeline import load_labels, load_split, summarize
from run_pilot import call_events, usage_summary


def export_review(session, data=ROOT / "data/pilot"):
    smoke = session / "smoke"
    run = read(smoke / "run.json") if (smoke / "run.json").exists() else {"status": "not_started", "simulated": False}
    recorded_status = run["status"]
    if recorded_status == "running":
        run["status"] = "incomplete"  # A snapshot cannot assert completion or that a worker is still alive.
    inputs = load_split(data, "train")[:5]
    labels = load_labels(data, "train")
    events = call_events(smoke / "calls.jsonl")
    outputs = read(smoke / "rollouts-00.json") if (smoke / "rollouts-00.json").exists() else []
    results = {(r["question_id"], r["attempt"]): dict(r) for r in outputs}
    pending_path = smoke / "pending-call.json"
    pending = read(pending_path) if pending_path.exists() else None
    if pending and any(all(e.get(k) == pending.get(k) for k in ("started_utc", "stage", "question_id", "attempt")) for e in events):
        # A hard stop after journal fsync but before marker removal still completed this call.
        pending = None
    for row in inputs:
        for attempt in range(2):
            key = row["question_id"], attempt
            results.setdefault(key, {"question_id": key[0], "task": row["task"], "attempt": attempt,
                                     "status": "not_started", "correct": None, "simulated": run["simulated"]})
    for event in events:
        key = event["question_id"], event["attempt"]
        if key not in results or event["stage"] not in ("answer_train", "judge"):
            continue
        r = results[key]
        prefix = "generation" if event["stage"] == "answer_train" else "judge"
        response_key = "response" if prefix == "generation" else "judge_response"
        if "response" in event:
            r[response_key] = event["response"]
        if event["status"] not in ("ok", "simulated"):
            r["status"] = prefix + ("_interrupted" if event["status"] == "interrupted" else "_failed")
            r["correct"] = None
        elif prefix == "generation":
            r["status"] = "generated"
        else:
            answer = event["response"].strip().lower()
            r["status"] = "valid" if answer in ("yes", "no") else "judge_parse_failed"
            r["correct"] = answer == "yes" if r["status"] == "valid" else None
    if pending:
        key = pending["question_id"], pending["attempt"]
        if key in results and pending["stage"] in ("answer_train", "judge"):
            results[key]["status"] = "request_incomplete"
            results[key]["correct"] = None
    ordered = [results[(r["question_id"], a)] for r in inputs for a in range(2)]
    for result in ordered:
        if result["status"] in ("generating", "judging"):
            result["status"] = "request_incomplete"
            result["correct"] = None
    review = [{"question_id": row["question_id"], "question": row["question"],
               "question_date": row["question_date"], "facts": row["facts"],
               "reference_answer": labels[row["question_id"]],
               "attempts": [results[(row["question_id"], a)] for a in range(2)]} for row in inputs]
    write_atomic(session / "review-inputs.json", review)
    summary = {"run_status": run["status"], "recorded_run_status": recorded_status, "training_smoke_only": True,
               "scores": summarize(ordered, run["simulated"]),
               "usage": usage_summary(smoke / "calls.jsonl"), "pending_call": pending is not None}
    write_atomic(session / "summary.json", summary)
    text = ["TRAINING SMOKE MANUAL REVIEW — not test performance", f"Run status: {run['status']}; simulated: {run['simulated']}"]
    for row in review:
        text += ["", "=" * 72, row["question_id"], row["question_date"], "QUESTION", row["question"], "FACTS"]
        text += [f"[{fact['fact_id']}] {fact['text']}" for fact in row["facts"]]
        text += ["REFERENCE (review/judge only)", row["reference_answer"]]
        for attempt in row["attempts"]:
            text += [f"ATTEMPT {attempt['attempt']}: {attempt['status']}", attempt.get("response") or "[no completed answer]",
                     "JUDGE: " + (attempt.get("judge_response") or "[not scored]")]
    (session / "review.txt").write_text("\n".join(text) + "\n", encoding="utf-8", newline="\n")
    human = session / "human-review.json"
    if not human.exists():
        write_atomic(human, [{"question_id": r["question_id"], "attempt": a, "human_correct": None,
                              "judge_agreement": None, "evidence_missing": None, "notes": ""}
                             for r in inputs for a in range(2)])
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export_review(args.session), indent=2))
