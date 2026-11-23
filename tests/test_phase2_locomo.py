import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_phase2_locomo as phase2


class Phase2Tests(unittest.TestCase):
    def test_shortage_redistributes_without_replacement(self):
        ids = ["a", "b"]
        rows = {cid: {"qa": [{"category": c} for c in [1] + [2, 3, 4, 5] * 20]}
                for cid in ids}
        selected = phase2.select_questions(rows, ids)
        self.assertEqual([sum(q["category"] == c for q in selected) for c in (1, 2, 3, 4)],
                         [2, 33, 33, 32])
        self.assertEqual(len({(q["sample_id"], q["qa_index"]) for q in selected}), 100)
        for row in rows.values():
            row["qa"] = [{"category": 2}]
        self.assertEqual(len(phase2.select_questions(rows, ids)), 2)

    @unittest.skipUnless((ROOT / "data/raw/locomo10.json").exists(), "Pinned LoCoMo file required")
    def test_frozen_release_by_original_session_turn_and_qa_offsets(self):
        def read(path):
            return json.loads((ROOT / path).read_text(encoding="utf-8"))

        rows = read("data/raw/locomo10.json")
        source = {r["sample_id"]: r for r in rows}
        phase1 = read("configs/locomo-smoke.json")
        manifest, files = phase2.prepare(rows, phase1)
        self.assertEqual(manifest, read("configs/locomo-phase2-heldout.json"))
        self.assertEqual(manifest["category_counts"], dict.fromkeys("1234", 25))
        heldout = set(phase1["splits"]["heldout"])
        self.assertTrue(heldout.isdisjoint(phase1["splits"]["development"]))
        questions = files["model/heldout.inputs.json"]
        labels = files["scoring/heldout.labels.json"]
        self.assertEqual(len(questions), len(labels))
        self.assertEqual(len({(q["sample_id"], q["qa_index"]) for q in questions}), 100)
        self.assertEqual({q["sample_id"] for q in questions}, heldout)
        turn_ids = {cid: {turn["dia_id"] for k, turns in source[cid]["conversation"].items()
                          if k.startswith("session_") and k[8:].isdigit() for turn in turns}
                    for cid in heldout}
        reference_counts = []
        for question, label in zip(questions, labels, strict=True):
            cid, i = question["sample_id"], question["qa_index"]
            qa = source[cid]["qa"][i]
            key = {"sample_id": cid, "qa_index": i, "category": qa["category"]}
            self.assertEqual(question, {**key, "question": qa["question"]})
            self.assertEqual(label, {**key, "answer": qa["answer"], "evidence": qa["evidence"]})
            references = [ref for entry in label["evidence"] for ref in entry.split()]
            reference_counts.append((len(references), sum(ref in turn_ids[cid] for ref in references)))
        self.assertEqual(sum(total for total, _ in reference_counts), 193)
        self.assertEqual(sum(valid for _, valid in reference_counts), 192)
        self.assertEqual(reference_counts.count((0, 0)), 2)
        self.assertEqual(sum(0 < valid < total for total, valid in reference_counts), 1)
        for row in files["model/heldout.conversations.json"]:
            cid = row["sample_id"]
            original = source[cid]["conversation"]
            conv = row["conversation"]
            sessions = [k for k in original if k.startswith("session_") and k[8:].isdigit()]
            expected = {k: original[k] for k in ("speaker_a", "speaker_b")}
            for session in sessions:
                expected[session + "_date_time"] = original[session + "_date_time"]
                expected[session] = [{k: turn[k] for k in ("dia_id", "speaker", "text", "blip_caption")
                                      if k in turn and (k != "blip_caption" or turn[k])}
                                     for turn in original[session]]
            self.assertEqual(row, {"sample_id": cid, "conversation": expected})
        first = phase1["questions"][0]
        expected = {**first, "question": source[first["sample_id"]]["qa"][first["qa_index"]]["question"]}
        self.assertEqual(files["model/development.one.inputs.json"], [expected])
        for name, payload in files.items():
            digest = hashlib.sha256(phase2.encode(payload)).hexdigest()
            self.assertEqual(digest, manifest["output_sha256"][name])
