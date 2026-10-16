"""Run from the repository root; every invocation gets a new output directory."""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from metamem_pilot.client import Client, RunStopped, validate_config
from metamem_pilot.data import digest, file_hash, read, write_atomic as write
from metamem_pilot.pipeline import learn, load_rules, select, test


def effective_config(args):
    config = read(args.config)
    if args.mock:
        config["backend"] = "mock"
        config["answer"]["model"] = config["judge"]["model"] = "MOCK-NO-MODEL"
    for stage in config["stages"].values():
        for option in ("max_tokens", "temperature", "top_p"):
            if getattr(args, option) is not None:
                stage[option] = getattr(args, option)
    validate_config(config)
    return config


def fingerprint(config, data):
    files = sorted((ROOT / "src").rglob("*.py")) + sorted((ROOT / "third_party").glob("*.py")) + [Path(__file__)]
    return digest({"config": config, "data_manifest": file_hash(data / "manifest.json"),
                   "code": {str(p.relative_to(ROOT)): file_hash(p) for p in files},
                   "B0": file_hash(ROOT / "configs/rules-b0.json"),
                   "B1": file_hash(ROOT / "configs/rules-b1.json")})


def call_events(log):
    raw = log.read_bytes() if log.exists() else b""
    lines = raw.splitlines()
    events = []
    for index, line in enumerate(lines):
        try:
            events.append(json.loads(line))
        except (json.JSONDecodeError, UnicodeDecodeError):
            if index != len(lines) - 1 or raw.endswith(b"\n"):
                raise
            # A process killed during the final append can leave a partial final line.
    return events


def usage_summary(log):
    events = call_events(log)
    pending_path = log.with_name("pending-call.json")
    pending = read(pending_path) if pending_path.exists() else None
    if pending and any(all(e.get(k) == pending.get(k) for k in ("started_utc", "stage", "question_id", "attempt")) for e in events):
        pending = None
    real = [e for e in events if e["backend"] != "mock"]
    usage = [e["usage"] for e in real if e["usage"] is not None]
    prompt_tokens = [u["prompt_tokens"] for u in usage if isinstance(u.get("prompt_tokens"), int)]
    completion_tokens = [u["completion_tokens"] for u in usage if isinstance(u.get("completion_tokens"), int)]
    return {"calls_logged": len(events), "real_requests": len(real), "simulated_calls": len(events) - len(real),
            "possibly_inflight_requests": int(pending is not None),
            "failed_calls": sum(e["status"] == "call_failed" for e in events),
            "interrupted_calls": sum(e["status"] == "interrupted" for e in events),
            "calls_with_reported_usage": len(usage), "calls_without_reported_usage": len(real) - len(usage),
            "reported_prompt_tokens": sum(prompt_tokens) if prompt_tokens else None,
            "reported_completion_tokens": sum(completion_tokens) if completion_tokens else None,
            "calls_missing_prompt_token_count": len(real) - len(prompt_tokens),
            "calls_missing_completion_token_count": len(real) - len(completion_tokens),
            "call_seconds": sum(e["seconds"] for e in events)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["smoke", "learn", "select", "test"])
    p.add_argument("--config", type=Path, default=ROOT / "configs/local.example.json")
    p.add_argument("--data", type=Path, default=ROOT / "data/pilot")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--training-run", type=Path)
    p.add_argument("--selection-run", type=Path)
    p.add_argument("--mock", action="store_true", help="Flow validation only; no real calls or model scores")
    p.add_argument("--deadline-epoch", type=float, help="Stop starting calls at this explicit run deadline")
    p.add_argument("--stop-file", type=Path, help="Stop when this file is created by the user")
    p.add_argument("--max-requests", type=int, help="Hard generation-request cap for this invocation")
    p.add_argument("--warmup", action="store_true", help="Explicit smoke-only load/warmup; never automatic")
    p.add_argument("--max-tokens", type=int, help="Override ALL stages, including judge/reflection/proposal/merge")
    p.add_argument("--temperature", type=float, help="Override ALL stages")
    p.add_argument("--top-p", type=float, help="Override ALL stages")
    args = p.parse_args()
    if args.warmup and args.command != "smoke":
        p.error("--warmup is only available for an explicitly started smoke")
    if args.max_requests is not None and args.max_requests < 1:
        p.error("--max-requests must be positive")
    config = effective_config(args)
    manifest = read(args.data / "manifest.json")
    if file_hash(ROOT / "configs/rules-b1.json") != manifest["manual_rules_sha256"]:
        raise ValueError("Manual rules changed after data preparation")
    for name, kind in (("b0", "baseline"), ("b1", "manual-fixed")):
        load_rules(ROOT / f"configs/rules-{name}.json", kind, config["rule_max_bytes"])
    if args.command == "select" and not args.training_run:
        p.error("select requires --training-run")
    if args.command == "test" and not args.selection_run:
        p.error("test requires --selection-run")
    args.out.mkdir(parents=True, exist_ok=False)
    fp = fingerprint(config, args.data)
    run = {"command": args.command, "argv": sys.argv, "config": config, "fingerprint": fp,
           "data_manifest_sha256": file_hash(args.data / "manifest.json"),
           "started_utc": datetime.now(timezone.utc).isoformat(), "status": "running",
           "simulated": config["backend"] == "mock"}
    write(args.out / "run.json", run)
    client = Client(config, args.out / "calls.jsonl", args.deadline_epoch, args.stop_file,
                    max_requests=args.max_requests)
    start = time.perf_counter()
    try:
        if args.warmup:
            warmup_config = json.loads(json.dumps(config))
            warmup_config["stages"]["answer_eval"]["max_tokens"] = 8
            warmup = Client(warmup_config, args.out / "calls.jsonl", args.deadline_epoch, args.stop_file,
                            max_requests=args.max_requests)
            warmup.call("answer_eval", "Reply with just OK.", "__warmup__")
            client.dispatched += warmup.dispatched
            if config["backend"] == "local":
                with client.opener.open(config["answer"]["base_url"].removesuffix("/v1") + "/api/ps", timeout=5) as response:
                    loaded = json.load(response)
                write(args.out / "loaded-after-warmup.json", loaded)
                match = [m for m in loaded["models"] if m["name"] == config["answer"]["model"]]
                if not match or match[0].get("context_length") != config["server_context_length"]:
                    raise ValueError("Loaded context length differs from the explicit server configuration")
        if args.command in ("smoke", "learn"):
            result = learn(args.data, args.out, client, 5 if args.command == "smoke" else None)
            run["outcome"] = result["outcome"]
        elif args.command == "select":
            select(args.data, args.out, client, args.training_run, fp, ROOT)
        else:
            test(args.data, args.out, client, args.selection_run, fp)
        run["status"] = "completed"
    except (RunStopped, KeyboardInterrupt) as exc:
        run["status"] = "interrupted"
        run["error"] = str(exc) or "KeyboardInterrupt"
    except Exception as exc:
        run["status"] = "failed"
        run["error"] = str(exc)
        raise
    finally:
        run["elapsed_seconds"] = time.perf_counter() - start
        run["usage"] = usage_summary(args.out / "calls.jsonl")
        write(args.out / "run.json", run)
    print(json.dumps({k: run[k] for k in ("command", "status", "simulated", "usage")}, indent=2))


if __name__ == "__main__":
    main()
