import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from llm_client import API_URL, Client, NoRedirect, build_messages, validate_config
from metamem_pilot.data import read
from run_qa import load_inputs, run


def config():
    return read(ROOT / "configs/qa.example.json")


def rows():
    return load_inputs(ROOT / "configs/qa-smoke.inputs.jsonl")


def response(answer="2026-09-30", finish="stop"):
    return {"model": "provider-returned-version", "id": "test-response", "choices": [
        {"finish_reason": finish, "message": {"role": "assistant", "content": answer}}],
        "usage": {"prompt_tokens": 101, "completion_tokens": 9, "total_tokens": 110,
                  "prompt_cache_hit_tokens": 37}}


def response_stream(body):
    return io.BytesIO(json.dumps(body).encode())


def write_inputs(path, inputs):
    path.write_text("".join(json.dumps(row) + "\n" for row in inputs), encoding="utf-8")


class QATests(unittest.TestCase):
    def test_identity_uses_conversation_and_original_qa_index(self):
        self.assertEqual(len(rows()), 2)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "inputs.jsonl"
            duplicate = rows()
            duplicate[1]["qa_index"] = 0
            write_inputs(path, duplicate)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_inputs(path)

    def test_label_annotations_and_unsupported_category_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "inputs.jsonl"
            for field in ("answer", "evidence", "adversarial_answer"):
                bad = rows()
                bad[1][field] = "GOLD MUST NEVER REACH ANSWERING"
                write_inputs(path, bad)
                with self.assertRaises(ValueError):
                    load_inputs(path)
            bad = rows()
            bad[0]["contexts"][0]["evidence"] = ["gold-source"]
            write_inputs(path, bad)
            with self.assertRaises(ValueError):
                load_inputs(path)
            bad = rows()
            bad[0]["category"] = 5
            write_inputs(path, bad)
            with self.assertRaises(ValueError):
                load_inputs(path)

    def test_complete_batch_validated_before_network_or_output_creation(self):
        with tempfile.TemporaryDirectory() as temp, patch("llm_client.urllib.request.build_opener") as opener:
            path = Path(temp) / "input.jsonl"
            bad = rows()
            bad[-1]["answer"] = "gold"
            write_inputs(path, bad)
            with self.assertRaises(ValueError):
                run(path, ROOT / "configs/qa.example.json", "S0", Path(temp) / "out", mock=False)
            opener.assert_not_called()
            self.assertFalse((Path(temp) / "out").exists())

    def test_explicit_config_rejects_secrets_invalid_settings_and_extra_prompt_fields(self):
        for key, value in (("api_key", "secret"), ("temperature", float("nan")),
                           ("max_tokens", True), ("timeout_seconds", 0), ("top_p", 0)):
            bad = config()
            bad[key] = value
            with self.assertRaises(ValueError):
                validate_config(bad)
        for template in ("{context} {question} {answer}", "{context[0]} {question}",
                         "{context!r} {question}", "question only"):
            bad = config()
            bad["method_prompts"]["S2"] = template
            with self.assertRaises(ValueError):
                validate_config(bad)

    def test_prompt_preserves_order_dates_sources_and_method_template(self):
        row = rows()[0]
        row["question"] += " Literal braces: {context}"
        row["contexts"].append({"kind": "synthesis", "source_ids": ["mem:2", "synthetic:D2:3"],
                                "text": "Source time 2026-10-02; a synthesis with {question}."})
        settings = config()
        settings["method_prompts"]["S2"] = "METHOD-SPECIFIC\n{context}\nQUESTION\n{question}"
        validate_config(settings)
        messages = build_messages(settings, "S2", row)
        self.assertEqual(messages[0]["content"], settings["system_prompt"])
        self.assertIn(json.dumps(row["contexts"], ensure_ascii=False), messages[1]["content"])
        self.assertTrue(messages[1]["content"].endswith(row["question"]))
        self.assertNotIn("category", messages[1]["content"])

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-secret"})
    def test_request_disables_thinking_and_records_raw_usage_without_credentials(self):
        client = Client(config())
        body = response()
        with patch.object(client.opener, "open", return_value=response_stream(body)) as send:
            event = client.call(build_messages(config(), "S0", rows()[0]))
        request = send.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, API_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["max_tokens"], 512)
        self.assertEqual(event["status"], "ok")
        self.assertEqual(event["raw_response"], body)
        self.assertEqual(event["usage"], body["usage"])
        self.assertEqual(event["returned_model"], body["model"])
        self.assertNotIn("test-secret", json.dumps(event))
        send.assert_called_once()

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-secret"})
    def test_truncation_empty_malformed_and_thinking_responses_are_not_predictions(self):
        missing_model = response()
        missing_model.pop("model")
        thinking = response()
        thinking["choices"][0]["message"]["reasoning_content"] = "Unexpected reasoning"
        client = Client(config())
        for body in (response(finish="length"), response(answer="  "), {"choices": []}, missing_model,
                     thinking, [], {"choices": [{"message": None}]}):
            with self.subTest(body=body), patch.object(client.opener, "open", return_value=response_stream(body)):
                event = client.call([])
            self.assertEqual(event["status"], "failed")
            self.assertIsNone(event["prediction"])
            self.assertEqual(event["raw_response"], body)
        with patch.object(client.opener, "open", return_value=response_stream(response(finish="length"))):
            self.assertEqual(client.call([])["usage"], response()["usage"])

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-secret"})
    def test_http_timeout_and_invalid_json_fail_once_without_leaking_error_text(self):
        client = Client(config())
        errors = [urllib.error.HTTPError(API_URL, 401, "test-secret", {}, io.BytesIO(b"test-secret")),
                  TimeoutError("test-secret")]
        for error in errors:
            with patch.object(client.opener, "open", side_effect=error) as send:
                event = client.call([])
            self.assertEqual(event["status"], "failed")
            self.assertIsNone(event["usage"])
            self.assertIsNone(event["prediction"])
            self.assertNotIn("test-secret", json.dumps(event))
            send.assert_called_once()
        with patch.object(client.opener, "open", return_value=io.BytesIO(b"not json")):
            self.assertEqual(client.call([])["status"], "failed")

    def test_redirect_is_refused(self):
        request = urllib.request.Request(API_URL, headers={"Authorization": "Bearer secret"})
        with self.assertRaises(urllib.error.HTTPError) as raised:
            NoRedirect().redirect_request(request, None, 307, "redirect", {}, "https://elsewhere.invalid")
        raised.exception.close()

    def test_mock_cli_needs_no_key_and_cannot_be_mistaken_for_real_results(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "out"
            result = subprocess.run([sys.executable, str(ROOT / "scripts/run_qa.py"), "--mock", "--method", "S0",
                                     "--input", str(ROOT / "configs/qa-smoke.inputs.jsonl"), "--out", str(out)],
                                    env={key: value for key, value in os.environ.items() if key != "DEEPSEEK_API_KEY"},
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = read(out / "run.json")
            self.assertEqual(manifest["status"], "simulated")
            self.assertEqual(manifest["successful_questions"], 0)
            self.assertEqual(manifest["simulated_questions"], 2)
            predictions = [json.loads(line) for line in (out / "predictions.jsonl").read_text().splitlines()]
            self.assertEqual([row["qa_index"] for row in predictions], [0, 1])
            self.assertTrue(all(row["simulated"] and row["usage"] is None and row["status"] == "simulated"
                                for row in predictions))

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-secret"})
    def test_partial_failure_keeps_original_denominator_and_later_question(self):
        with tempfile.TemporaryDirectory() as temp, patch("llm_client.urllib.request.build_opener") as factory:
            factory.return_value.open.side_effect = [response_stream(response(finish="length")),
                                                      response_stream(response("reading club"))]
            out = Path(temp) / "out"
            with redirect_stdout(io.StringIO()):
                code = run(ROOT / "configs/qa-smoke.inputs.jsonl", ROOT / "configs/qa.example.json", "S0", out, False)
            self.assertEqual(code, 1)
            manifest = read(out / "run.json")
            self.assertEqual((manifest["planned_questions"], manifest["processed_questions"],
                              manifest["successful_questions"], manifest["failed_questions"]), (2, 2, 1, 1))
            self.assertEqual(manifest["status"], "completed_with_failures")
            predictions = [json.loads(line) for line in (out / "predictions.jsonl").read_text().splitlines()]
            self.assertIsNone(predictions[0]["prediction"])
            self.assertEqual(predictions[1]["prediction"], "reading club")
            self.assertEqual(predictions[0]["usage"], response()["usage"])
            self.assertEqual(factory.return_value.open.call_count, 2)

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-secret"})
    def test_interrupt_records_unfinished_batch_and_returns_130(self):
        with tempfile.TemporaryDirectory() as temp, patch("llm_client.urllib.request.build_opener") as factory:
            factory.return_value.open.side_effect = KeyboardInterrupt()
            out = Path(temp) / "out"
            with redirect_stdout(io.StringIO()):
                code = run(ROOT / "configs/qa-smoke.inputs.jsonl", ROOT / "configs/qa.example.json", "S0", out, False)
            self.assertEqual(code, 130)
            manifest = read(out / "run.json")
            self.assertEqual(manifest["status"], "interrupted")
            self.assertEqual(manifest["planned_questions"], 2)
            self.assertEqual(manifest["processed_questions"], 1)
            self.assertEqual(manifest["interrupted_questions"], 1)
            factory.return_value.open.assert_called_once()

    def test_empty_retrieval_missing_usage_and_output_collision_are_explicit(self):
        with tempfile.TemporaryDirectory() as temp, patch("llm_client.urllib.request.build_opener") as factory:
            path = Path(temp) / "inputs.jsonl"
            inputs = rows()[:1]
            inputs[0]["contexts"] = []
            write_inputs(path, inputs)
            self.assertEqual(load_inputs(path)[0]["contexts"], [])
            out = Path(temp) / "already-exists"
            out.mkdir()
            with self.assertRaises(FileExistsError):
                run(path, ROOT / "configs/qa.example.json", "S0", out, mock=True)
            factory.return_value.open.assert_not_called()
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-secret"}):
            client = Client(config())
            body = response()
            body.pop("usage")
            with patch.object(client.opener, "open", return_value=response_stream(body)):
                event = client.call([])
            self.assertEqual(event["status"], "ok")
            self.assertIsNone(event["usage"])

    def test_question_fingerprint_shared_across_methods_but_context_hash_changes(self):
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(io.StringIO()):
            directory = Path(temp)
            path = directory / "s2.jsonl"
            inputs = rows()
            inputs[0]["contexts"][0]["kind"] = "synthesis"
            inputs[0]["contexts"][0]["text"] = "Different retrieved evidence"
            write_inputs(path, inputs)
            run(ROOT / "configs/qa-smoke.inputs.jsonl", ROOT / "configs/qa.example.json", "S0", directory / "s0", True)
            run(path, ROOT / "configs/qa.example.json", "S2", directory / "s2", True)
            first, second = read(directory / "s0/run.json"), read(directory / "s2/run.json")
            self.assertEqual(first["question_set_sha256"], second["question_set_sha256"])
            self.assertNotEqual(first["input_sha256"], second["input_sha256"])


if __name__ == "__main__":
    unittest.main()
