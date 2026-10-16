"""Explicitly start one one-hour session, or stop that session. No scheduling."""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from metamem_pilot.data import read, write_atomic
from review_smoke import export_review
from run_pilot import usage_summary

URL = "http://127.0.0.1:11436"
ACTIVE_SECONDS = 50 * 60
TOTAL_SECONDS = 60 * 60


def api(path, payload=None, timeout=10):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(URL + path, data=json.dumps(payload).encode() if payload is not None else None,
                                     headers={"Content-Type": "application/json"})
    with opener.open(request, timeout=timeout) as response:
        return json.load(response)


def service(action, expected_pid=None):
    command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
               str(ROOT / "scripts/ollama_service.ps1"), action]
    if expected_pid is not None:
        command += ["-ExpectedProcessId", str(expected_pid)]
    # A detached Windows server may inherit pipe handles, preventing communicate() from finishing.
    log = ROOT / "output/ollama-service/control.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("ab") as stream:
        return subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                              stdout=stream, stderr=subprocess.STDOUT, timeout=45, check=True)


def stop_reason(child, stop_file, deadline, now=time.monotonic):
    if child.poll() is not None:
        return "worker_finished"
    if stop_file.exists():
        return "user_stop"
    if now() >= deadline:
        return "50_minute_cutoff"
    return None


def finish_run_record(session, reason):
    path = session / "smoke/run.json"
    if path.exists():
        run = read(path)
        if run["status"] == "running":
            run["status"] = "interrupted"
            run["error"] = reason
            run["usage"] = usage_summary(session / "smoke/calls.jsonl")
            write_atomic(path, run)


def cleanup_ok(cleanup):
    return bool(cleanup.get("server_stopped")) and not any(key.endswith("_error") for key in cleanup)


def start(session, config_path=None):
    # All setup, loading and warmup count against the explicit user's start time.
    started = time.monotonic()
    epoch = time.time()
    session.mkdir(parents=True, exist_ok=False)
    config_path = Path(config_path).resolve() if config_path else ROOT / "configs/qwen-library.json"
    config = read(config_path)
    state = {"started_utc": datetime.fromtimestamp(epoch, timezone.utc).isoformat(),
             "active_deadline_epoch": epoch + ACTIVE_SECONDS, "total_deadline_epoch": epoch + TOTAL_SECONDS,
             "status": "starting", "config": config, "cleanup_reserved_seconds": 600}
    write_atomic(session / "session.json", state)
    child = None
    owned = False
    reason = "startup_failed"
    try:
        service("StartRuntime")
        owned = True
        state["service_pid"] = read(ROOT / "output/ollama-service/service.json")["pid"]
        write_atomic(session / "session.json", state)
        if api("/api/version")["version"] != config["ollama_version"]:
            raise ValueError("Ollama version changed; check compatibility before running")
        if api("/api/ps")["models"]:
            raise ValueError("Dedicated service unexpectedly has a loaded model")
        models = api("/api/tags")["models"]
        match = next((m for m in models if m["name"] == config["answer"]["model"]), None)
        expected = read(ROOT / "output/model-download/verified.json")
        if not match or match["digest"] != expected["model"]["digest"]:
            raise ValueError("Downloaded model digest differs or download verification is missing")
        write_atomic(session / "model.json", match)
        command = [sys.executable, "-X", "utf8", str(ROOT / "scripts/run_pilot.py"), "smoke",
                   "--config", str(config_path), "--out", str(session / "smoke"), "--warmup",
                   "--deadline-epoch", str(epoch + ACTIVE_SECONDS), "--stop-file", str(session / "STOP")]
        with (session / "worker.log").open("wb") as log:
            child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            state.update(status="running", worker_pid=child.pid, command=command)
            write_atomic(session / "session.json", state)
            while True:
                reason = stop_reason(child, session / "STOP", started + ACTIVE_SECONDS)
                if reason:
                    break
                time.sleep(0.5)
    except KeyboardInterrupt:
        reason = "keyboard_interrupt"
    except Exception as exc:
        state["error"] = str(exc)
        reason = "startup_or_runtime_error"
    finally:
        (session / "STOP").touch()
        cleanup = {}
        if owned:
            try:
                if child and child.poll() is None:
                    # Abort the current request/runner immediately; don't wait out generation.
                    service("Stop", state["service_pid"])
                    cleanup["forced_server_stop"] = True
                else:
                    # Empty request with keep_alive=0 unloads this model; no generation prompt.
                    cleanup["unload"] = api("/api/generate", {"model": config["answer"]["model"], "keep_alive": 0, "stream": False})
                    cleanup["loaded_after_unload"] = api("/api/ps")
                    if cleanup["unload"].get("done_reason") != "unload" or cleanup["loaded_after_unload"]["models"]:
                        raise RuntimeError("Model unload not confirmed or models remain loaded")
            except Exception as exc:
                cleanup["unload_error"] = str(exc)
            finally:
                try:
                    service("Stop", state["service_pid"])
                    cleanup["server_stopped"] = True
                except Exception as exc:
                    cleanup["server_stop_error"] = str(exc)
        if child and child.poll() is None:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.terminate()
                child.wait(timeout=5)
        finish_run_record(session, reason)
        run_path = session / "smoke/run.json"
        state["run_status"] = read(run_path)["status"] if run_path.exists() else "not_started"
        state.update(status="closed", stop_reason=reason, elapsed_seconds=time.monotonic() - started,
                     cleanup=cleanup, worker_returncode=child.returncode if child else None)
        try:
            result = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,utilization.gpu", "--format=csv"],
                                    capture_output=True, text=True, timeout=10)
            state["gpu_after"] = result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired) as exc:
            state["gpu_check_error"] = str(exc)
        write_atomic(session / "session.json", state)
        export_review(session)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0 if state["run_status"] == "completed" and cleanup_ok(state["cleanup"]) else 2


def stop(session):
    if not (session / "session.json").exists():
        raise ValueError("No session record at this path")
    state = read(session / "session.json")
    if state["status"] == "closed":
        print("This session is already closed; no server was stopped.")
        return
    (session / "STOP").touch()
    if "service_pid" in state:
        service("Stop", state["service_pid"])
    print("Stop requested. The supervisor will preserve outputs and export the review.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["start", "stop"])
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--config", type=Path, help="Explicit run configuration; defaults to the original smoke config")
    args = p.parse_args()
    session = args.out.resolve()
    if args.action == "start":
        sys.exit(start(session, args.config))
    else:
        stop(session)
