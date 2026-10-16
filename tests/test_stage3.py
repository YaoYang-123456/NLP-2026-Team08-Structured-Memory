import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
from metamem_pilot.data import read, digest
from run_stage3 import prepare_slots, stage3_prompt, recover_logged_answers
from summarize_stage3 import statistics
from stage3_quality import validate as validate_quality


class Stage3Tests(unittest.TestCase):
    def test_statistics_keep_uncertain_and_failed_separate(self):
        rows = [
            {"round": 0, "question_id": "q", "condition": "baseline", "label": "Yes"},
            {"round": 0, "question_id": "q", "condition": "candidate", "label": "uncertain"},
            {"round": 1, "question_id": "q", "condition": "baseline", "label": "No"},
            {"round": 1, "question_id": "q", "condition": "candidate"},
        ]
        result = statistics(rows)
        candidate = result["overall"]["candidate"]
        self.assertEqual(candidate["No"], 0)
        self.assertEqual(candidate["uncertain"], 1)
        self.assertEqual(candidate["missing_or_failed"], 1)
        self.assertEqual(candidate["valid"], 0)
        self.assertEqual(len(result["paired"]["incomparable"]), 2)

    def test_quality_hash_missing_duplicate_and_dimension_validation(self):
        policy = read(ROOT / "configs/evidence-quality-v1.json")
        item = {"sample_id": "synthetic", "question": "Q", "response": "R", "facts": []}
        item["input_sha256"] = digest(item)
        queue = [item]
        row = {"sample_id": item["sample_id"], "input_sha256": item["input_sha256"],
               "reason": "Synthetic validation only", "dimensions": {
                   key: values[0] for key, values in policy["dimensions"].items()}}
        review = {"version": policy["version"], "queue_sha256": digest(queue),
                  "policy_sha256": digest(policy),
                  "reviewer": {"type": "external_ai_app", "human_gold": False,
                               "identity": "synthetic", "exact_model_version": "unknown"},
                  "results": [row]}
        self.assertEqual(validate_quality(queue, review, policy), {"synthetic": row})
        for invalid_results in ([], [row, row], [dict(row, input_sha256="wrong")],
                                [dict(row, dimensions={**row["dimensions"], "extra": "yes"})]):
            with self.assertRaises(ValueError):
                validate_quality(queue, dict(review, results=invalid_results), policy)
        changed = copy.deepcopy(queue)
        changed[0]["response"] = "Changed answer"
        with self.assertRaises(ValueError):
            validate_quality(changed, dict(review, queue_sha256=digest(changed)), policy)

    def test_literal_citation_existence_is_not_support(self):
        from stage3_quality import citation_existence
        item={'facts':[{'fact_id':'abc123:2:0','text':'Some fact'}], 'response':'Claim [abc123:2:0].'}
        self.assertEqual(citation_existence(item)[0], 'valid')
        item['response']='Claim [Fact ID: abc123].'
        self.assertEqual(citation_existence(item)[0], 'invalid')
        item['response']='Claim uses abc123:2:0 inline.'
        self.assertEqual(citation_existence(item)[0], 'valid')
        item['response']='No citation.'
        self.assertEqual(citation_existence(item)[0], 'none')

    def test_frozen_schedule_and_identical_facts(self):
        plan = read(ROOT / "configs/metamem-stage3-plan.json")
        original = {qid: {"facts": [{"fact_id": "f", "text": qid, "score": 1}]}
                    for qid in plan["question_ids"]}
        slots, _ = prepare_slots(original, plan)
        self.assertEqual(len(slots), 60)
        self.assertEqual(len({r["sample_id"] for r in slots}), 60)
        self.assertEqual({r["question_id"] for r in slots[:24]}, set(plan["initial_question_ids"]))
        self.assertTrue(all(r["phase"] == "initial_four" for r in slots[:24]))
        self.assertTrue(all(r["phase"] == "remaining_six" for r in slots[24:]))
        for repeat, order in enumerate(plan["round_orders"]):
            for qid in original:
                pair = [r for r in slots if r["round"] == repeat and r["question_id"] == qid]
                self.assertEqual([r["condition"] for r in pair], order)
                self.assertEqual([r["facts_sha256"] for r in pair], [digest(original[qid]["facts"])] * 2)
                self.assertTrue(all(not r["learned"] for r in pair))

    def test_prompt_ignores_reference_fields(self):
        row = {"question": "Synthetic question?", "question_date": "2020/01/01",
               "facts": [{"fact_id": "s:m0:c0", "text": "Known fact.", "score": 1}]}
        for condition in ("baseline", "candidate"):
            expected = stage3_prompt(row, condition)
            poisoned = dict(row, answer="SECRET_REFERENCE", reference="SECRET_REFERENCE",
                            task="SECRET_TASK", answer_session_ids=["SECRET_SESSION"])
            self.assertEqual(expected, stage3_prompt(poisoned, condition))
            self.assertIn("[s:m0:c0] Known fact.", expected)
            self.assertNotIn("SECRET", expected)

    def test_recovery_requires_exact_prompt_and_preserves_failure(self):
        row = {"question": "Q?", "question_date": "2020/01/01", "facts": []}
        by = {"original": {"q": row}}
        slot = {"sample_id": "s", "question_id": "q", "condition": "candidate", "status": "generating"}
        event = {"question_id": "s", "prompt": stage3_prompt(row, "candidate"),
                 "status": "ok", "finish_reason": "stop", "response": "Saved answer"}
        slots = [copy.deepcopy(slot)]
        self.assertEqual(recover_logged_answers(slots, [event], by, []), ["s"])
        self.assertEqual(slots[0]["response"], "Saved answer")
        with self.assertRaises(ValueError):
            recover_logged_answers([copy.deepcopy(slot)], [dict(event, prompt="different")], by, [])
        with self.assertRaises(ValueError):
            recover_logged_answers([copy.deepcopy(slot)], [event, event], by, [])
        failed = [copy.deepcopy(slot)]
        self.assertEqual(recover_logged_answers(failed, [dict(event, status="call_failed", finish_reason="length")], by, []), [])
        self.assertEqual(failed[0]["status"], "generation_failed")
        self.assertEqual(recover_logged_answers(failed, [event], by, []), [])
        self.assertEqual(failed[0]["status"], "generation_failed")
        interrupted = [copy.deepcopy(slot)]
        recover_logged_answers(interrupted, [], by, [])
        self.assertEqual(interrupted[0]["status"], "generation_interrupted")


if __name__ == "__main__":
    unittest.main()
