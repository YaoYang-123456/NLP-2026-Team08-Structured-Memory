import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from summarize_stability import validate_review, validate_outputs, score, pair_category, digest, conservative_label


class StabilitySummaryTests(unittest.TestCase):
    def test_complete_coordinates_and_response_binding(self):
        inputs = [{'question_id': 'q', 'question': 'Q', 'facts': []}]
        conditions = {c: {'rules_sha256': digest([])} for c in ['B0', 'B2']}
        rows = [{'question_id': 'q', 'round': i, 'condition': c, 'sample_id': str(i)+c,
                 'facts_sha256': digest([]), 'rules_sha256': digest([]), 'status': 'generated', 'response': 'original'}
                for i in range(3) for c in conditions]
        queue = [{'sample_id': r['sample_id'], 'question': 'Q', 'response': 'original',
                  'applicable_strict_abstention': False} for r in rows]
        validate_outputs(rows, queue, inputs, conditions)
        for mutation in ['response', 'duplicate', 'missing', 'rules', 'id']:
            bad = copy.deepcopy(rows)
            if mutation == 'response': bad[0]['response'] = 'changed'
            if mutation == 'duplicate': bad[0] = copy.deepcopy(bad[1])
            if mutation == 'missing': bad.pop()
            if mutation == 'rules': bad[0]['rules_sha256'] = 'wrong'
            if mutation == 'id': bad[0]['sample_id'] = bad[1]['sample_id']
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_outputs(bad, queue, inputs, conditions)

    def test_audit_disagreement_stays_uncertain(self):
        self.assertEqual(conservative_label("Yes", "uncertain"), "uncertain")
        self.assertEqual(conservative_label("Yes", "No"), "uncertain")
        self.assertEqual(conservative_label("No", "No"), "No")

    def test_failures_and_uncertain_are_not_wrong(self):
        self.assertEqual(score([{"label": "Yes"}, {"label": "uncertain"}, {"status": "generation_failed"}]),
                         {"planned": 3, "Yes": 1, "No": 0, "uncertain": 1, "missing_or_failed": 1, "valid": 1})
        self.assertEqual(pair_category(None, "Yes"), "incomparable")
        self.assertEqual(pair_category("uncertain", "No"), "incomparable")
        self.assertEqual(pair_category("Yes", "No"), "only_B0")
        self.assertEqual(pair_category("No", "Yes"), "only_B2")

    def test_review_bound_to_input_and_policy(self):
        policy = {"version": "v2"}
        item = {"sample_id": "x", "question": "Q", "response": "R"}
        item["input_sha256"] = digest(item)
        queue = [item]
        doc = {"version": "v2", "queue_sha256": digest(queue), "policy_sha256": digest(policy),
               "reviewer": {"type": "external_ai_app", "identity": "AI", "exact_model_version": "unknown", "human_gold": False},
               "results": [{"sample_id": "x", "input_sha256": item["input_sha256"], "label": "uncertain", "reason": "ambiguous",
                            "unsupported_expansion": "unknown", "quality_reason": "not enough evidence"}]}
        self.assertEqual(validate_review(queue, doc, policy)["x"]["label"], "uncertain")
        for mutation in ("missing", "duplicate", "input", "policy", "human"):
            bad = copy.deepcopy(doc)
            if mutation == "missing": bad["results"] = []
            if mutation == "duplicate": bad["results"] *= 2
            if mutation == "input": bad["results"][0]["input_sha256"] = "changed"
            if mutation == "policy": bad["policy_sha256"] = "changed"
            if mutation == "human": bad["reviewer"]["human_gold"] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_review(queue, bad, policy)


if __name__ == "__main__":
    unittest.main()
