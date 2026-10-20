import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_structmem_synthesis as runner


class PaidSynthesisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.preparation = self.root / "preparation"
        self.preparation.mkdir()
        self.request = {"model": "deepseek-flash", "messages": [
            {"role": "system", "content": "Summarize"}, {"role": "user", "content": "Evidence"}],
            "thinking": {"type": "disabled"}, "stream": False,
            "temperature": 0, "top_p": 1, "max_tokens": 8192}
        rows = [{"sample_id": "conv-48", "window_index": i, "stage": "offline_synthesis_preparation",
                 "proposed_request": self.request, "real_request_sent": False, "usage": None} for i in range(2)]
        source = self.preparation / "proposed-calls.jsonl"
        source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        runner.write_json(self.preparation / "preparation.json", {
            "status": "offline_native_synthesis_prepared", "synthetic": True, "sample_id": "conv-48",
            "proposed_calls": 2, "proposal_sha256": runner.file_hash(source)})

    def event(self, status="ok"):
        return {"status": status, "simulated": False, "request": copy.deepcopy(self.request),
                "prediction": "Real summary" if status == "ok" else None, "finish_reason": "stop",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15} if status == "ok" else None}

    def test_stops_and_records_first_failure_without_retry(self):
        with patch.object(runner, "Client") as factory:
            factory.return_value.call.return_value = self.event("failed")
            self.assertEqual(runner.run([self.preparation], self.root / "failed"), 1)
            self.assertEqual(factory.return_value.call.call_count, 1)
        manifest = runner.read_json(self.root / "failed/run.json")
        self.assertEqual(manifest["new_requests"], 1)
        self.assertEqual(manifest["successful_windows"], 0)

    def test_successful_record_is_reused_without_paying_again(self):
        cached = self.root / "previous.jsonl"
        cached.write_text(json.dumps({**self.event(), "sample_id": "conv-48", "window_index": 0}) + "\n", encoding="utf-8")
        with patch.object(runner, "Client") as factory:
            factory.return_value.call.return_value = self.event()
            self.assertEqual(runner.run([self.preparation], self.root / "completed", cached), 0)
            self.assertEqual(factory.return_value.call.call_count, 1)
        manifest = runner.read_json(self.root / "completed/run.json")
        self.assertEqual(manifest["reused_successful_calls"], 1)
        self.assertEqual(manifest["usage"]["total_tokens"], 30)

    def test_changed_proposal_is_rejected_before_client_initialization(self):
        with (self.preparation / "proposed-calls.jsonl").open("a", encoding="utf-8") as stream:
            stream.write("{}\n")
        with patch.object(runner, "Client") as factory, self.assertRaisesRegex(ValueError, "receipt"):
            runner.run([self.preparation], self.root / "rejected")
        factory.assert_not_called()

    def test_recorded_success_with_changed_request_is_rejected(self):
        changed = {**self.event(), "sample_id": "conv-48", "window_index": 0}
        changed["request"]["max_tokens"] = 1
        cached = self.root / "changed.jsonl"
        cached.write_text(json.dumps(changed) + "\n", encoding="utf-8")
        with patch.object(runner, "Client") as factory, self.assertRaisesRegex(ValueError, "differ"):
            runner.run([self.preparation], self.root / "rejected", cached)
        factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
