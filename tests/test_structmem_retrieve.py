import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import structmem_retrieve as sm
import retrieve_structmem as command


def vector(x=1.0, y=0.0):
    return [x, y] + [0.0] * 382


def point(pid, x=1.0, y=0.0, summary=False):
    payload = ({"summary": "Alex joined the club.", "covered_entry_ids": ["e1"],
                "seed_entry_ids": [], "time_range": {"start": "2023-01-01T10:00:00",
                                                       "end": "2023-01-01T11:00:00"}}
               if summary else {"memory": "Alex joined the club yesterday.", "speaker_name": "Alex",
                                "time_stamp": "2023-01-01T10:00:00", "weekday": "Sunday",
                                "entry_type": "factual", "float_time_stamp": 1672567200})
    return {"id": pid, "vector": vector(x, y), "payload": payload}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def make_index(root, synthetic=False):
    save(root / "events.json", [point("e1"), point("e2", 0.0, 1.0)])
    save(root / "summaries.json", [point("s1", summary=True)])
    index = {"upstream_revision": sm.UPSTREAM_REVISION, "embedding": sm.EMBEDDING,
             "source_conversations_sha256": "a" * 64,
             "synthetic": synthetic, "conversations": {"conv-48": {kind: {"path": filename,
                 "sha256": sm.file_hash(root / filename)} for kind, filename in
                 (("event", "events.json"), ("synthesis", "summaries.json"))}}}
    save(root / "index.json", index)
    return index


class StructMemTests(unittest.TestCase):
    def test_question_union_key_and_label_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "questions.json"
            rows = [{"sample_id": "conv-48", "qa_index": i, "question": "When?", "category": 1}
                    for i in (86, 104)]
            save(path, rows)
            self.assertEqual(sm.load_questions(path), rows)
            for bad in (rows + [rows[0]], [{**rows[0], "answer": "SECRET"}],
                        [{**rows[0], "qa_index": True}], [{**rows[0], "category": 5}]):
                save(path, bad)
                with self.assertRaises(ValueError):
                    sm.load_questions(path)

    def test_cosine_stable_order_and_independent_limits(self):
        entries = [point("first"), point("other", 0.0, 1.0), point("tie")]
        self.assertEqual([p["id"] for p in sm.rank_points(entries, vector(), 2)], ["first", "tie"])
        self.assertAlmostEqual(sm.rank_points([point("scaled", 5.0, 0.0)], vector(2.0), 1)[0]["score"], 1)
        for bad in ([0.0] * 384, vector(float("nan")), vector(float("inf")), [1.0] * 383):
            with self.assertRaises(ValueError):
                sm.rank_points(entries, bad, 60)

    def test_native_exports_preserve_binding_and_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_index(root)
            memories, hashes = sm.load_memory_index(root / "index.json", ["conv-48"])
            q = {"sample_id": "conv-48", "qa_index": 86, "question": "When?", "category": 1}
            rows, traces = sm.prepare_inputs([q], memories, lambda _: vector())
            self.assertEqual(set(rows[0]), sm.QUESTION_FIELDS | {"contexts"})
            self.assertEqual(rows[0]["contexts"][0]["source_ids"], ["conv-48/event/e1"])
            self.assertEqual(rows[0]["contexts"][-1]["source_ids"],
                             ["conv-48/synthesis/s1", "conv-48/event/e1"])
            self.assertIn("2023-01-01T10:00:00", rows[0]["contexts"][0]["text"])
            self.assertIn("Alex", rows[0]["contexts"][0]["text"])
            self.assertEqual(traces[0]["retrieved"]["event"][0]["payload"]["entry_type"], "factual")
            self.assertEqual(hashes["conv-48"]["event"], sm.file_hash(root / "events.json"))
            with self.assertRaises(KeyError):
                sm.load_memory_index(root / "index.json", ["conv-42"])

    def test_snapshot_hash_and_version_mismatches_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            index = make_index(root)
            for key, bad in (("upstream_revision", "wrong"), ("embedding", {**sm.EMBEDDING, "revision": "wrong"})):
                save(root / "index.json", {**index, key: bad})
                with self.assertRaises(ValueError):
                    sm.load_memory_index(root / "index.json", ["conv-48"])
            save(root / "index.json", index)
            with (root / "events.json").open("a", encoding="utf-8") as stream:
                stream.write(" ")
            with self.assertRaises(ValueError):
                sm.load_memory_index(root / "index.json", ["conv-48"])

    def test_empty_missing_vector_and_annotation_exports_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "points.json"
            for bad in ([], [{"id": "e", "payload": point("e")["payload"]}],
                        [{**point("e"), "payload": {**point("e")["payload"], "nested": {"answer": "SECRET"}}}],
                        [point("e"), point("e")], [point("e", math.nan)]):
                save(path, bad)
                with self.assertRaises(ValueError):
                    sm.load_points(path, "event")

    def test_dangling_summary_links_and_synthetic_exports_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            index = make_index(root, synthetic=True)
            with self.assertRaises(ValueError):
                sm.load_memory_index(root / "index.json", ["conv-48"])
            self.assertIn("conv-48", sm.load_memory_index(root / "index.json", ["conv-48"], True)[0])
            summary = point("s1", summary=True)
            summary["payload"]["seed_entry_ids"] = ["other-conversation-event"]
            save(root / "summaries.json", [summary])
            index["conversations"]["conv-48"]["synthesis"]["sha256"] = sm.file_hash(root / "summaries.json")
            save(root / "index.json", index)
            with self.assertRaises(ValueError):
                sm.load_memory_index(root / "index.json", ["conv-48"], True)

    def test_60_events_plus_5_summaries_and_original_order(self):
        memories = {"conv-48": {"event": [point(f"e{i}") for i in range(75)],
                                 "synthesis": [point(f"s{i}", summary=True) for i in range(9)]}}
        questions = [{"sample_id": "conv-48", "qa_index": i, "question": "When?", "category": 1}
                     for i in (104, 86)]
        rows, _ = sm.prepare_inputs(questions, memories, lambda _: vector())
        self.assertEqual([r["qa_index"] for r in rows], [104, 86])
        self.assertEqual([c["kind"] for c in rows[0]["contexts"]], ["event"] * 60 + ["synthesis"] * 5)

    def test_real_cli_checks_frozen_text_before_embedding_or_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            q = [{"sample_id": "conv-48", "qa_index": 86, "category": 1, "question": "When?"}]
            save(root / "inputs.json", q)
            make_index(root)
            config = {"lightmem": {"revision": sm.UPSTREAM_REVISION}, "embedding": sm.EMBEDDING,
                      "questions": [{k: row[k] for k in ("sample_id", "qa_index", "category")} for row in q],
                      "smoke_question_keys": [["conv-48", 86]], "splits": {"development": ["conv-48"]},
                      "output_sha256": {"smoke.inputs.json": sm.file_hash(root / "inputs.json"),
                                        "development.conversations.json": "a" * 64}}
            save(root / "config.json", config)
            with patch.object(command, "local_embedder", return_value=lambda _: vector()) as embed:
                result = command.run(root / "inputs.json", root / "config.json", root / "index.json", root, root / "out")
                self.assertEqual(result["status"], "retrieval_only")
                self.assertEqual(result["answer_api_calls"], 0)
                with self.assertRaises(FileExistsError):
                    command.run(root / "inputs.json", root / "config.json", root / "index.json", root, root / "out")
                q[0]["question"] = "Changed after freeze"
                save(root / "inputs.json", q)
                embed.reset_mock()
                with self.assertRaises(ValueError):
                    command.run(root / "inputs.json", root / "config.json", root / "index.json", root, root / "new")
                embed.assert_not_called()
                self.assertFalse((root / "new").exists())

    def test_summarize_uses_actual_upstream_signature(self):
        memory = Mock()
        sm.summarize_memory(memory)
        memory.summarize.assert_called_once_with(retrieval_scope="global", time_window=3600,
                                                top_k_seeds=15, process_all=True, enable_cross_event=True)

    def test_merged_f_consumes_d_output_without_network(self):
        from run_qa import load_inputs, run
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_index(root, synthetic=True)
            memories, _ = sm.load_memory_index(root / "index.json", ["conv-48"], allow_synthetic=True)
            question = {"sample_id": "conv-48", "qa_index": 86, "question": "SYNTHETIC: When?", "category": 1}
            rows, _ = sm.prepare_inputs([question], memories, lambda _: vector())
            inputs = root / "retrieval.jsonl"
            inputs.write_text(json.dumps(rows[0]) + "\n", encoding="utf-8", newline="\n")
            self.assertEqual(load_inputs(inputs), rows)
            with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("Unexpected network")), \
                    patch("builtins.print"):
                status = run(inputs, ROOT / "configs/qa.example.json", "S2", root / "qa", mock=True)
            result = sm.read_json(root / "qa/run.json")
            prediction = json.loads((root / "qa/predictions.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(status, 0)
            self.assertEqual(result["simulated_questions"], 1)
            self.assertEqual(result["successful_questions"], 0)
            self.assertEqual(prediction["contexts"], rows[0]["contexts"])
            self.assertEqual(prediction["status"], "simulated")
            self.assertIsNone(prediction["usage"])


if __name__ == "__main__":
    unittest.main()
