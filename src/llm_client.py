"""Shared non-thinking DeepSeek answering; no retries or answer labels."""
import http.client
import json
import math
import os
import string
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

API_URL = "https://api.deepseek.com/chat/completions"
METHODS = ("S0", "S1", "S2")


def validate_config(config):
    fields = {"model", "temperature", "top_p", "max_tokens", "timeout_seconds",
              "system_prompt", "method_prompts"}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError("Expected only the documented QA configuration fields; keep keys in the environment")
    if config["model"] != "deepseek-flash":
        raise ValueError("This experiment uses deepseek-flash for all answering methods")
    for name, lower, upper in (("temperature", 0, 2), ("top_p", 0, 1),
                               ("timeout_seconds", 0, math.inf)):
        value = config[name]
        if (type(value) not in (int, float) or not math.isfinite(value) or
                not lower <= value <= upper or (name != "temperature" and value == 0)):
            raise ValueError("Invalid QA setting: " + name)
    if type(config["max_tokens"]) is not int or not 1 <= config["max_tokens"] <= 393216:
        raise ValueError("max_tokens must be an integer between 1 and 393216")
    if not isinstance(config["system_prompt"], str) or not config["system_prompt"].strip():
        raise ValueError("system_prompt must be nonempty")
    templates = config["method_prompts"]
    if not isinstance(templates, dict) or set(templates) != set(METHODS):
        raise ValueError("Provide an explicit prompt for each of S0, S1 and S2")
    for template in templates.values():
        if not isinstance(template, str):
            raise ValueError("Method prompts must be strings")
        fields = [(field, spec, conversion) for _, field, spec, conversion in
                  string.Formatter().parse(template) if field is not None]
        if ({field for field, _, _ in fields} != {"context", "question"} or
                any(spec or conversion for _, spec, conversion in fields)):
            raise ValueError("Method prompts must contain only plain {context} and {question} placeholders")


def build_messages(config, method, row):
    """Render already validated retrieval rows, preserving their order and full text."""
    context = json.dumps(row["contexts"], ensure_ascii=False)
    return [{"role": "system", "content": config["system_prompt"]},
            {"role": "user", "content": config["method_prompts"][method].format(
                context=context, question=row["question"])}]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the Authorization header to a redirect target.
        raise urllib.error.HTTPError(req.full_url, code, "Redirect refused", headers, fp)


class Client:
    def __init__(self, config, mock=False):
        validate_config(config)
        self.config = config
        self.mock = mock
        self.api_key = None if mock else os.environ.get("DEEPSEEK_API_KEY")
        if not mock and (not self.api_key or not self.api_key.strip()):
            raise ValueError("DEEPSEEK_API_KEY must be set for --execute")
        self.opener = urllib.request.build_opener(NoRedirect())

    def call(self, messages):
        """Return a recorded ok/failed/interrupted/simulated outcome for one request."""
        payload = {"model": self.config["model"], "messages": messages,
                   "thinking": {"type": "disabled"}, "stream": False,
                   **{key: self.config[key] for key in ("temperature", "top_p", "max_tokens")}}
        result = {"started_utc": datetime.now(timezone.utc).isoformat(),
                  "request": payload, "raw_response": None, "prediction": None,
                  "status": "pending", "simulated": self.mock, "usage": None,
                  "returned_model": None, "finish_reason": None, "error": None, "http_status": None}
        start = time.perf_counter()
        try:
            if self.mock:
                result.update(status="simulated", prediction="MOCK FLOW ONLY: no model was called.")
                return result
            request = urllib.request.Request(
                API_URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.api_key},
                method="POST")
            with self.opener.open(request, timeout=self.config["timeout_seconds"]) as response:
                body = json.load(response)
            result["raw_response"] = body
            if not isinstance(body, dict):
                raise ValueError("invalid_response")
            result["usage"] = body.get("usage")
            result["returned_model"] = body.get("model")
            if result["usage"] is not None and not isinstance(result["usage"], dict):
                raise ValueError("invalid_usage")
            choice = body["choices"][0]
            result["finish_reason"] = choice["finish_reason"]
            message = choice["message"]
            answer = message["content"]
            if choice["finish_reason"] != "stop":
                result["error"] = "non_stop_finish"
            elif not isinstance(answer, str) or not answer.strip():
                result["error"] = "empty_response"
            elif message.get("reasoning_content"):
                result["error"] = "unexpected_thinking_response"
            elif not isinstance(result["returned_model"], str) or not result["returned_model"].strip():
                result["error"] = "missing_response_model"
            else:
                result.update(status="ok", prediction=answer)
            if result["error"]:
                result["status"] = "failed"
        except KeyboardInterrupt:
            result.update(status="interrupted", error="KeyboardInterrupt")
        except (urllib.error.URLError, http.client.HTTPException, OSError,
                ValueError, KeyError, IndexError, TypeError) as exc:
            # Provider error bodies and exception text can contain secrets; record only type/status.
            result.update(status="failed", error=type(exc).__name__)
            if isinstance(exc, urllib.error.HTTPError):
                result["http_status"] = exc.code
                exc.close()
        finally:
            result["seconds"] = time.perf_counter() - start
        return result
