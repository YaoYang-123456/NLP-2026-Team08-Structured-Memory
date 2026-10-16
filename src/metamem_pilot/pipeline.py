"""Bounded B0/B1/B2 learning, validation selection and frozen evaluation."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from third_party.metamem_judge import get_anscheck_prompt
from third_party.metamem_templates import (
    PROBLEM_WITH_META_MEMORY_TEMPLATE, TRAJECTORY_SUMMARY_TEMPLATE,
    META_MEMORY_UPDATE_TEMPLATE, BATCH_META_MEMORY_UPDATE_TEMPLATE,
)
from .client import CallError, RunStopped
from .data import digest, file_hash, read, write, write_atomic

JUDGE_PARSER_VERSION = "single-label-v2"


def parse_judge_label(text):
    """Accept one complete ASCII yes/no label with optional terminal period."""
    match = re.fullmatch(r"(yes|no)\.?", text.strip(), flags=re.IGNORECASE | re.ASCII)
    return match.group(1).lower() == "yes" if match else None


def load_rules(path, kind, budget):
    obj = read(path)  # Missing or malformed files are fatal, including B0.
    if obj.get("kind") != kind:
        raise ValueError("Unexpected rule provenance: " + str(path))
    validate_rules(obj["rules"], budget)
    if kind == "baseline" and obj["rules"]:
        raise ValueError("B0 must have an explicit empty rule list")
    if kind == "manual-fixed" and not obj["rules"]:
        raise ValueError("B1 must not silently become B0")
    return obj


def validate_rules(rules, budget):
    if not isinstance(rules, list) or any(not isinstance(r, str) or not r.strip() for r in rules):
        raise ValueError("Rules must be a list of nonempty strings")
    if len(rules) > 8 or len(rule_text(rules).encode("utf-8")) > budget:
        raise ValueError("Rules exceed the shared limit; no silent truncation")


def rule_text(rules):
    return "\n".join(f"[M{i}] {r}" for i, r in enumerate(rules))


def answer_prompt(row, rules):
    # No labels, task/abstention labels or evidence annotations are accepted here.
    facts = "\n".join(f"[{f['fact_id']}] {f['text']}" for f in row["facts"])
    return PROBLEM_WITH_META_MEMORY_TEMPLATE.format(
        meta_memories=rule_text(rules), memories=facts,
        question=f"Question date: {row['question_date']}\n{row['question']}")


def load_split(data, split):
    manifest = read(data / "manifest.json")
    name = f"{split}.inputs.json"
    if file_hash(data / name) != manifest["files"][name]:
        raise ValueError("Input changed after freezing")
    rows = read(data / name)
    if [r["question_id"] for r in rows] != [r["question_id"] for r in manifest["splits"][split]]:
        raise ValueError("Input IDs differ from frozen split")
    for row in rows:
        if set(row) != {"question_id", "task", "question", "question_date", "facts"}:
            raise ValueError("Unexpected input field; labels must be isolated")
        if any(set(f) != {"fact_id", "text", "score"} for f in row["facts"]):
            raise ValueError("Unexpected fact annotation")
    return rows


def load_labels(data, split):
    manifest = read(data / "manifest.json")
    name = f"{split}.labels.json"
    if file_hash(data / name) != manifest["files"][name]:
        raise ValueError("Labels changed after freezing")
    labels = read(data / name)
    if set(labels) != {r["question_id"] for r in manifest["splits"][split]}:
        raise ValueError("Label IDs differ from frozen split")
    return labels


def evaluate(rows, rules, client, labels_loader, stage="answer_eval", samples=1, condition="B2", progress_path=None):
    outputs = []
    for row in rows:
        for attempt in range(samples):
            result = {"question_id": row["question_id"], "task": row["task"], "attempt": attempt,
                      "condition": condition, "rules_sha256": digest(rules),
                      "simulated": client.config["backend"] == "mock",
                      "facts_sha256": digest(row["facts"]), "status": "not_started", "correct": None}
            outputs.append(result)

    def save_progress():
        if progress_path:
            write_atomic(progress_path, outputs)

    save_progress()
    for result in outputs:
        row = next(r for r in rows if r["question_id"] == result["question_id"])
        result["status"] = "generating"
        save_progress()
        try:
            result["response"] = client.call(stage, answer_prompt(row, rules), row["question_id"], result["attempt"])
            result["status"] = "generated"
        except CallError:
            result["status"] = "generation_failed"
        except (RunStopped, KeyboardInterrupt):
            result["status"] = "generation_interrupted"
            raise
        finally:
            save_progress()
    # Reference answers are loaded only after all answer requests for this evaluation.
    labels = labels_loader()
    for result in outputs:
        if result["status"] != "generated":
            continue
        row = next(r for r in rows if r["question_id"] == result["question_id"])
        prompt = get_anscheck_prompt(row["task"], row["question"], labels[row["question_id"]],
                                     result["response"], row["question_id"].endswith("_abs"))
        result["status"] = "judging"
        save_progress()
        try:
            result["judge_response"] = client.call("judge", prompt, row["question_id"], result["attempt"])
            result["judge_parser_version"] = JUDGE_PARSER_VERSION
            parsed = parse_judge_label(result["judge_response"])
            if parsed is None:
                result["status"] = "judge_parse_failed"
            else:
                result["correct"] = parsed
                result["status"] = "valid"
        except CallError:
            result["status"] = "judge_failed"
        except (RunStopped, KeyboardInterrupt):
            result["status"] = "judge_interrupted"
            raise
        finally:
            save_progress()
    return outputs


def metrics(rows, simulated):
    valid = [r for r in rows if r["status"] == "valid"]
    correct = sum(r["correct"] for r in valid)
    return {"planned": len(rows), "generated": sum("response" in r for r in rows),
            "valid_scores": len(valid), "statuses": dict(Counter(r["status"] for r in rows)),
            "valid_model_scores": 0 if simulated else len(valid),
            "coverage": len(valid) / len(rows) if rows else 0,
            "correct": None if simulated else correct,
            "accuracy_on_valid": None if simulated or not valid else correct / len(valid),
            "correct_over_planned": None if simulated or not rows else correct / len(rows),
            "simulated": simulated}


def summarize(rows, simulated):
    result = metrics(rows, simulated)
    result["by_task"] = {task: metrics([r for r in rows if r["task"] == task], simulated)
                         for task in sorted({r["task"] for r in rows})}
    return result


def partial_groups(rollouts, samples):
    grouped = defaultdict(list)
    for row in rollouts:
        grouped[row["question_id"]].append(row)
    eligible, skipped = {}, {}
    for qid, group in grouped.items():
        if len(group) != samples or any(r["status"] != "valid" for r in group):
            skipped[qid] = "incomplete_or_service_failure"
        elif 0 < sum(r["correct"] for r in group) < samples:
            eligible[qid] = group
        else:
            skipped[qid] = "all_correct" if group[0]["correct"] else "all_wrong"
    return eligible, skipped


def parse_operations(text):
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    operations = json.loads(fenced[-1] if fenced else text)
    if not isinstance(operations, list):
        raise ValueError("Expected an operation array")
    for op in operations:
        if not isinstance(op, dict) or op.get("operation") not in ("add", "update", "delete"):
            raise ValueError("Invalid rule operation")
        allowed = {"operation", "content"} if op["operation"] == "add" else (
            {"operation", "id"} if op["operation"] == "delete" else {"operation", "id", "content"})
        if set(op) != allowed:
            raise ValueError("Invalid operation fields")
    return operations


def apply_operations(rules, ops, budget):
    current = {f"M{i}": r for i, r in enumerate(rules)}
    next_id = len(current)
    touched = set()
    for op in ops:
        if op["operation"] == "add":
            current[f"M{next_id}"] = op["content"]
            next_id += 1
        else:
            key = op["id"]
            if key not in current or key in touched:
                raise ValueError("Missing or multiply modified rule ID")
            touched.add(key)
            if op["operation"] == "delete":
                del current[key]
            else:
                current[key] = op["content"]
    if any(not isinstance(r, str) or len(r.split()) > 30 for r in current.values()):
        raise ValueError("Learned rules must be strings of at most 30 words")
    result = list(dict.fromkeys(current.values()))
    validate_rules(result, budget)
    return result


def learn(data, out, client, limit=None):
    rows = load_split(data, "train")
    if limit is not None:
        rows = rows[:limit]
    labels = load_labels(data, "train")
    rules = []
    candidates = []
    batches = []
    kind = "learned-simulated" if client.config["backend"] == "mock" else "learned"

    def checkpoint(index):
        filename = f"rules-{index:02d}.json"
        write(out / filename, {"kind": kind, "rules": rules, "training_ids": [r["question_id"] for r in rows]})
        candidates.append({"file": filename, "sha256": file_hash(out / filename), "rules_sha256": digest(rules)})

    checkpoint(0)
    for start in range(0, len(rows), 5):
        batch = rows[start:start + 5]
        rollouts = evaluate(batch, rules, client, lambda: labels, "answer_train", 2,
                            progress_path=out / f"rollouts-{start // 5:02d}.json")
        write_atomic(out / f"rollouts-{start // 5:02d}.json", rollouts)
        eligible, skipped = partial_groups(rollouts, 2)
        record = {"batch": start // 5, "eligible_ids": list(eligible), "skipped": skipped,
                  "failures": [], "updated": False}
        proposed = []
        for qid, group in eligible.items():
            row = next(r for r in batch if r["question_id"] == qid)
            memories = "\n".join(f["text"] for f in row["facts"])
            question = f"Question date: {row['question_date']}\n{row['question']}"
            try:
                summaries = [client.call("reflect", TRAJECTORY_SUMMARY_TEMPLATE.format(
                    question=question, memories=memories, answer=labels[qid],
                    response=r["response"], grade=r["correct"]), qid, r["attempt"]) for r in group]
                prompt = META_MEMORY_UPDATE_TEMPLATE.format(question=question, memories=memories,
                    answer=labels[qid], summaries="\n".join(summaries), meta_memories=rule_text(rules))
                ops = parse_operations(client.call("propose", prompt, qid))
                apply_operations(rules, ops, client.config["rule_max_bytes"])
                proposed.append({"question_id": qid, "operations": ops})
            except (CallError, ValueError, TypeError) as exc:
                record["failures"].append({"question_id": qid, "stage": "reflect_or_propose", "error": str(exc)})
        if proposed:
            try:
                prompt = BATCH_META_MEMORY_UPDATE_TEMPLATE.format(
                    existing_meta_memories=rule_text(rules), proposed_updates=json.dumps(proposed, ensure_ascii=False))
                ops = parse_operations(client.call("merge", prompt, f"batch-{start // 5}"))
                new_rules = apply_operations(rules, ops, client.config["rule_max_bytes"])
                record["updated"] = new_rules != rules
                rules = new_rules
            except (CallError, ValueError, TypeError) as exc:
                record["failures"].append({"stage": "merge", "error": str(exc)})
        record["summary"] = summarize(rollouts, client.config["backend"] == "mock")
        batches.append(record)
        checkpoint(start // 5 + 1)
    result = {"candidates": candidates, "batches": batches, "training_ids": [r["question_id"] for r in rows],
              "outcome": ("simulated_rules" if kind.endswith("simulated") else "rules_learned") if rules else "no_rules_learned",
              "simulated": client.config["backend"] == "mock"}
    write(out / "learning.json", result)
    return result


def verify_prior(path, fingerprint, command):
    run = read(path / "run.json")
    if run["fingerprint"] != fingerprint or run["command"] != command or run["status"] != "completed":
        raise ValueError("Prior run config/code/data/backend differs, is incomplete, or has the wrong phase")


def select(data, out, client, training, fingerprint, root):
    verify_prior(training, fingerprint, "learn")
    candidates = read(training / "learning.json")["candidates"]
    rows = load_split(data, "validation")
    scores = []
    seen = set()
    kind = "learned-simulated" if client.config["backend"] == "mock" else "learned"
    for candidate in candidates:
        path = training / candidate["file"]
        if file_hash(path) != candidate["sha256"]:
            raise ValueError("Candidate changed after training")
        rules = load_rules(path, kind, client.config["rule_max_bytes"])["rules"]
        if digest(rules) in seen:
            continue
        seen.add(digest(rules))
        outputs = evaluate(rows, rules, client, lambda: load_labels(data, "validation"))
        write(out / (path.stem + ".validation.json"), outputs)
        score = sum(r["correct"] for r in outputs) if all(r["status"] == "valid" for r in outputs) else None
        scores.append({**candidate, "selection_score": score, "summary": summarize(outputs, kind.endswith("simulated"))})
    valid = [s for s in scores if s["selection_score"] is not None]
    if not valid:
        write(out / "selection-failed.json", scores)
        raise ValueError("No candidate has full validation coverage; no rules frozen")
    # Prefer the earliest checkpoint on a tie, without consulting test labels.
    winner = max(valid, key=lambda s: s["selection_score"])
    frozen = {}
    for name, path, expected_kind in [("B0", root / "configs/rules-b0.json", "baseline"),
                                     ("B1", root / "configs/rules-b1.json", "manual-fixed"),
                                     ("B2", training / winner["file"], kind)]:
        obj = load_rules(path, expected_kind, client.config["rule_max_bytes"])
        write(out / f"{name}.json", obj)
        frozen[name] = {"file": f"{name}.json", "sha256": file_hash(out / f"{name}.json"), "kind": expected_kind}
    result = {"scores": scores, "selected": winner["file"], "frozen": frozen,
              "selection_split": "validation", "simulated": kind.endswith("simulated")}
    write(out / "selection.json", result)
    return result


def test(data, out, client, selection, fingerprint):
    verify_prior(selection, fingerprint, "select")
    frozen = read(selection / "selection.json")["frozen"]
    if set(frozen) != {"B0", "B1", "B2"}:
        raise ValueError("Expected all three frozen conditions")
    rows = load_split(data, "test")
    results = {}
    simulated = client.config["backend"] == "mock"
    for condition in ("B0", "B1", "B2"):
        entry = frozen[condition]
        path = selection / entry["file"]
        if file_hash(path) != entry["sha256"]:
            raise ValueError("Frozen rule file changed")
        rules = load_rules(path, entry["kind"], client.config["rule_max_bytes"])["rules"]
        outputs = evaluate(rows, rules, client, lambda: load_labels(data, "test"), condition=condition)
        write(out / f"{condition}.results.json", outputs)
        results[condition] = outputs
    paired = []
    for a, b in zip(results["B0"], results["B2"]):
        if a["question_id"] != b["question_id"] or a["facts_sha256"] != b["facts_sha256"]:
            raise ValueError("Unpaired comparison")
        paired.append({"question_id": a["question_id"], "valid": a["status"] == b["status"] == "valid",
                       "B0_correct": None if simulated else a["correct"],
                       "B2_correct": None if simulated else b["correct"]})
    result = {"conditions": {k: summarize(v, simulated) for k, v in results.items()},
              "paired_B0_B2": paired, "simulated": simulated}
    write(out / "summary.json", result)
    return result
