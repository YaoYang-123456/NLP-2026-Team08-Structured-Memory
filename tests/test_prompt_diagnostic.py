import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
from metamem_pilot.data import digest, file_hash, read, write
from metamem_pilot.pipeline import answer_prompt
from prepare_prompt_diagnostic import prepare


class PromptDiagnosticTests(unittest.TestCase):
    def fixture(self, root):
        spec = copy.deepcopy(read(ROOT / "configs/metamem-prompt-diagnostic.json"))
        rows = [{"question_id": qid, "question": "Which event?", "question_date": "2026-01-01",
                 "task": "multi-session", "facts": [{"fact_id": "s:0:0", "text": "A dated fact.", "score": 1}]}
                for qid in spec["question_ids"]]
        inputs = root / "data/pilot/validation.inputs.json"
        write(inputs, rows)
        spec["expected_validation_inputs_sha256"] = file_hash(inputs)
        write(root / "configs/metamem-prompt-diagnostic.json", spec)
        for name in ("generation_config", "rules_file", "policy_file"):
            write(root / spec[name], read(ROOT / spec[name]))
        write(root / "data/pilot/manifest.json", {
            "files": {inputs.name: file_hash(inputs)},
            "splits": {"validation": [{"question_id": row["question_id"]} for row in rows]}})
        # No labels or test files exist: preparation must not depend on them.
        return rows, spec

    def test_all_coordinates_share_facts_and_rules_without_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows, spec = self.fixture(root)
            out = root / "prepared"
            plan = prepare(root, out)
            requests = read(out / "requests.frozen.json")
            self.assertEqual(len(requests), 24)
            self.assertEqual(len({r["sample_id"] for r in requests}), 24)
            self.assertEqual(plan["real_requests"], 0)
            self.assertFalse(plan["reference_answers_read"])
            rules = read(out / "rules.frozen.json")["rules"]
            for row in rows:
                paired = [r for r in requests if r["question_id"] == row["question_id"]]
                self.assertEqual({r["facts_sha256"] for r in paired}, {digest(row["facts"])})
                self.assertEqual({r["rules_sha256"] for r in paired}, {digest(rules)})
                for request in paired:
                    text = request["payload"]["messages"][0]["content"]
                    original = answer_prompt(row, rules)
                    if request["condition"] == "original":
                        self.assertEqual(text, original)
                    else:
                        self.assertTrue(text.startswith(original))
                        self.assertIn(spec["instructions"], text)
                    self.assertEqual(request["payload_sha256"], digest(request["payload"]))
                    self.assertEqual(request["status"], "not_started")
                    self.assertIsNone(request["response"])
            for name, sha in plan["artifacts_sha256"].items():
                self.assertEqual(file_hash(out / name), sha)
            with self.assertRaises(FileExistsError):
                prepare(root, out)

    def test_tampered_inputs_and_wrong_split_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows, spec = self.fixture(root)
            write(root / "data/pilot/validation.inputs.json", rows[:-1])
            with self.assertRaisesRegex(ValueError, "stage-two baseline"):
                prepare(root, root / "out")
            write(root / "data/pilot/validation.inputs.json", rows)
            spec["question_ids"][0] = "not-a-development-id"
            write(root / "configs/metamem-prompt-diagnostic.json", spec)
            with self.assertRaisesRegex(ValueError, "four distinct"):
                prepare(root, root / "out")


if __name__ == "__main__":
    unittest.main()
