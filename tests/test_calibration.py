import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
from metamem_pilot.client import Client, RunStopped
from metamem_pilot.data import read
from metamem_pilot.judge import ORIGINAL, CLARIFIED, CLARIFICATION, judge_prompt
from third_party.metamem_judge import get_anscheck_prompt
from calibrate_judge import save_comparison, restore_judgments
import json


class CalibrationTests(unittest.TestCase):
    def test_local_save_retry_is_bounded(self):
        with patch("calibrate_judge.write_atomic", side_effect=[PermissionError(), None]) as write, patch("calibrate_judge.time.sleep"):
            save_comparison(Path("unused"), [])
            self.assertEqual(write.call_count, 2)
        with patch("calibrate_judge.write_atomic", side_effect=PermissionError()) as write, patch("calibrate_judge.time.sleep"):
            with self.assertRaises(PermissionError):
                save_comparison(Path("unused"), [])
            self.assertEqual(write.call_count, 5)

    def test_recover_complete_call_not_stale_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            item = {"source": "s", "question_id": "q", "attempt": 0, "task": "knowledge-update",
                    "question": "Q", "reference": "A", "response": "R", "judgments": {}}
            event = {"stage": "judge", "question_id": "s:q:" + ORIGINAL, "attempt": 0,
                     "prompt": judge_prompt("knowledge-update", "Q", "A", "R"), "response": "No.", "status": "ok"}
            (Path(d) / "calls.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
            self.assertEqual(restore_judgments([item], Path(d)), 1)
            self.assertIs(item["judgments"][ORIGINAL]["correct"], False)
            with self.assertRaises(ValueError):
                restore_judgments([item], Path(d))

    def test_versions_and_unchanged_abstention(self):
        args = ("knowledge-update", "Q", "A", "R")
        self.assertEqual(judge_prompt(*args), get_anscheck_prompt(*args))
        self.assertEqual(judge_prompt(*args, version=CLARIFIED), CLARIFICATION + get_anscheck_prompt(*args))
        self.assertEqual(judge_prompt(*args, True, CLARIFIED), judge_prompt(*args, True, ORIGINAL))
        with self.assertRaises(ValueError):
            judge_prompt(*args, version="unknown")

    def test_request_cap_prevents_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            config = read(ROOT / "configs/qwen-budget-diagnostic.json")
            config["backend"] = "mock"
            log = Path(d) / "calls.jsonl"
            client = Client(config, log, max_requests=1)
            client.call("judge", "Q", "q")
            before = log.read_bytes()
            with self.assertRaises(RunStopped):
                client.call("judge", "Q", "q")
            self.assertEqual(log.read_bytes(), before)
            self.assertFalse((Path(d) / "pending-call.json").exists())


if __name__ == "__main__":
    unittest.main()
