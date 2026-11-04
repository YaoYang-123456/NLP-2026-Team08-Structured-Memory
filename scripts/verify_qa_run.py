"""Rebuild a qa-run-v2 request snapshot and check prediction/response bindings offline."""
import argparse
from collections import Counter
import json
from pathlib import Path

from run_qa import ROOT, EvidenceBudget, load_inputs, prepare_question
from llm_client import API_URL, validate_config
from metamem_pilot.data import digest, file_hash, read


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_run(directory, tokenizer_cache=None):
    directory = Path(directory)
    manifest = read(directory / "run.json")
    require(manifest["schema_version"] == "qa-run-v2", "Expected a qa-run-v2 snapshot")
    require(manifest["status"] in ("completed", "completed_with_failures", "simulated", "interrupted", "failed"),
            "Run has not finished")
    config = manifest["config"]
    validate_config(config)
    require(digest(config) == manifest["config_sha256"], "Configuration hash mismatch")
    require(manifest["endpoint"] == API_URL and manifest["http_method"] == "POST", "Endpoint mismatch")
    # Rebuilding must use the code version saved with this run, rather than silently reinterpreting it.
    for name in ("scripts/run_qa.py", "src/llm_client.py", "src/evidence_budget.py", "src/metamem_pilot/data.py"):
        require(file_hash(ROOT / name) == manifest["code_sha256"][name], f"Check out the recorded code: {name}")
    for name, field in (("inputs.jsonl", "input_snapshot_sha256"), ("requests.jsonl", "requests_sha256")):
        require(file_hash(directory / name) == manifest[field], f"Snapshot hash mismatch: {name}")
    rows = load_inputs(directory / "inputs.jsonl")
    requests = jsonl(directory / "requests.jsonl")
    calls = jsonl(directory / "calls.jsonl")
    predictions = jsonl(directory / "predictions.jsonl")
    require(len(rows) == len(requests) == manifest["planned_questions"], "Planned denominator mismatch")
    require(len(calls) == len(predictions) == manifest["processed_questions"] <= len(rows),
            "Processed denominator mismatch")
    require(manifest["planned_posts"] == (0 if manifest["simulated"] else len(rows)), "POST plan mismatch")
    require(digest([{k: r[k] for k in ("sample_id", "qa_index", "question", "category")} for r in rows]) ==
            manifest["question_set_sha256"], "Question set mismatch")
    budget = None
    if "evidence_budget" in config:
        require(manifest["variant"] in ("M", "N", "A", "U"), "Missing phase-two variant")
        budget = EvidenceBudget(config["evidence_budget"]["max_tokens"], tokenizer_cache)
        from importlib.metadata import version
        require(manifest["tokenizer"] == {"name": "cl100k_base", "package": "tiktoken", "version": version("tiktoken")},
                "Tokenizer version mismatch")
    else:
        require(manifest["variant"] is None, "Legacy run must not claim a budgeted variant")
    counts = Counter()
    usage_totals = Counter()
    usage_missing = Counter()
    real_calls = 0
    for i, (row, saved) in enumerate(zip(rows, requests)):
        identity = {"method": manifest["method"], "variant": manifest["variant"], "run_id": manifest["run_id"],
                    "sample_id": row["sample_id"], "qa_index": row["qa_index"]}
        rebuilt = {**identity, **prepare_question(config, manifest["method"], row, budget)}
        require(saved == rebuilt, f"Prepared request mismatch at row {i}")
        if i >= len(calls):
            continue
        call, prediction = calls[i], predictions[i]
        for key in (*identity, "input_row_sha256", "contexts_sha256", "request_sha256"):
            require(call[key] == prediction[key] == rebuilt[key], f"Record binding mismatch at row {i}: {key}")
        require(call["request"] == rebuilt["request"] and digest(call["request"]) == call["request_sha256"],
                f"Actual request mismatch at row {i}")
        for key in ("question", "category", "contexts"):
            require(prediction[key] == row[key], f"Input changed at row {i}: {key}")
        require(prediction["source_ids"] == list(dict.fromkeys(s for c in row["contexts"] for s in c["source_ids"])),
                f"Source mapping mismatch at row {i}")
        expected_tokens = rebuilt["evidence"]["proxy_tokens"] if budget else None
        require(prediction["evidence_proxy_tokens"] == expected_tokens, f"Evidence token mismatch at row {i}")
        for key in ("prediction", "status", "simulated", "usage", "seconds", "started_utc", "returned_model",
                    "finish_reason", "error", "http_status", "abstained"):
            require(call[key] == prediction[key], f"Call/prediction mismatch at row {i}: {key}")
        require(call["simulated"] == manifest["simulated"], f"Simulation flag mismatch at row {i}")
        status, body = call["status"], call["raw_response"]
        require(status in ("ok", "failed", "interrupted", "simulated"), f"Unknown status at row {i}")
        if call["simulated"]:
            require(status == "simulated" and body is None and call["usage"] is None and call["abstained"] is None,
                    f"Mock run contains real-result claims at row {i}")
        else:
            require(status != "simulated", f"Real run contains simulated status at row {i}")
            real_calls += 1
            require(call["usage"] == (body.get("usage") if isinstance(body, dict) else None),
                    f"Usage differs from raw response at row {i}")
            if status == "ok":
                choice = body["choices"][0]
                require(choice["finish_reason"] == call["finish_reason"] == "stop" and
                        choice["message"]["content"] == call["prediction"] and
                        isinstance(call["prediction"], str) and bool(call["prediction"].strip()) and
                        not choice["message"].get("reasoning_content") and call["error"] is None and
                        body["model"] == call["returned_model"], f"Invalid successful response at row {i}")
                require(call["abstained"] == (call["prediction"].strip().rstrip(".").casefold() == "i don't know"),
                        f"Abstention mismatch at row {i}")
            else:
                require(call["prediction"] is None and call["abstained"] is None and call["error"],
                        f"Failed call reported an answer at row {i}")
            for key in ("prompt_tokens", "completion_tokens", "total_tokens", "prompt_cache_hit_tokens",
                        "prompt_cache_miss_tokens"):
                value = call["usage"].get(key) if isinstance(call["usage"], dict) else None
                if type(value) is int and value >= 0:
                    usage_totals[key] += value
                else:
                    usage_missing[key] += 1
        counts[status] += 1
        counts["abstained"] += call["abstained"] is True
    for status, field in (("ok", "successful_questions"), ("failed", "failed_questions"),
                          ("simulated", "simulated_questions"), ("interrupted", "interrupted_questions"),
                          ("abstained", "abstained_questions")):
        require(counts[status] == manifest[field], f"Status count mismatch: {field}")
    if manifest["status"] in ("completed", "completed_with_failures", "simulated"):
        require(len(calls) == len(rows) and not counts["interrupted"], "Completed run has missing/interrupted rows")
        expected = "simulated" if manifest["simulated"] else ("completed_with_failures" if counts["failed"] else "completed")
        require(manifest["status"] == expected, "Batch status mismatch")
    return {"verified": True, "run_id": manifest["run_id"], "method": manifest["method"],
            "variant": manifest["variant"], "status": manifest["status"],
            "planned_questions": len(rows), "processed_questions": len(calls),
            "unprocessed_questions": len(rows) - len(calls), "real_calls": real_calls,
            "abstained_questions": counts["abstained"], "recorded_usage_totals": dict(usage_totals),
            "usage_missing_call_counts": dict(usage_missing)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--tokenizer-cache", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_run(args.run, args.tokenizer_cache), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
