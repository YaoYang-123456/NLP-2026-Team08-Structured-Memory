"""Contract checks use synthetic data; optional real-data checks use the pinned release."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prepare_locomo", ROOT / "scripts/prepare_locomo.py")
data = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(data)


def fixture():
    return [{"sample_id": f"conv-{c}", "conversation": {
        "speaker_a": "A", "speaker_b": "B", "session_1_date_time": "1:00 pm on 1 May, 2023",
        "session_1": [{"dia_id": "D1:1", "speaker": "A", "text": f"message {c}",
                       "blip_caption": "a picture", "answer": "forbidden"}],
        "summary": "forbidden"},
        "qa": [{"question": f"question {c}/{i}", "category": i % 4 + 1,
                "answer": f"secret-{c}-{i}", "evidence": ["D1:1"]} for i in range(60)],
        "session_summary": "forbidden"} for c in range(10)]


class PreparationTests(unittest.TestCase):
    def test_split_and_smoke_contract(self):
        rows = fixture()
        config = data.freeze(rows)
        self.assertEqual(config, data.freeze(copy.deepcopy(rows)))
        self.assertEqual(config, data.freeze(list(reversed(rows))))
        self.assertFalse(set(config["splits"]["development"]) & set(config["splits"]["heldout"]))
        self.assertEqual(len(config["splits"]["development"]), 3)
        self.assertEqual(len(config["splits"]["heldout"]), 7)
        self.assertEqual(len({tuple(k) for k in config["smoke_question_keys"]}), 5)
        self.assertTrue({tuple(k) for k in config["smoke_question_keys"]} <=
                        {(q["sample_id"], q["qa_index"]) for q in config["questions"]})
        self.assertEqual({q["category"] for q in config["questions"][:5]}, {1, 2, 3, 4})

    def test_labels_and_annotations_do_not_reach_inputs(self):
        rows = fixture()
        config = data.freeze(rows)
        payloads = data.build_payloads(rows, config["splits"], config["questions"])
        for name in ("development.inputs.json", "smoke.inputs.json"):
            self.assertNotIn("secret-", json.dumps(payloads[name]))
            self.assertTrue(all(set(q) == {"sample_id", "qa_index", "category", "question"}
                                for q in payloads[name]))
        convs = payloads["development.conversations.json"]
        self.assertNotIn("forbidden", json.dumps(convs))
        self.assertEqual(convs[0]["conversation"]["session_1"][0]["dia_id"], "D1:1")
        self.assertIn("blip_caption", convs[0]["conversation"]["session_1"][0])

    def test_rejects_split_leakage_and_bad_ids(self):
        rows = fixture()
        config = data.freeze(rows)
        splits = copy.deepcopy(config["splits"])
        splits["heldout"][0] = splits["development"][0]
        with self.assertRaises(ValueError):
            data.build_payloads(rows, splits, config["questions"])
        selected = copy.deepcopy(config["questions"])
        selected[0]["qa_index"] = -1
        with self.assertRaises(ValueError):
            data.build_payloads(rows, config["splits"], selected)

    def test_rejects_duplicate_turns(self):
        rows = fixture()
        rows[0]["conversation"]["session_1"].append(copy.deepcopy(rows[0]["conversation"]["session_1"][0]))
        with self.assertRaises(ValueError):
            data.audit_source(rows)

    def test_source_hash_is_checked_before_parsing(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "source.json"
            source.write_bytes(b"[]")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                data.load_source(source)

    def test_frozen_outputs_cannot_be_replaced(self):
        rows = fixture()
        config = data.freeze(rows)
        with tempfile.TemporaryDirectory() as d, patch.object(data, "load_source", return_value=rows):
            dest = Path(d)
            data.materialize(Path("unused"), config, dest)
            changed = dest / "development.inputs.json"
            changed.write_text("[]", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                data.materialize(Path("unused"), config, dest)
            self.assertEqual(changed.read_text(encoding="utf-8"), "[]")
            invalid = copy.deepcopy(config)
            invalid["seed"] += 1
            with self.assertRaises(ValueError):
                data.materialize(Path("unused"), invalid, dest)

    @unittest.skipUnless((ROOT / "data/raw/locomo10.json").exists(), "Pinned data is not downloaded")
    def test_real_release_regenerates_exact_frozen_files(self):
        config = json.loads((ROOT / "configs/locomo-smoke.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            report = data.materialize(ROOT / "data/raw/locomo10.json", config, Path(d))
            self.assertEqual(report["questions"], 30)
            for name, digest in config["output_sha256"].items():
                self.assertEqual(data.sha256((Path(d) / name).read_bytes()), digest)


if __name__ == "__main__":
    unittest.main()
