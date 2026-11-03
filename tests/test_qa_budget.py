import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from evidence_budget import ASSET_URL, EvidenceBudget, render_evidence
from llm_client import validate_config
from metamem_pilot.data import read, write
from run_qa import load_inputs, run, write_jsonl
from verify_qa_run import jsonl, verify_run


class QABudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cache = Path(os.environ.get("QA_TOKENIZER_CACHE", ROOT / "data/tokenizer-cache"))
        try:
            cls.budget = EvidenceBudget(4096, cls.cache)
        except (ValueError, ImportError) as exc:
            raise unittest.SkipTest(f"Prepare requirements-qa.txt and the offline counter cache: {exc}")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.config = read(ROOT / "configs/qa-phase2.json")
        self.config_path = self.directory / "config.json"
        write(self.config_path, self.config)
        self.inputs = self.directory / "inputs.jsonl"
        self.rows = load_inputs(ROOT / "configs/qa-smoke.inputs.jsonl")
        write_jsonl(self.inputs, self.rows)

    def execute(self, name="run", *, mock=True, variant="A"):
        out = self.directory / name
        with redirect_stdout(io.StringIO()):
            code = run(self.inputs, self.config_path, "S2", out, mock,
                       variant=variant, tokenizer_cache=self.cache)
        return out, code

    def test_exact_budget_counts_headers_unicode_and_literal_special_tokens(self):
        contexts = copy.deepcopy(self.rows[0]["contexts"])
        contexts[0]["text"] += "\n日期不改写。 <|endoftext|> {question}"
        contexts[0]["source_ids"] = ["long-source-" * 200]
        measured = self.budget.count(contexts)
        exact = EvidenceBudget(measured, self.cache).prepare(contexts)
        self.assertEqual(exact["proxy_tokens"], len(self.budget.encoding.encode_ordinary(exact["text"])))
        self.assertIn(contexts[0]["text"], exact["text"])
        self.assertIn("[E1] raw\n", exact["text"])
        self.assertNotIn("long-source-", exact["text"])
        self.assertEqual(exact["source_map"][0]["source_ids"], contexts[0]["source_ids"])
        with self.assertRaisesRegex(ValueError, "budget exceeded"):
            EvidenceBudget(measured - 1, self.cache).prepare(contexts)
        self.assertEqual(self.budget.prepare([])["proxy_tokens"], 0)

    def test_missing_or_corrupt_cache_never_downloads(self):
        import hashlib
        cache = self.directory / "empty-cache"
        cache.mkdir()
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            with self.assertRaisesRegex(ValueError, "pinned"):
                EvidenceBudget(4096, cache)
            (cache / hashlib.sha1(ASSET_URL.encode()).hexdigest()).write_bytes(b"wrong asset")
            with self.assertRaisesRegex(ValueError, "pinned"):
                EvidenceBudget(4096, cache)

    def test_last_row_over_budget_blocks_entire_batch_before_client_creation(self):
        self.rows[-1]["contexts"][0]["text"] = "large evidence " * 5000
        self.inputs.unlink()
        write_jsonl(self.inputs, self.rows)
        with patch("run_qa.Client") as client:
            with self.assertRaisesRegex(ValueError, "budget exceeded"):
                self.execute(mock=False)
        client.assert_not_called()
        self.assertFalse((self.directory / "run").exists())

    def test_variant_and_single_common_prompt_are_required(self):
        with self.assertRaisesRegex(ValueError, "variant"):
            self.execute(variant=None)
        bad = copy.deepcopy(self.config)
        bad["method_prompts"]["S0"] += "different instruction"
        with self.assertRaisesRegex(ValueError, "same user prompt"):
            validate_config(bad)
        for key in bad["method_prompts"]:
            bad["method_prompts"][key] = "{context} {context} {question}"
        with self.assertRaisesRegex(ValueError, "exactly once"):
            validate_config(bad)

    def test_mock_requests_are_rebuilt_without_key_or_network_and_have_distinct_run_ids(self):
        with patch("llm_client.urllib.request.OpenerDirector.open", side_effect=AssertionError("network forbidden")):
            out, code = self.execute()
            other, _ = self.execute("other", variant="N")
            verified = verify_run(out, self.cache)
        self.assertEqual(code, 0)
        self.assertEqual(verified["real_calls"], 0)
        self.assertEqual(verified["recorded_usage_totals"], {})
        self.assertNotEqual(read(out / "run.json")["run_id"], read(other / "run.json")["run_id"])
        first, second = jsonl(out / "requests.jsonl")[0], jsonl(other / "requests.jsonl")[0]
        self.assertEqual(first["request"], second["request"])
        self.assertEqual(first["request_sha256"], second["request_sha256"])
        self.assertNotEqual(first["variant"], second["variant"])
        self.assertIn(render_evidence(self.rows[0]["contexts"]), first["request"]["messages"][1]["content"])
        self.inputs.unlink()
        self.config_path.unlink()
        self.assertTrue(verify_run(out, self.cache)["verified"])

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "offline-test-only"})
    def test_wire_payload_usage_abstention_and_failure_are_bound_to_snapshot(self):
        response = {"model": "offline-provider-fixture", "choices": [{"finish_reason": "stop",
                    "message": {"content": "I don't know."}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 5, "total_tokens": 105,
                              "prompt_cache_hit_tokens": 80}}
        with patch("llm_client.urllib.request.build_opener") as factory:
            factory.return_value.open.side_effect = [io.BytesIO(json.dumps(response).encode()), TimeoutError()]
            out, code = self.execute(mock=False)
        self.assertEqual(code, 1)
        prepared = jsonl(out / "requests.jsonl")
        for sent, expected in zip(factory.return_value.open.call_args_list, prepared):
            self.assertEqual(json.loads(sent.args[0].data), expected["request"])
        verified = verify_run(out, self.cache)
        self.assertEqual(verified["real_calls"], 2)  # Recorded transport attempts, provided by offline doubles.
        self.assertEqual(verified["abstained_questions"], 1)
        self.assertEqual(verified["recorded_usage_totals"]["total_tokens"], 105)
        self.assertEqual(verified["usage_missing_call_counts"]["total_tokens"], 1)
        self.assertEqual(read(out / "run.json")["processed_questions"], 2)

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "offline-test-only"})
    def test_interrupt_preserves_planned_denominator(self):
        with patch("llm_client.urllib.request.build_opener") as factory:
            factory.return_value.open.side_effect = KeyboardInterrupt()
            out, code = self.execute(mock=False)
        self.assertEqual(code, 130)
        verified = verify_run(out, self.cache)
        self.assertEqual((verified["planned_questions"], verified["processed_questions"],
                          verified["unprocessed_questions"]), (2, 1, 1))

    def test_tampered_variant_payload_mapping_and_usage_are_rejected(self):
        out, _ = self.execute()
        for name, mutate in [
            ("calls.jsonl", lambda row: row.update(variant="N")),
            ("calls.jsonl", lambda row: row["request"]["messages"][1].update(content="changed")),
            ("predictions.jsonl", lambda row: row.update(source_ids=["wrong-source"])),
            ("predictions.jsonl", lambda row: row.update(usage={"total_tokens": 100})),
            ("requests.jsonl", lambda row: row["evidence"].update(proxy_tokens=0)),
        ]:
            path = out / name
            original = path.read_bytes()
            rows = jsonl(path)
            mutate(rows[0])
            path.unlink()
            write_jsonl(path, rows)
            with self.subTest(name=name), self.assertRaises(ValueError):
                verify_run(out, self.cache)
            path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
