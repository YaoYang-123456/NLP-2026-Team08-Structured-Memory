import copy
import sys
import tempfile
import unittest
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
from metamem_pilot.data import digest, read
from metamem_pilot.external_review import make_item, validate_reviews, STANDARD, REVIEWER, ExternalClient
from metamem_pilot.pipeline import partial_groups
from metamem_pilot.client import RunStopped
from run_external_experiment import choose_candidate


class ExternalReviewTests(unittest.TestCase):
    def test_full_coverage_and_earliest_tie(self):
        candidates = [{"file": "early", "reuses_condition": "a"}, {"file": "late", "reuses_condition": "b"}]
        scores = {"a": {"valid_scores": 10, "correct": 7}, "b": {"valid_scores": 10, "correct": 7}}
        self.assertEqual(choose_candidate(candidates, scores, 10)["file"], "early")
        scores["a"]["valid_scores"] = 9
        self.assertEqual(choose_candidate(candidates, scores, 10)["file"], "late")
        scores["b"]["valid_scores"] = 9
        self.assertIsNone(choose_candidate(candidates, scores, 10))

    def fixture(self):
        q = [make_item("Q", "A", "R", "knowledge-update", False)]
        d = {"standard_version": STANDARD, "queue_sha256": digest(q), "reviewer": REVIEWER,
             "results": [{"sample_id": q[0]["sample_id"], "input_sha256": q[0]["input_sha256"],
                          "label": "uncertain", "reason": "ambiguous", "unsupported_expansion": "unknown",
                          "quality_reason": "no evidence"}]}
        return q, d

    def test_visible_inputs_hide_condition_and_history(self):
        q, d = self.fixture()
        self.assertEqual(set(q[0]), {"sample_id", "question", "reference", "response", "standard", "standard_version", "input_sha256"})
        self.assertEqual(validate_reviews(q, d)[q[0]["sample_id"]]["label"], "uncertain")

    def test_bad_review_fails_closed(self):
        q, d = self.fixture()
        variants = []
        for key, value in (("sample_id", "unknown"), ("input_sha256", "bad"), ("label", "maybe"),
                           ("reason", ""), ("unsupported_expansion", "maybe")):
            obj = copy.deepcopy(d); obj["results"][0][key] = value; variants.append(obj)
        obj = copy.deepcopy(d); obj["results"] = []; variants.append(obj)
        obj = copy.deepcopy(d); obj["results"] *= 2; variants.append(obj)
        obj = copy.deepcopy(d); obj["queue_sha256"] = "bad"; variants.append(obj)
        obj = copy.deepcopy(d); obj["reviewer"]["human_gold"] = True; variants.append(obj)
        for obj in variants:
            with self.subTest(obj=obj), self.assertRaises(ValueError):
                validate_reviews(q, obj)
        changed = copy.deepcopy(q); changed[0]["response"] = "modified"
        d["queue_sha256"] = digest(changed)
        with self.assertRaises(ValueError): validate_reviews(changed, d)

    def test_uncertain_never_makes_mixed_group(self):
        rows = [{"question_id": "q", "status": "valid", "correct": True},
                {"question_id": "q", "status": "judge_uncertain", "correct": None}]
        eligible, skipped = partial_groups(rows, 2)
        self.assertEqual(eligible, {})
        self.assertEqual(skipped["q"], "uncertain_judgment")

    def test_no_local_judge_and_stop_while_waiting(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); config = read(ROOT / "configs/qwen-budget-diagnostic.json")
            config["backend"] = "mock"
            client = ExternalClient(config, root / "calls.jsonl", time.time() - 1, root / "STOP", root / "review")
            with self.assertRaises(ValueError): client.call("judge", "Q", "q")
            with self.assertRaises(RunStopped): client.wait_file(root / "missing.json")
            self.assertFalse((root / "calls.jsonl").exists())


if __name__ == "__main__": unittest.main()
