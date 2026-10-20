"""Offline checks for input isolation and extraction provenance boundaries."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from structmem_build import prepare_session, validate_extraction, validate_prepared


class StructMemInputTests(unittest.TestCase):
    def sample(self):
        return [{"sample_id": "test", "qa": [{"answer": "ANSWER_CANARY"}], "conversation": {
            "speaker_a": "Alice", "speaker_b": "Bob",
            "session_1_date_time": "1:00 pm on 19 October, 2026",
            "session_1": [{"speaker": "Alice", "text": "I visited Tianjin.", "dia_id": "D1:1"},
                          {"speaker": "Bob", "text": "I met you there.", "dia_id": "D1:2"}]}}]

    def test_qa_exclusion_and_original_ids(self):
        value = prepare_session(self.sample(), "test", 1)
        validate_prepared(value)
        self.assertNotIn("ANSWER_CANARY", json.dumps(value))
        self.assertEqual(value["messages"][1]["message_id"], "D1:2")
        self.assertEqual(value["timestamp"], "2026-10-19T13:00:00")

    def test_duplicate_ids_rejected(self):
        value = self.sample()
        value[0]["conversation"]["session_1"][1]["dia_id"] = "D1:1"
        with self.assertRaises(ValueError):
            prepare_session(value, "test", 1)

    def test_unexpected_answer_field_rejected(self):
        value = prepare_session(self.sample(), "test", 1)
        value["answer"] = "secret"
        with self.assertRaises(ValueError):
            validate_prepared(value)

    def test_out_of_range_or_coerced_source_rejected(self):
        for source in (-1, 2, True, "0", None):
            with self.subTest(source=source), self.assertRaises(ValueError):
                validate_extraction(json.dumps({"data": [{"fact": "a", "source_id": source}]}), 2)

    def test_bad_or_truncated_json_rejected(self):
        for content in ('{"data": [', '{"facts": []}', '{"data": [null]}', '{"data": [{"source_id": 0}]}'):
            with self.subTest(content=content), self.assertRaises((ValueError, TypeError)):
                validate_extraction(content, 2)

    def test_official_relational_schema_accepted(self):
        content = '{"data": [{"source_id": 1, "relation": "Bob thanked Alice."}]}'
        self.assertEqual(validate_extraction(content, 2)[0]["relation"], "Bob thanked Alice.")


if __name__ == "__main__":
    unittest.main()
