"""Scoped low-load checks. All model/server/controller responses are simulated."""
import io
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
from metamem_pilot.client import Client, RunStopped, validate_config
from metamem_pilot.data import read, write
from metamem_pilot.pipeline import evaluate, metrics
import evening_smoke
import review_smoke
from run_pilot import call_events, usage_summary


ROW = {"question_id": "training-fixture", "task": "multi-session", "question": "What happened?",
       "question_date": "2026-10-15", "facts": [{"fact_id": "f1", "text": "fixture fact", "score": 1}]}


class SequenceClient:
    config = {"backend": "mock"}

    def __init__(self, responses):
        self.responses = iter(responses)

    def call(self, *args):
        value = next(self.responses)
        if isinstance(value, BaseException):
            raise value
        return value


class EveningTests(unittest.TestCase):
    def test_service_uses_files_instead_of_inherited_output_pipes(self):
        with tempfile.TemporaryDirectory() as d, patch.object(evening_smoke, "ROOT", Path(d)), \
                patch.object(evening_smoke.subprocess, "run") as run:
            evening_smoke.service("StartRuntime")
            options = run.call_args.kwargs
            self.assertEqual(options["stdin"], subprocess.DEVNULL)
            self.assertNotEqual(options["stdout"], subprocess.PIPE)
            self.assertEqual(options["stderr"], subprocess.STDOUT)
            self.assertTrue((Path(d) / "output/ollama-service/control.log").exists())

    def test_context_is_server_capacity_not_output_limit(self):
        config = read(ROOT / "configs/qwen-library.json")
        validate_config(config)
        self.assertEqual(config["answer"], config["judge"])
        self.assertEqual(config["server_context_length"], 8192)
        self.assertEqual(config["ollama_version"], "0.34.0")
        self.assertTrue(all(s["max_tokens"] < config["server_context_length"] for s in config["stages"].values()))

    def test_stop_and_expired_deadline_prevent_dispatch(self):
        config = read(ROOT / "configs/qwen-library.json")
        with tempfile.TemporaryDirectory() as d:
            stop = Path(d) / "STOP"
            stop.touch()
            for deadline, stop_file in [(None, stop), (time.time() - 1, None)]:
                client = Client(config, Path(d) / "calls.jsonl", deadline, stop_file)
                client.opener = Mock()
                with self.assertRaises(RunStopped):
                    client.call("answer_train", "fixture", "id")
                client.opener.open.assert_not_called()

    def test_generation_interruption_saves_completed_and_unstarted(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "progress.json"
            labels = Mock(return_value={ROW["question_id"]: "secret"})
            with self.assertRaises(RunStopped):
                evaluate([ROW], [], SequenceClient(["saved answer", RunStopped("stop")]), labels,
                         stage="answer_train", samples=3, progress_path=path)
            rows = read(path)
            self.assertEqual([r["status"] for r in rows], ["generated", "generation_interrupted", "not_started"])
            self.assertEqual(rows[0]["response"], "saved answer")
            self.assertTrue(all(r["correct"] is None for r in rows))
            labels.assert_not_called()

    def test_judge_interruption_preserves_prior_score(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "progress.json"
            with self.assertRaises(KeyboardInterrupt):
                evaluate([ROW], [], SequenceClient(["a", "b", "yes", KeyboardInterrupt()]),
                         lambda: {ROW["question_id"]: "truth"}, samples=2, progress_path=path)
            rows = read(path)
            self.assertEqual([r["status"] for r in rows], ["valid", "judge_interrupted"])
            self.assertEqual(metrics(rows, False)["accuracy_on_valid"], 1)
            self.assertIsNone(rows[1]["correct"])

    def test_completed_call_and_keyboard_interrupt_are_durable(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "calls.jsonl"
            client = Client(read(ROOT / "configs/qwen-library.json"), log)
            body = {"model": "fixture", "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
            client.opener = Mock()
            client.opener.open.side_effect = [io.StringIO(json.dumps(body)), KeyboardInterrupt()]
            client.call("answer_train", "fixture", "id")
            with self.assertRaises(KeyboardInterrupt):
                client.call("judge", "fixture", "id")
            self.assertEqual([e["status"] for e in call_events(log)], ["ok", "interrupted"])
            self.assertFalse((Path(d) / "pending-call.json").exists())

    def test_partial_final_journal_line_retains_prior_calls(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "calls.jsonl"
            for tail in (b'{"interrupted":', b'{"response":"\xe4\xb8'):
                log.write_bytes(b'{"stage":"answer_train"}\n' + tail)
                self.assertEqual(call_events(log), [{"stage": "answer_train"}])

    def test_review_recovers_journal_and_preserves_human_notes(self):
        with tempfile.TemporaryDirectory() as d, patch.object(review_smoke, "load_split", return_value=[ROW]) as inputs, \
                patch.object(review_smoke, "load_labels", return_value={ROW["question_id"]: "truth"}) as labels:
            session = Path(d)
            smoke = session / "smoke"
            write(smoke / "run.json", {"status": "running", "simulated": True})
            events = [{"stage": stage, "started_utc": stage, "question_id": ROW["question_id"], "attempt": 0,
                       "status": "simulated", "response": response, "backend": "mock", "usage": None, "seconds": 0}
                      for stage, response in [("answer_train", "saved answer"), ("judge", "yes")]]
            (smoke / "calls.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
            write(smoke / "pending-call.json", events[-1])
            write(session / "human-review.json", [{"notes": "keep my review"}])
            summary = review_smoke.export_review(session)
            self.assertEqual(summary["run_status"], "incomplete")
            self.assertFalse(summary["pending_call"])
            self.assertEqual(summary["usage"]["possibly_inflight_requests"], 0)
            self.assertEqual(summary["scores"]["statuses"], {"valid": 1, "not_started": 1})
            self.assertIsNone(summary["scores"]["accuracy_on_valid"])
            self.assertEqual(read(session / "human-review.json"), [{"notes": "keep my review"}])
            self.assertEqual(inputs.call_args.args[1], "train")
            self.assertEqual(labels.call_args.args[1], "train")

    def test_monotonic_cutoff_and_user_stop(self):
        child = Mock()
        child.poll.return_value = None
        with tempfile.TemporaryDirectory() as d:
            stop = Path(d) / "STOP"
            self.assertIsNone(evening_smoke.stop_reason(child, stop, 3000, now=lambda: 2999))
            self.assertEqual(evening_smoke.stop_reason(child, stop, 3000, now=lambda: 3000), "50_minute_cutoff")
            stop.touch()
            self.assertEqual(evening_smoke.stop_reason(child, stop, 3000, now=lambda: 1), "user_stop")
        self.assertEqual(evening_smoke.TOTAL_SECONDS - evening_smoke.ACTIVE_SECONDS, 600)

    def test_supervisor_cutoff_stops_owned_server_and_finalizes(self):
        config = read(ROOT / "configs/qwen-library.json")
        child = Mock()
        child.poll.return_value = None
        child.returncode = -15
        child.pid = 12345
        real_read = evening_smoke.read
        def fake_read(path):
            if Path(path).name == "verified.json":
                return {"model": {"digest": "fixture-digest"}}
            if Path(path) == ROOT / "output/ollama-service/service.json":
                return {"pid": 12346}
            return real_read(path)
        def fake_api(path, payload=None, timeout=10):
            if path == "/api/version":
                return {"version": config["ollama_version"]}
            if path == "/api/ps":
                return {"models": []}
            if path == "/api/tags":
                return {"models": [{"name": config["answer"]["model"], "digest": "fixture-digest"}]}
            raise AssertionError("No unload/generate request is needed on forced server stop")
        with tempfile.TemporaryDirectory() as d, patch.object(evening_smoke, "service") as service, \
                patch.object(evening_smoke, "api", side_effect=fake_api), \
                patch.object(evening_smoke, "read", side_effect=fake_read), \
                patch.object(evening_smoke, "ACTIVE_SECONDS", 0), \
                patch.object(evening_smoke.subprocess, "Popen", return_value=child), \
                patch.object(evening_smoke.subprocess, "run", return_value=Mock(stdout="fixture GPU idle")), \
                patch.object(evening_smoke, "export_review") as export, patch("builtins.print"):
            out = Path(d) / "session"
            evening_smoke.start(out)
            state = real_read(out / "session.json")
            self.assertEqual(state["stop_reason"], "50_minute_cutoff")
            self.assertTrue(state["cleanup"]["server_stopped"])
            self.assertIn(unittest.mock.call("Stop", 12346), service.call_args_list)
            export.assert_called_once_with(out)
            self.assertTrue((out / "STOP").exists())

    def test_stop_does_not_touch_service_without_session_record(self):
        with tempfile.TemporaryDirectory() as d, patch.object(evening_smoke, "service") as service:
            with self.assertRaises(ValueError):
                evening_smoke.stop(Path(d))
            service.assert_not_called()

    def test_stop_closed_session_does_not_stop_a_new_server(self):
        with tempfile.TemporaryDirectory() as d, patch.object(evening_smoke, "service") as service, patch("builtins.print"):
            session = Path(d)
            write(session / "session.json", {"status": "closed", "service_pid": 12346})
            evening_smoke.stop(session)
            service.assert_not_called()


if __name__ == "__main__":
    unittest.main()
