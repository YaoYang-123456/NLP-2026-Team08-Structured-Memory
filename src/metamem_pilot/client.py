"""Local OpenAI-compatible HTTP calls with per-stage provenance; no response cache."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .data import digest

STAGES = {"answer_train", "answer_eval", "judge", "reflect", "propose", "merge"}


class CallError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CallError("Local endpoint redirected; automatic forwarding is disabled")


def validate_config(config):
    if config["backend"] not in ("local", "mock"):
        raise ValueError("No model configured: use an explicitly configured local model or --mock for flow checks")
    if set(config["stages"]) != STAGES:
        raise ValueError("Every call stage must have explicit generation settings")
    for options in config["stages"].values():
        if set(options) != {"temperature", "top_p", "max_tokens"}:
            raise ValueError("Expected temperature, top_p and max_tokens for every stage")
        if not (options["max_tokens"] > 0 and 0 <= options["temperature"] <= 2 and 0 < options["top_p"] <= 1):
            raise ValueError("Invalid generation options")
    if config["backend"] == "local":
        for role in ("answer", "judge"):
            service = config[role]
            url = urllib.parse.urlparse(service["base_url"])
            if (url.scheme != "http" or url.hostname not in ("localhost", "127.0.0.1", "::1") or
                    url.username or url.password or url.query or url.fragment):
                raise ValueError("This pilot only supports explicitly configured loopback services")
            if not service["model"] or "cloud" in service["model"].lower():
                raise ValueError("Specify a locally served model; cloud model tags are not allowed")


class Client:
    def __init__(self, config, log):
        validate_config(config)
        self.config = config
        self.log = Path(log)
        # Ignore system proxy settings for loopback; do not alter the machine's network configuration.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def call(self, stage, prompt, qid, attempt=0):
        role = "judge" if stage == "judge" else "answer"
        service = self.config[role]
        payload = {"model": service["model"], "messages": [{"role": "user", "content": prompt}],
                   **self.config["stages"][stage], "stream": False}
        event = {"stage": stage, "question_id": qid, "attempt": attempt,
                 "backend": self.config["backend"], "service": service,
                 "settings": self.config["stages"][stage], "prompt_sha256": digest(payload),
                 "prompt": prompt, "started_utc": datetime.now(timezone.utc).isoformat(),
                 "usage": None, "status": "pending"}
        start = time.perf_counter()
        try:
            if self.config["backend"] == "mock":
                if stage == "judge":
                    answer = "yes" if attempt % 2 == 0 else "no"
                elif stage in ("propose", "merge"):
                    answer = '[{"operation":"add","content":"MOCK FLOW ONLY: compare event contexts before combining facts."}]'
                else:
                    answer = "MOCK FLOW ONLY: this is not a model response."
                event["status"] = "simulated"
            else:
                request = urllib.request.Request(service["base_url"].rstrip("/") + "/chat/completions",
                                                 data=json.dumps(payload).encode(),
                                                 headers={"Content-Type": "application/json"})
                with self.opener.open(request, timeout=self.config["timeout_seconds"]) as response:
                    body = json.load(response)
                event["usage"] = body.get("usage")
                event["returned_model"] = body.get("model")
                event["system_fingerprint"] = body.get("system_fingerprint")
                choice = body["choices"][0]
                event["finish_reason"] = choice.get("finish_reason")
                answer = choice["message"]["content"]
                event["response"] = answer
                if choice.get("finish_reason") != "stop":
                    raise CallError("non_stop_finish")
                if not isinstance(answer, str) or not answer.strip():
                    raise CallError("empty_response")
                event["status"] = "ok"
            event["response"] = answer
            return answer
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError, CallError) as exc:
            event["status"] = "call_failed"
            event["error_type"] = type(exc).__name__
            if isinstance(exc, urllib.error.HTTPError):
                event["http_status"] = exc.code
            raise CallError(f"{stage} failed ({event['error_type']})") from exc
        finally:
            event["seconds"] = time.perf_counter() - start
            with self.log.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + "\n")
