import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
from metamem_pilot.pipeline import JUDGE_PARSER_VERSION, evaluate, parse_judge_label
from reparse_judges import derive


class JudgeParserTests(unittest.TestCase):
    def test_evaluate_keeps_raw_and_accepts_false_label(self):
        class Client:
            config = {"backend": "mock"}

            def call(self, stage, *args):
                return " No.\n" if stage == "judge" else "answer"

        rows = [{"question_id": "fixture", "task": "knowledge-update", "question": "Question?",
                 "question_date": "2026-10-15", "facts": []}]
        result = evaluate(rows, [], Client(), lambda: {"fixture": "reference"})[0]
        self.assertEqual(result["status"], "valid")
        self.assertIs(result["correct"], False)
        self.assertEqual(result["judge_response"], " No.\n")
        self.assertEqual(result["judge_parser_version"], JUDGE_PARSER_VERSION)

    def test_complete_variants(self):
        for raw, expected in [("Yes", True), ("NO", False), (" yEs.\n", True),
                              ("\tNo. \r\n", False), ("yes", True), ("no", False)]:
            with self.subTest(raw=raw):
                self.assertIs(parse_judge_label(raw), expected)

    def test_reject_ambiguous_or_extra_text(self):
        for raw in ["", " \n", "yes no", "Yes. No.", "No, actually yes", "Yes because it is correct",
                    "No.\nExplanation", "yesterday", "nobody", "Yes..", "No!", "Yes。", "No .",
                    '"Yes"', "**No**", "Label: Yes", "yes\nno"]:
            with self.subTest(raw=raw):
                self.assertIsNone(parse_judge_label(raw))

    def test_offline_preserves_raw_and_does_not_recover_call_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "smoke").mkdir()
            rows = [{"question_id": "same", "attempt": i, "status": status,
                     "correct": None, "judge_response": "No."}
                    for i, status in enumerate(["judge_parse_failed", "judge_failed"])]
            p = root / "smoke/rollouts-00.json"
            p.write_text(json.dumps(rows), encoding="utf-8")
            original = p.read_bytes()
            result = derive(root)
            self.assertEqual(p.read_bytes(), original)
            self.assertEqual(result["valid"], 1)
            self.assertEqual(result["no"], 1)
            self.assertEqual(result["records"][0]["judge_raw"], "No.")
            self.assertEqual(result["records"][1]["derived_status"], "judge_failed")
            self.assertIsNone(result["records"][1]["derived_correct"])


if __name__ == "__main__":
    unittest.main()
