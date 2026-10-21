"""Download only. No generate/chat/load calls; partial blobs remain resumable."""
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MODEL = "qwen2.5:7b-instruct-q4_K_M"
URL = "http://127.0.0.1:11436"
ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / "output/model-download"
    out.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(URL + "/api/ps", timeout=5) as response:
        if json.load(response)["models"]:
            raise SystemExit("A model is already loaded; download-only precondition failed")
    request = urllib.request.Request(URL + "/api/pull", data=json.dumps({"model": MODEL, "stream": True}).encode(),
                                     headers={"Content-Type": "application/json"})
    result = {"model": MODEL, "started_utc": datetime.now(timezone.utc).isoformat(), "status": "incomplete",
              "generation_requests": 0}
    last_print = 0
    try:
        with opener.open(request, timeout=120) as response, (out / "pull.jsonl").open("a", encoding="utf-8", newline="\n") as log:
            for line in response:
                event = json.loads(line)
                log.write(json.dumps(event) + "\n")
                log.flush()
                if "error" in event:
                    raise RuntimeError(event["error"])
                now = time.monotonic()
                if now - last_print >= 10 or event.get("status") == "success":
                    print(json.dumps(event), flush=True)
                    last_print = now
                result["last_event"] = event
        if result.get("last_event", {}).get("status") != "success":
            raise RuntimeError("Stream ended without success; retain partial files and resume with the same command")
        result["status"] = "downloaded"
    finally:
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (out / "pull-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
