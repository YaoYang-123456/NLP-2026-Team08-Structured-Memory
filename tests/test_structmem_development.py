"""Synthetic contract tests; no LoCoMo QA, model requests, or experiment scores."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import structmem_development as development
from structmem_build import sha256, write_json, UPSTREAM_REV


class DevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "development.conversations.json"
        self.selection = self.root / "selection.json"
        self.profile = self.root / "profile.json"
        self.output = self.root / "run"
        self.rows = [{"sample_id": cid, "conversation": {
            "speaker_a": "Alice", "speaker_b": "Bob",
            "session_1_date_time": "1:00 pm on 19 October, 2026",
            "session_1": [{"dia_id": "D1:1", "speaker": "Alice", "text": "Hello.", "blip_caption": "a blue cup"}],
            "session_2_date_time": "1:00 pm on 20 October, 2026",
            "session_2": [{"dia_id": "D2:1", "speaker": "Bob", "text": "Thanks."}]}}
            for cid in development.DEVELOPMENT]
        write_json(self.profile, {"profile": "test-only", "model": "deepseek-flash", "embedding_dims": 384,
                                 "normalize_embeddings": True, "max_input_tokens": 12000})
        self.save_source()

    def save_source(self):
        write_json(self.data, self.rows)
        write_json(self.selection, {"splits": {"development": development.DEVELOPMENT},
                                   "lightmem": {"revision": UPSTREAM_REV},
                                   "output_sha256": {self.data.name: sha256(self.data)}})

    def make_plan(self):
        return development.make_plan(self.data, self.selection, self.profile, self.output)

    def checkpoint(self, session, status="success"):
        folder = self.output / session["sample_id"] / f"session-{session['session_number']:03d}/attempt-001"
        folder.mkdir(parents=True)
        write_json(folder / "memories.json", [{"id": "0f27307b-3602-4c20-8db7-198311cd4101", "vector": [1.0] + [0.0]*383,
                   "payload": {"memory": "Test fixture only", "source_sample_id": session["sample_id"],
                               "source_session_id": f"session_{session['session_number']}",
                               "source_message_id": f"D{session['session_number']}:1"}}])
        write_json(folder / "summary.json", {"status": status, "input_sha256": session["sha256"],
                   "synthetic": False, "execution": "live", "sample_id": session["sample_id"],
                   "session_id": f"session_{session['session_number']}", "upstream_revision": UPSTREAM_REV,
                   "config": development.read_json(self.profile), "disk_readback_verified": True,
                   "memories_sha256": sha256(folder / "memories.json")})
        return folder

    def test_full_conversations_and_image_description(self):
        plan = self.make_plan()
        self.assertEqual((plan["session_count"], plan["message_count"]), (6, 6))
        for cid in development.DEVELOPMENT:
            first = development.read_json(self.output / cid / "inputs/session-001.json")
            self.assertIn("(image description: a blue cup)", first["messages"][0]["content"])
        development.validate_plan(self.output / "plan.json")

    def test_unknown_fields_rejected_even_with_matching_hash(self):
        for change in ("qa", "event_summary"):
            with self.subTest(change=change):
                self.rows[0][change] = "FORBIDDEN_CANARY"
                self.save_source()
                with self.assertRaises(ValueError):
                    self.make_plan()
                del self.rows[0][change]

    def test_duplicate_within_conversation_rejected(self):
        self.rows[0]["conversation"]["session_2"][0]["dia_id"] = "D1:1"
        self.save_source()
        with self.assertRaises(ValueError):
            self.make_plan()

    def test_plan_tamper_rejected(self):
        self.make_plan()
        path = self.output / "conv-48/inputs/session-001.json"
        path.write_text("{}")
        with self.assertRaises(ValueError):
            development.validate_plan(self.output / "plan.json")

    def test_omitted_session_rejected(self):
        plan = self.make_plan()
        plan["sessions"].pop()
        plan["session_count"] -= 1
        plan["message_count"] -= 1
        write_json(self.output / "plan.json", plan)
        with self.assertRaises(ValueError):
            development.validate_plan(self.output / "plan.json")

    def test_successful_checkpoints_skipped_without_generation(self):
        plan = self.make_plan()
        for session in plan["sessions"]:
            self.checkpoint(session)
        with patch.object(development, "build") as generate:
            result = development.run_plan(SimpleNamespace(plan=self.output / "plan.json", conversation=None, limit=0))
        generate.assert_not_called()
        self.assertEqual(result["completed_sessions_skipped"], 6)

    def test_failed_checkpoint_requires_explicit_retry(self):
        plan = self.make_plan()
        self.checkpoint(plan["sessions"][0], "failed")
        with patch.object(development, "build") as generate, self.assertRaises(RuntimeError):
            development.run_plan(SimpleNamespace(plan=self.output / "plan.json", conversation=None, limit=0, retry_failed=False))
        generate.assert_not_called()

    def test_assembly_isolation_and_completeness(self):
        plan = self.make_plan()
        self.checkpoint(plan["sessions"][0])
        with self.assertRaises(ValueError):
            development.collect_conversation(self.output, plan, "conv-48")
        for session in plan["sessions"][1:]:
            self.checkpoint(session)
        results = development.assemble(SimpleNamespace(plan=self.output / "plan.json", conversation=None, output=self.root / "handoff"))
        self.assertEqual(set(results), set(development.DEVELOPMENT))
        self.assertTrue(all(v["entry_count"] == 2 and v["disk_readback_verified"] for v in results.values()))
        first = development.collect_conversation(self.output, plan, "conv-48")
        second = development.collect_conversation(self.output, plan, "conv-42")
        self.assertEqual(first[0]["payload"]["source_key"], "conv-48/D1:1")
        self.assertNotEqual(first[0]["id"], second[0]["id"])


if __name__ == "__main__":
    unittest.main()
