import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_strict_abstention import counts, mixed, paired, validate, digest, VERSION


class SensitivityTests(unittest.TestCase):
    def test_uncertain_is_not_wrong_or_mixed(self):
        rows = [{"label": x} for x in ("Yes", "No", "uncertain")]
        self.assertEqual(counts(rows, "label"), {"Yes": 1, "No": 1, "uncertain": 1, "valid": 2, "total": 3})
        self.assertFalse(mixed(["Yes", "uncertain"]))
        self.assertFalse(mixed(["No", "No"]))
        self.assertTrue(mixed(["Yes", "No"]))

    def test_pair_partition(self):
        rows = []
        for i, (a, b) in enumerate([("Yes", "Yes"), ("No", "Yes"), ("Yes", "No"), ("No", "No"), ("No", "uncertain")]):
            rows.extend([{"question_id": str(i), "condition": c, "label": label}
                         for c, label in (("B0", a), ("B2-rules-01.json", b))])
        result = paired(rows, "label")
        self.assertEqual(result, {"both_correct": ["0"], "only_B2": ["1"], "only_B0": ["2"], "both_wrong": ["3"], "incomparable": ["4"]})

    def test_review_scope_and_integrity(self):
        item = {"sample_id": "a", "applicable": True, "response": "complete"}
        item["input_sha256"] = digest(item)
        queue = [item, {"sample_id": "b", "applicable": False}]
        doc = {"version": VERSION, "queue_sha256": digest(queue), "policy_sha256": "frozen",
               "reviewer": {"type": "external_ai_app", "human_gold": False},
               "results": [{"sample_id": "a", "input_sha256": item["input_sha256"],
                            "label": "No", "reason": "assumption presented as fact", "clauses": ["S2"]}]}
        self.assertEqual(set(validate(queue, doc, "frozen")), {"a"})
        variants = []
        for key, value in (("sample_id", "b"), ("input_sha256", "changed"), ("clauses", ["S5"])):
            bad = copy.deepcopy(doc); bad["results"][0][key] = value; variants.append(bad)
        bad = copy.deepcopy(doc); bad["results"] = []; variants.append(bad)
        bad = copy.deepcopy(doc); bad["results"] *= 2; variants.append(bad)
        bad = copy.deepcopy(doc); bad["policy_sha256"] = "changed"; variants.append(bad)
        for bad in variants:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate(queue, bad, "frozen")


if __name__ == "__main__":
    unittest.main()
