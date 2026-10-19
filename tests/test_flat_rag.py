import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from flat_rag import (OllamaEmbeddings, embed_chunks, load_questions, normalized,
                      prepare_retrieval, rank_chunks, raw_chunks)
from run_s0 import run


def sample():
    return {"sample_id": "conv-A", "conversation": {
        "speaker_a": "Jo", "speaker_b": "Sam",
        "session_2_date_time": "2026-10-02 08:00", "session_2": [
            {"dia_id": "D2:1", "speaker": "Jo", "text": "I moved to Prague."}],
        "session_1_date_time": "2026-10-01 08:00", "session_1": [
            {"dia_id": "D1:1", "speaker": "Sam", "text": "My cat is called Sunbeam."},
            {"dia_id": "D1:2", "speaker": "Jo", "text": "I read a book."}]}}


class FakeEncoder:
    model = "fake-test-only"

    def __init__(self):
        self.calls = []

    def encode(self, texts):
        self.calls.append(texts)
        return [[1.0, 0.0] if "cat" in text.lower() else [0.0, 1.0] for text in texts]


class FlatRagTests(unittest.TestCase):
    def test_stable_source_time_order_and_raw_text_only(self):
        data = sample()
        data["qa"] = [{"answer": "GOLD", "evidence": ["NEVER"]}]
        chunks = raw_chunks(data["sample_id"], data["conversation"])
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0]["source_ids"], ["conv-A:session_1:D1:1:0"])
        self.assertIn("2026-10-01", chunks[0]["text"])
        self.assertIn("Sam: My cat", chunks[0]["text"])
        self.assertIn("2026-10-02", chunks[-1]["text"])
        self.assertNotIn("GOLD", json.dumps(chunks))

    def test_char_splitting_reconstructs_turn_and_stable_ids(self):
        data = sample()
        data["conversation"]["session_1"][0]["text"] = "cat " * 70
        chunks = raw_chunks(data["sample_id"], data["conversation"], chunk_chars=80)
        text = "".join(c["text"].split(": ", 1)[1] for c in chunks if "D1:1" in c["source_ids"][0])
        self.assertEqual(text, "cat " * 70)
        self.assertEqual(len({c["source_ids"][0] for c in chunks}), len(chunks))

    def test_embedding_retrieval_deterministic_and_grouped(self):
        encoder = FakeEncoder()
        selection = [{"sample_id": "conv-A", "qa_index": 7, "question": "What is my cat called?", "category": 1},
                     {"sample_id": "conv-A", "qa_index": 9, "question": "Where did I move?", "category": 2}]
        answers, audit = prepare_retrieval({"conv-A": sample()["conversation"]}, selection, encoder, top_k=2)
        self.assertEqual(len(encoder.calls), 2)  # one corpus batch, one question batch
        self.assertEqual(answers[0]["contexts"][0]["source_ids"], ["conv-A:session_1:D1:1:0"])
        self.assertEqual(set(answers[0]), {"sample_id", "qa_index", "question", "category", "contexts"})
        self.assertEqual(len(audit[0]["ranking"]), 2)
        self.assertEqual(answers[1]["qa_index"], 9)
        self.assertEqual([r["rank"] for r in audit[0]["ranking"]], [1, 2])

    def test_bad_vectors_and_unavailable_sample(self):
        for bad in ([], [0, 0], [float("nan")], [True, 0]):
            with self.assertRaises(ValueError):
                normalized(bad)
        with self.assertRaises(ValueError):
            rank_chunks([{"text": "x"}], [[1, 0]], [0, 1], top_k=0)
        with self.assertRaisesRegex(ValueError, "Missing selected"):
            prepare_retrieval({}, [{"sample_id": "none"}], FakeEncoder())
        with self.assertRaises(ValueError):
            OllamaEmbeddings("model", "https://api.example.com/api/embed")

    def test_cache_avoids_embedding_repeated_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            chunks = raw_chunks("conv-A", sample()["conversation"])
            encoder = FakeEncoder()
            self.assertEqual(embed_chunks(chunks, encoder, tmp), embed_chunks(chunks, encoder, tmp))
            self.assertEqual(len(encoder.calls), 1)
            self.assertEqual(len(list(Path(tmp).glob("*.json"))), 1)

    def test_cli_run_preflight_and_output_no_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            conv = d / "locomo10.json"
            conv.write_text(json.dumps([{**sample(), "qa": [{"answer": "GOLD", "evidence": ["SECRET"]}]}]),
                            encoding="utf-8")
            select = d / "selected.jsonl"
            selected = {"sample_id": "conv-A", "qa_index": 4, "question": "My cat?", "category": 1}
            select.write_text(json.dumps(selected) + "\n", encoding="utf-8")
            output = d / "s0"
            report = run(conv, select, output, FakeEncoder(), top_k=60)
            self.assertEqual(report["status"], "retrieval_only_no_answers")
            self.assertEqual(report["answer_generation_calls"], 0)
            result = json.loads((output / "s0.inputs.jsonl").read_text())
            self.assertNotIn("GOLD", json.dumps(result))
            self.assertNotIn("SECRET", json.dumps(result))
            self.assertEqual(result["qa_index"], 4)
            self.assertEqual(result["contexts"][0]["kind"], "raw")
            self.assertEqual(len(result["contexts"]), 3)
            self.assertEqual(len((output / "s0.retrieval.jsonl").read_text().splitlines()), 1)
            with self.assertRaises(FileExistsError):
                run(conv, select, output, FakeEncoder())
            select.write_text(json.dumps({**selected, "answer": "SECRET"}) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "only"):
                load_questions(select)


if __name__ == "__main__":
    unittest.main()
