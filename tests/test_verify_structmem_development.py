from pathlib import Path
from types import SimpleNamespace
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_structmem_development import compare_hits


class CompleteSnapshotComparisonTests(unittest.TestCase):
    def setUp(self):
        self.vector = [1.0, 0.0] + [0.0] * 382
        self.points = {pid: {"id": pid, "vector": vector, "payload": {}}
                       for pid, vector in (("a", self.vector), ("b", self.vector),
                                           ("c", [0.0, 1.0] + [0.0] * 382))}

    def test_equal_score_duplicate_ids_can_have_different_order_or_cutoff(self):
        result = compare_hits([{"id": "a", "score": 1.0}],
                              [SimpleNamespace(id="b", score=1.0)], self.points, self.vector)
        self.assertFalse(result["same_order"])
        self.assertFalse(result["same_id_set"])
        self.assertTrue(result["valid_cosine_order_including_ties"])

    def test_non_tie_reordering_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "order differs"):
            compare_hits([{"id": "a", "score": 1.0}],
                         [SimpleNamespace(id="c", score=0.0)], self.points, self.vector)

    def test_wrong_score_and_missing_results_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "scores differ"):
            compare_hits([{"id": "a", "score": 1.0}],
                         [SimpleNamespace(id="a", score=0.4)], self.points, self.vector)
        with self.assertRaisesRegex(ValueError, "lengths differ"):
            compare_hits([{"id": "a", "score": 1.0}], [], self.points, self.vector)

    def test_candidate_preserves_shared_settings_and_ablation_prompt(self):
        from llm_client import validate_config
        candidate = json.loads((ROOT / "configs/qa-structmem-candidate.json").read_text(encoding="utf-8"))
        baseline = json.loads((ROOT / "configs/qa.example.json").read_text(encoding="utf-8"))
        validate_config(candidate)
        self.assertEqual({k: v for k, v in candidate.items() if k != "method_prompts"},
                         {k: v for k, v in baseline.items() if k != "method_prompts"})
        self.assertEqual(candidate["method_prompts"]["S0"], baseline["method_prompts"]["S0"])
        self.assertEqual(candidate["method_prompts"]["S1"], candidate["method_prompts"]["S2"])


if __name__ == "__main__":
    unittest.main()
