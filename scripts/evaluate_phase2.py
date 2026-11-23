"""Score and summarize verified M/N/A qa-run-v2 batches with E-only labels."""

import argparse
import csv
import hashlib
import http.client
import json
import os
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from evaluate import (
    JUDGE_MODEL,
    JUDGE_SYSTEM,
    JUDGE_URL,
    NoRedirect,
    read_json,
    read_jsonl,
    save_judgments,
    validate_judgment_input,
)

VARIANTS = ("M", "N", "A")
METHOD = "S2"
USAGE_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens",
                "prompt_cache_hit_tokens", "prompt_cache_miss_tokens")


def qid(row):
    return row["sample_id"], row["qa_index"]


def composite(run_id, variant, method, key):
    return run_id, variant, method, key[0], key[1]


def keyed_labels(path):
    rows = read_json(path)
    if not isinstance(rows, list) or not rows:
        raise ValueError("The frozen E label file must be a nonempty JSON array")
    out = {}
    for row in rows:
        if not isinstance(row, dict) or not {"sample_id", "qa_index", "category", "question", "answer"}.issubset(row):
            raise ValueError("Each frozen label needs sample_id, qa_index, category, question and answer")
        key = qid(row)
        if (not isinstance(key[0], str) or not key[0] or type(key[1]) is not int or key[1] < 0 or
                type(row["category"]) is not int or not isinstance(row["question"], str) or
                not isinstance(row["answer"], str)):
            raise ValueError(f"Malformed frozen label: {key}")
        if key in out:
            raise ValueError(f"Duplicate frozen label key: {key}")
        out[key] = row
    return out


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_runs(run_dirs, labels, tokenizer_cache=None):
    """Load three verified, answer-free runs and preserve every planned label key."""
    try:
        from verify_qa_run import verify_run
    except ImportError as exc:
        raise RuntimeError("Phase-two evaluation requires F's merged scripts/verify_qa_run.py (PR #77)") from exc

    runs = {}
    question_set_hashes = set()
    config_hashes = set()
    run_ids = set()
    for run_dir in run_dirs:
        directory = Path(run_dir)
        manifest = read_json(directory / "run.json")
        require(manifest.get("schema_version") == "qa-run-v2", f"Not a qa-run-v2 batch: {directory}")
        require(manifest.get("simulated") is False, f"Mock output cannot be scored: {directory}")
        require(manifest.get("method") == METHOD, f"Expected method={METHOD}: {directory}")
        variant = manifest.get("variant")
        require(variant in VARIANTS, f"Expected variant M, N or A: {directory}")
        require(variant not in runs, f"More than one run supplied for variant {variant}")
        run_id = manifest.get("run_id")
        require(isinstance(run_id, str) and run_id and run_id not in run_ids,
                f"Missing or repeated run_id: {directory}")
        run_ids.add(run_id)

        receipt = verify_run(directory, tokenizer_cache)
        require(receipt.get("verified") is True, f"F's run verifier did not approve {directory}")
        require(receipt.get("run_id") == run_id and receipt.get("variant") == variant,
                f"Run verifier identity mismatch: {directory}")
        require(manifest.get("status") in
                ("completed", "completed_with_failures", "interrupted", "failed"),
                f"Run is not a real final or interrupted batch: {directory}")

        questions = read_jsonl(directory / "inputs.jsonl")
        requests = read_jsonl(directory / "requests.jsonl")
        calls = read_jsonl(directory / "calls.jsonl")
        predictions = read_jsonl(directory / "predictions.jsonl")
        require(_file_hash(directory / "inputs.jsonl") == manifest.get("input_snapshot_sha256"),
                f"Input snapshot hash mismatch: {directory}")
        require(_file_hash(directory / "requests.jsonl") == manifest.get("requests_sha256"),
                f"Request snapshot hash mismatch: {directory}")
        require(len(questions) == len(requests) == manifest.get("planned_questions") == len(labels),
                f"Planned denominator does not match E labels: {directory}")
        require(len(calls) == len(predictions) == manifest.get("processed_questions"),
                f"Processed output count mismatch: {directory}")

        input_by_key = {}
        request_by_key = {}
        prediction_by_key = {}
        for row in questions:
            key = qid(row)
            if key in input_by_key:
                raise ValueError(f"Duplicate input key in {directory}: {key}")
            label = labels.get(key)
            require(label is not None, f"Run contains a question outside the frozen E labels: {key}")
            require(row.get("question") == label["question"] and row.get("category") == label["category"],
                    f"Question or category differs from frozen E labels: {key}")
            require(not {"answer", "reference_answer", "gold_answer", "evidence"}.intersection(row),
                    f"Answer annotations leaked into QA input: {key}")
            input_by_key[key] = row
        require(set(input_by_key) == set(labels), f"Run's planned questions differ from E labels: {directory}")

        for row in requests:
            key = qid(row)
            identity = composite(run_id, variant, METHOD, key)
            require(key in input_by_key and key not in request_by_key,
                    f"Duplicate or unknown request key in {directory}: {key}")
            require(tuple(row.get(field) for field in
                          ("run_id", "variant", "method", "sample_id", "qa_index")) == identity,
                    f"Request identity mismatch in {directory}: {key}")
            request_by_key[key] = row
        require(set(request_by_key) == set(labels), f"Request snapshot omits planned E labels: {directory}")

        for call, prediction in zip(calls, predictions):
            key = qid(prediction)
            identity = composite(run_id, variant, METHOD, key)
            require(key in input_by_key and key not in prediction_by_key,
                    f"Duplicate or unknown prediction key in {directory}: {key}")
            for row in (call, prediction):
                require(tuple(row.get(field) for field in
                              ("run_id", "variant", "method", "sample_id", "qa_index")) == identity,
                        f"Prediction identity mismatch in {directory}: {key}")
            source = input_by_key[key]
            require(prediction.get("question") == source["question"] and
                    prediction.get("category") == source["category"] and
                    prediction.get("contexts") == source["contexts"],
                    f"Prediction input differs from frozen QA input: {key}")
            require(call.get("request") == request_by_key[key].get("request") and
                    call.get("request_sha256") == request_by_key[key].get("request_sha256"),
                    f"Actual call differs from prepared request: {key}")
            require(call.get("prediction") == prediction.get("prediction") and
                    call.get("status") == prediction.get("status") and
                    call.get("usage") == prediction.get("usage"),
                    f"Call and prediction records disagree: {key}")
            prediction_by_key[key] = prediction

        question_set_hashes.add(manifest.get("question_set_sha256"))
        config_hashes.add(manifest.get("config_sha256"))
        runs[variant] = {"directory": str(directory), "manifest": manifest,
                         "questions": input_by_key, "requests": request_by_key,
                         "predictions": prediction_by_key}

    require(set(runs) == set(VARIANTS), "Supply exactly one real M, N and A run")
    require(len(question_set_hashes) == 1 and None not in question_set_hashes,
            "M/N/A use different frozen question sets")
    require(len(config_hashes) == 1 and None not in config_hashes,
            "M/N/A use different model or prompt configurations")
    return runs


def load_support_annotations(path, labels):
    if path is None:
        return None
    rows = read_json(path)
    if not isinstance(rows, list):
        raise ValueError("Support annotations must be a JSON array")
    annotations = {}
    for row in rows:
        key = qid(row)
        if key in annotations or key not in labels:
            raise ValueError(f"Duplicate or unknown support annotation key: {key}")
        units = row.get("units")
        if (not isinstance(row.get("scope"), str) or not isinstance(units, list) or
                any(not isinstance(unit, dict) or not isinstance(unit.get("name"), str) or
                    not isinstance(unit.get("alternatives"), list) or not unit["alternatives"]
                    for unit in units)):
            raise ValueError(f"Malformed support annotation: {key}")
        for unit in units:
            for alternative in unit["alternatives"]:
                if (not isinstance(alternative, list) or not alternative or
                        any(not isinstance(part, dict) or not isinstance(part.get("id"), str) or
                            not isinstance(part.get("quote"), str) or not part["quote"]
                            for part in alternative)):
                    raise ValueError(f"Malformed support alternative: {key} / {unit['name']}")
        annotations[key] = row
    require(set(annotations) == set(labels), "Support annotations must cover exactly the frozen question set")
    return annotations


def _support_for(prediction, annotation):
    context_texts = defaultdict(list)
    for context in (prediction or {}).get("contexts", []):
        for source_id in context.get("source_ids", []):
            context_texts[source_id].append(context.get("text", ""))
    covered = []
    for unit in annotation["units"]:
        found = any(all(part["id"] in context_texts and
                        any(part["quote"] in text for text in context_texts[part["id"]])
                        for part in alternative)
                    for alternative in unit["alternatives"])
        if found:
            covered.append(unit["name"])
    names = [unit["name"] for unit in annotation["units"]]
    return {"scope": annotation["scope"], "covered": covered,
            "uncovered": [name for name in names if name not in covered], "total": len(names),
            "contexts_available": prediction is not None}


def _judge_record(identity, prediction, label):
    if prediction is None:
        return {**identity, "status": "generation_missing", "correct": None, "judgment": None,
                "request": None, "usage": None, "generation_usage": None, "seconds": None}
    if prediction.get("status") != "ok":
        return {**identity, "status": "generation_" + str(prediction.get("status", "unknown")),
                "correct": None, "judgment": None, "request": None,
                "usage": None, "generation_usage": prediction.get("usage"), "seconds": None}
    user_data = {"question": prediction["question"], "reference_answer": label["answer"],
                 "model_answer": prediction["prediction"]}
    payload = {"model": JUDGE_MODEL,
               "messages": [{"role": "system", "content": JUDGE_SYSTEM},
                            {"role": "user", "content": json.dumps(user_data, ensure_ascii=False)}],
               "thinking": {"type": "disabled"}, "temperature": 0, "top_p": 1,
               "max_tokens": 16, "stream": False}
    serialized = json.dumps(user_data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {**identity, "status": "pending", "correct": None, "judgment": None,
            "raw_response": None, "usage": None, "seconds": None,
            "generation_usage": prediction.get("usage"),
            "returned_model": None, "finish_reason": None, "http_status": None,
            "error": None, "request": payload,
            "input_sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
            "started_utc": datetime.now(timezone.utc).isoformat()}


def run_phase2_judge(runs, labels, output_path):
    """Make one no-retry fixed judge call per successful M/N/A answer."""
    output_path = Path(output_path)
    if output_path.exists():
        raise ValueError("Judgment output exists; select a fresh E-only output path")
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError("Set DEEPSEEK_API_KEY in the local environment before --judge-api")
    ordered = []
    for variant in VARIANTS:
        run = runs[variant]
        for key, label in labels.items():
            identity = {"run_id": run["manifest"]["run_id"], "variant": variant,
                        "method": METHOD, "sample_id": key[0], "qa_index": key[1]}
            ordered.append(_judge_record(identity, run["predictions"].get(key), label))
    document = {"schema_version": "phase2-judgments-v1",
                "metadata": {"adjudicator": JUDGE_MODEL, "status": "running",
                             "endpoint": JUDGE_URL, "temperature": 0, "top_p": 1,
                             "max_tokens": 16, "thinking": "disabled", "retries": 0,
                             "run_ids": {v: runs[v]["manifest"]["run_id"] for v in VARIANTS},
                             "started_utc": datetime.now(timezone.utc).isoformat()},
                "items": ordered}
    save_judgments(output_path, document)
    opener = urllib.request.build_opener(NoRedirect())
    for result in ordered:
        if result["status"] != "pending":
            continue
        result["started_utc"] = datetime.now(timezone.utc).isoformat()
        started = time.perf_counter()
        try:
            payload = result["request"]
            request = urllib.request.Request(
                JUDGE_URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key},
                method="POST")
            with opener.open(request, timeout=60) as response:
                body = json.load(response)
            if not isinstance(body, dict):
                raise ValueError("invalid_judge_response")
            result["usage"] = body.get("usage")
            result["returned_model"] = body.get("model")
            choice = body["choices"][0]
            result["finish_reason"] = choice.get("finish_reason")
            answer = choice["message"].get("content")
            result["raw_response"] = answer
            normalized = answer.strip().lower().rstrip(".! ") if isinstance(answer, str) else ""
            if choice.get("finish_reason") != "stop":
                result["error"] = "non_stop_finish"
            elif normalized not in ("yes", "no"):
                result["error"] = "invalid_judgment_format"
            else:
                result.update(status="scored", judgment=normalized, correct=(normalized == "yes"))
            if result["error"]:
                result["status"] = "judge_failed"
        except KeyboardInterrupt:
            result.update(status="interrupted", error="KeyboardInterrupt")
            document["metadata"]["status"] = "interrupted"
            raise
        except (urllib.error.URLError, http.client.HTTPException, OSError,
                ValueError, KeyError, IndexError, TypeError) as exc:
            result.update(status="judge_failed", error=type(exc).__name__)
            if isinstance(exc, urllib.error.HTTPError):
                result["http_status"] = exc.code
                exc.close()
        finally:
            result["seconds"] = time.perf_counter() - started
            save_judgments(output_path, document)
    if document["metadata"]["status"] == "running":
        pending = any(row["status"] == "pending" for row in ordered)
        failed = any(row["status"] in ("judge_failed", "interrupted") for row in ordered)
        document["metadata"]["status"] = ("incomplete" if pending else
                                           "completed_with_failures" if failed else "complete")
    save_judgments(output_path, document)
    return document


def _validated_judgments(path, runs, labels):
    document = read_json(path)
    require(document.get("schema_version") == "phase2-judgments-v1",
            "Expected phase2-judgments-v1 judgment records")
    expected_run_ids = {variant: runs[variant]["manifest"]["run_id"] for variant in VARIANTS}
    require(document.get("metadata", {}).get("run_ids") == expected_run_ids,
            "Judgment file is bound to different M/N/A runs")
    wanted = {}
    for variant in VARIANTS:
        run_id = runs[variant]["manifest"]["run_id"]
        for key in labels:
            wanted[composite(run_id, variant, METHOD, key)] = (variant, key)
    found = {}
    for item in document.get("items", []):
        identity = composite(item.get("run_id"), item.get("variant"), item.get("method"),
                             (item.get("sample_id"), item.get("qa_index")))
        if identity in found or identity not in wanted:
            raise ValueError(f"Duplicate or unexpected judgment identity: {identity}")
        variant, key = wanted[identity]
        prediction = runs[variant]["predictions"].get(key)
        label = labels[key]
        require(item.get("generation_usage") == (prediction.get("usage") if prediction else None),
                f"Answer usage differs from the verified run: {identity}")
        if prediction is not None and prediction.get("status") == "ok":
            validate_judgment_input(prediction, label, item)
            user_data = {"question": prediction["question"], "reference_answer": label["answer"],
                         "model_answer": prediction["prediction"]}
            serialized = json.dumps(user_data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            require(item.get("input_sha256") == hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
                    f"Judgment input hash mismatch: {identity}")
        elif prediction is None:
            require(item.get("status") == "generation_missing", f"Missing prediction status mismatch: {identity}")
        else:
            require(item.get("status") == "generation_" + str(prediction.get("status")),
                    f"Generation failure status mismatch: {identity}")
        status = item.get("status")
        if status == "scored":
            if type(item.get("correct")) is not bool or item.get("judgment") not in ("yes", "no"):
                raise ValueError(f"Malformed scored judgment: {identity}")
        elif item.get("correct") is not None:
            raise ValueError(f"Unscored judgment has a correctness value: {identity}")
        found[identity] = item
    return document, found, wanted


def _aggregate(rows):
    count = len(rows)
    scored = [row for row in rows if row["correct"] is not None]
    correct = sum(row["correct"] is True for row in scored)
    def usage_summary(name, expected_calls):
        usage = [row[name] for row in rows if isinstance(row.get(name), dict)]
        totals = {}
        for field in USAGE_FIELDS:
            values = [item[field] for item in usage
                      if type(item.get(field)) is int and item[field] >= 0]
            totals[field] = sum(values)
            totals[field + "_calls_with_value"] = len(values)
            totals[field + "_calls_without_value"] = expected_calls - len(values)
        return {**totals, "calls_with_usage": len(usage),
                "calls_without_usage": expected_calls - len(usage)}

    answer_seconds = [row["answer_seconds"] for row in rows
                      if isinstance(row.get("answer_seconds"), (int, float))]
    judge_seconds = [row["judge_seconds"] for row in rows
                     if isinstance(row.get("judge_seconds"), (int, float))]
    return {"planned": count, "scored": len(scored), "correct": correct,
            "accuracy_on_scored": correct / len(scored) if scored else None,
            "correct_over_planned": correct / count if count else None,
            "scoring_coverage": len(scored) / count if count else None,
            "generation_statuses": dict(Counter(row["generation_status"] for row in rows)),
            "judge_statuses": dict(Counter(row["score_status"] for row in rows)),
            "abstentions": sum(row["abstained"] is True for row in rows),
            "ordinary_wrong": sum(row["correct"] is False and row["abstained"] is not True for row in rows),
            "answer_usage": usage_summary("usage", count),
            "judge_usage": usage_summary("judge_usage",
                                         sum(row["generation_status"] == "ok" for row in rows)),
            "sum_answer_call_seconds": sum(answer_seconds) if answer_seconds else None,
            "sum_judge_call_seconds": sum(judge_seconds) if judge_seconds else None}


def evaluate_phase2(run_dirs, labels_path, judgments_path, *, support_annotations_path=None,
                    adjudications_path=None, tokenizer_cache=None):
    labels = keyed_labels(labels_path)
    runs = load_runs(run_dirs, labels, tokenizer_cache)
    support = load_support_annotations(support_annotations_path, labels)
    judgment_doc, judgments, wanted = _validated_judgments(judgments_path, runs, labels)

    overrides = {}
    adjudication_doc = read_json(adjudications_path) if adjudications_path else None
    if adjudication_doc:
        for item in adjudication_doc.get("overrides", []):
            key = (item.get("run_id"), item.get("variant"), item.get("method"),
                   item.get("sample_id"), item.get("qa_index"))
            if key not in wanted or key in overrides:
                raise ValueError(f"Duplicate or unknown adjudication: {key}")
            raw = judgments.get(key)
            if (not raw or raw.get("status") != "scored" or item.get("raw_judgment") != raw.get("judgment") or
                    type(item.get("correct")) is not bool or item["correct"] == raw.get("correct") or
                    not isinstance(item.get("rationale"), str) or not item["rationale"].strip()):
                raise ValueError(f"Invalid E adjudication override: {key}")
            overrides[key] = item

    detailed = []
    for variant in VARIANTS:
        run = runs[variant]
        manifest = run["manifest"]
        for key, label in labels.items():
            identity = composite(manifest["run_id"], variant, METHOD, key)
            prediction = run["predictions"].get(key)
            judgment = judgments.get(identity)
            status = prediction.get("status", "missing") if prediction else "missing"
            if prediction is not None and prediction.get("simulated") is True:
                raise ValueError("Mock predictions cannot enter a score report")
            if status != "ok" and judgment and judgment.get("status") == "scored":
                raise ValueError(f"Failed generation has a scored judgment: {identity}")
            raw_correct = judgment.get("correct") if judgment and judgment.get("status") == "scored" else None
            override = overrides.get(identity)
            correct = override["correct"] if override else raw_correct
            support_row = _support_for(prediction, support[key]) if support else None
            detailed.append({
                "run_id": manifest["run_id"], "variant": variant, "method": METHOD,
                "sample_id": key[0], "qa_index": key[1], "category": label["category"],
                "generation_status": status,
                "score_status": "adjudicated" if override else
                    (judgment.get("status", "judge_missing") if judgment else "judge_missing"),
                "correct": correct, "raw_judge_correct": raw_correct,
                "abstained": prediction.get("abstained") if prediction else None,
                "usage": prediction.get("usage") if prediction else None,
                "answer_seconds": prediction.get("seconds") if prediction else None,
                "judge_usage": judgment.get("usage") if judgment else None,
                "judge_seconds": judgment.get("seconds") if judgment else None,
                "support": support_row,
            })

    by_variant = {}
    for variant in VARIANTS:
        rows = [row for row in detailed if row["variant"] == variant]
        by_category = {}
        for category in sorted({row["category"] for row in rows}):
            by_category[str(category)] = _aggregate([row for row in rows if row["category"] == category])
        by_session = {}
        for sample_id in sorted({row["sample_id"] for row in rows}):
            by_session[sample_id] = _aggregate([row for row in rows if row["sample_id"] == sample_id])
        result = {"run_id": runs[variant]["manifest"]["run_id"], **_aggregate(rows),
                  "by_category": by_category, "by_session": by_session}
        if support:
            support_rows = [row for row in rows if row["support"] is not None]
            scopes = sorted({row["support"]["scope"] for row in support_rows})
            result["support_coverage"] = {
                "covered_units": sum(len(row["support"]["covered"]) for row in support_rows),
                "total_units": sum(row["support"]["total"] for row in support_rows),
                "questions_with_contexts": sum(row["support"]["contexts_available"] for row in support_rows),
                "questions_without_contexts": sum(not row["support"]["contexts_available"] for row in support_rows),
                "by_scope": {scope: {
                    "covered_units": sum(len(row["support"]["covered"]) for row in support_rows
                                          if row["support"]["scope"] == scope),
                    "total_units": sum(row["support"]["total"] for row in support_rows
                                       if row["support"]["scope"] == scope),
                    "questions_complete": sum(
                        row["support"]["scope"] == scope and not row["support"]["uncovered"]
                        for row in support_rows),
                    "questions": sum(row["support"]["scope"] == scope for row in support_rows),
                } for scope in scopes},
            }
        by_variant[variant] = result

    paired = {}
    for left_index, left in enumerate(VARIANTS):
        for right in VARIANTS[left_index + 1:]:
            left_rows = {qid(row): row for row in detailed if row["variant"] == left}
            right_rows = {qid(row): row for row in detailed if row["variant"] == right}
            common = [(left_rows[key], right_rows[key]) for key in labels
                      if left_rows[key]["correct"] is not None and right_rows[key]["correct"] is not None]
            paired[f"{left}_vs_{right}"] = {
                "common_scored": len(common),
                "left_wins": sum(a["correct"] is True and b["correct"] is False for a, b in common),
                "right_wins": sum(a["correct"] is False and b["correct"] is True for a, b in common),
                "ties": sum(a["correct"] == b["correct"] for a, b in common),
            }

    public_rows = []
    for row in detailed:
        support_row = row["support"]
        public_rows.append({
            "variant": row["variant"], "run_id": row["run_id"], "method": row["method"],
            "sample_id": row["sample_id"], "qa_index": row["qa_index"],
            "category": row["category"], "generation_status": row["generation_status"],
            "score_status": row["score_status"], "correct": row["correct"],
            "raw_judge_correct": row["raw_judge_correct"], "abstained": row["abstained"],
            "answer_support_covered": (len(support_row["covered"]) if support_row and
                                        support_row["scope"] == "answer_support" else None),
            "answer_support_total": (support_row["total"] if support_row and
                                      support_row["scope"] == "answer_support" else None),
            "uncovered_answer_support_units": (len(support_row["uncovered"]) if support_row and
                                                support_row["scope"] == "answer_support" else None),
            "all_support_covered": len(support_row["covered"]) if support_row else None,
            "all_support_total": support_row["total"] if support_row else None,
            "usage_total_tokens": (row["usage"].get("total_tokens")
                                    if isinstance(row["usage"], dict) else None),
            "judge_total_tokens": (row["judge_usage"].get("total_tokens")
                                   if isinstance(row["judge_usage"], dict) else None),
            "answer_seconds": row["answer_seconds"],
            "judge_seconds": row["judge_seconds"],
        })
    summary = {"schema_version": "phase2-evaluation-v1", "planned_questions": len(labels),
               "planned_category_counts": {str(c): sum(row["category"] == c for row in labels.values())
                                           for c in sorted({row["category"] for row in labels.values()})},
               "judgment_metadata": judgment_doc.get("metadata", {}),
               "adjudication_metadata": adjudication_doc.get("metadata", {}) if adjudication_doc else None,
               "support_annotations_sha256": _file_hash(support_annotations_path) if support_annotations_path else None,
               "cost_note": "Raw provider usage is retained; no approved price schedule was supplied.",
               "variants": by_variant, "paired": paired}
    return summary, public_rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", type=Path, required=True,
                        help="One verified M, N or A run directory; provide this option three times")
    parser.add_argument("--labels", type=Path, required=True,
                        help="E-only frozen labels JSON; keep it and all judgments local")
    parser.add_argument("--judgments", type=Path, help="Existing phase2-judgments-v1 JSON")
    parser.add_argument("--support-annotations", type=Path,
                        help="Optional E-only support-units.json; not needed for held-out scoring")
    parser.add_argument("--adjudications", type=Path, help="Optional E-only human overrides JSON")
    parser.add_argument("--tokenizer-cache", type=Path, help="Pinned local tokenizer cache for F's verifier")
    parser.add_argument("--judge-api", action="store_true",
                        help="Call the fixed DeepSeek judge once per successful prediction; paid requests")
    parser.add_argument("--out", type=Path, required=True, help="New local output directory")
    args = parser.parse_args(argv)
    if args.judge_api and args.judgments:
        parser.error("Use either --judgments or --judge-api, not both")
    if not args.judge_api and not args.judgments:
        parser.error("Provide --judgments or explicitly enable --judge-api")
    if args.out.exists() and any(args.out.iterdir()):
        parser.error("Output directory contains existing artifacts; choose a new local directory")
    args.out.mkdir(parents=True, exist_ok=True)
    labels = keyed_labels(args.labels)
    runs = load_runs(args.run, labels, args.tokenizer_cache)
    judgment_path = args.judgments
    if args.judge_api:
        judgment_path = args.out / "phase2-judgments.json"
        run_phase2_judge(runs, labels, judgment_path)
    summary, rows = evaluate_phase2(args.run, args.labels, judgment_path,
                                    support_annotations_path=args.support_annotations,
                                    adjudications_path=args.adjudications,
                                    tokenizer_cache=args.tokenizer_cache)
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = list(rows[0]) if rows else []
    with (args.out / "per-question.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"out": str(args.out), "planned_questions": summary["planned_questions"],
                      "variants": {v: {"correct": summary["variants"][v]["correct"],
                                      "planned": summary["variants"][v]["planned"],
                                      "scored": summary["variants"][v]["scored"]}
                                    for v in VARIANTS}, "paired": summary["paired"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
