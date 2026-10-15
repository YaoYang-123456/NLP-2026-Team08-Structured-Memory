import argparse
import copy
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
from metamem_pilot.client import CallError, Client, STAGES, validate_config
from metamem_pilot.data import digest, file_hash, overlap_report, read, retrieve, split_rows, write
from metamem_pilot.pipeline import (answer_prompt, apply_operations, evaluate, learn, load_rules,
                                     load_split, metrics, partial_groups, verify_prior, test as run_test)
from run_pilot import effective_config, fingerprint


def question(qid="q1", session_id="s1", text="The trip cost 100 dollars."):
    return {"question_id": qid, "question_type": "multi-session", "question": "What did the trip cost?",
            "question_date": "2026-01-01", "answer": "SECRET_LABEL_SENTINEL",
            "answer_session_ids": [session_id], "haystack_session_ids": [session_id],
            "haystack_dates": ["2025-01-01"],
            "haystack_sessions": [[{"role": "user", "content": text, "has_answer": True}]]}


class RecordingClient:
    config = {"backend": "mock", "rule_max_bytes": 2048}

    def __init__(self, fail=None, judge="yes"):
        self.calls = []
        self.fail = fail
        self.judge = judge

    def call(self, stage, prompt, qid, attempt=0):
        self.calls.append((stage, prompt, qid))
        if stage == self.fail:
            raise CallError("deliberate service error")
        return self.judge if stage == "judge" else "a generated answer"


class PipelineTests(unittest.TestCase):
    def test_answer_and_evidence_annotations_are_isolated(self):
        row = retrieve(question())
        prompt = answer_prompt(row, [])
        self.assertNotIn("SECRET_LABEL_SENTINEL", prompt)
        self.assertNotIn("has_answer", json.dumps(row))
        self.assertNotIn("answer_session_ids", json.dumps(row))
        client = RecordingClient()
        def labels():
            self.assertEqual([s for s, _, _ in client.calls], ["answer_eval"])
            return {"q1": "SECRET_LABEL_SENTINEL"}
        evaluate([row], [], client, labels)
        self.assertNotIn("SECRET_LABEL_SENTINEL", client.calls[0][1])
        self.assertIn("SECRET_LABEL_SENTINEL", client.calls[1][1])

    def test_service_and_parse_errors_are_not_wrong_answers(self):
        row = retrieve(question())
        for fail, judge, expected in [("answer_eval", "yes", "generation_failed"),
                                       ("judge", "yes", "judge_failed"), (None, "maybe", "judge_parse_failed")]:
            output = evaluate([row], [], RecordingClient(fail, judge), lambda: {"q1": "truth"})
            self.assertEqual(output[0]["status"], expected)
            self.assertIsNone(output[0]["correct"])
            self.assertIsNone(metrics(output, False)["accuracy_on_valid"])
            self.assertEqual(metrics(output, False)["valid_scores"], 0)

    def test_same_text_different_ids_not_mixed(self):
        rows = [{"question_id": "a", "status": "valid", "correct": True},
                {"question_id": "a", "status": "valid", "correct": True},
                {"question_id": "b", "status": "valid", "correct": False},
                {"question_id": "b", "status": "valid", "correct": False}]
        eligible, skipped = partial_groups(rows, 2)
        self.assertEqual(eligible, {})
        self.assertEqual(skipped, {"a": "all_correct", "b": "all_wrong"})
        rows[1]["status"] = "judge_failed"
        self.assertEqual(partial_groups(rows, 2)[1]["a"], "incomplete_or_service_failure")

    def test_rules_missing_wrong_kind_or_empty_manual_fail(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "rules.json"
            with self.assertRaises(FileNotFoundError):
                load_rules(p, "learned", 2048)
            write(p, {"kind": "manual-fixed", "rules": []})
            with self.assertRaises(ValueError):
                load_rules(p, "manual-fixed", 2048)
            with self.assertRaises(ValueError):
                load_rules(p, "baseline", 2048)

    def test_rule_operations_and_budget(self):
        self.assertEqual(apply_operations(["old"], [{"operation": "update", "id": "M0", "content": "new"}], 100), ["new"])
        with self.assertRaises(ValueError):
            apply_operations([], [{"operation": "delete", "id": "M0"}], 100)
        with self.assertRaises(ValueError):
            apply_operations([], [{"operation": "add", "content": "x" * 200}], 100)

    def test_group_overlap_rejected_by_selection(self):
        rows = []
        for i in range(18):
            row = question(f"q{i}", f"s{i // 2}", f"unique context group {i // 2}")
            row["question"] = f"Question {i // 2}"
            rows.append(row)
        splits = split_rows(rows, set(), sizes=(3, 3, 3))
        self.assertEqual([len(v) for v in splits.values()], [3, 3, 3])
        self.assertTrue(all(n == 0 for pair in overlap_report(splits).values() for n in pair.values()))
        self.assertEqual(splits, split_rows(rows, set(), sizes=(3, 3, 3)))

    def test_no_partial_groups_no_rule_fallback(self):
        # Run over the frozen real training inputs, with a simulated always-wrong judge.
        with tempfile.TemporaryDirectory() as d:
            result = learn(ROOT / "data/pilot", Path(d), RecordingClient(judge="no"), limit=5)
            self.assertEqual(result["outcome"], "no_rules_learned")
            self.assertEqual(result["batches"][0]["eligible_ids"], [])
            self.assertEqual(read(Path(d) / "rules-01.json")["rules"], [])

    def test_changed_config_or_phase_cannot_reuse_prior_run(self):
        with tempfile.TemporaryDirectory() as d:
            write(Path(d) / "run.json", {"fingerprint": "a", "command": "smoke", "status": "completed"})
            with self.assertRaises(ValueError):
                verify_prior(Path(d), "b", "smoke")
            with self.assertRaises(ValueError):
                verify_prior(Path(d), "a", "learn")

    def test_frozen_rules_cannot_be_modified_before_test(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            write(directory / "run.json", {"fingerprint": "fp", "command": "select", "status": "completed"})
            write(directory / "B0.json", {"kind": "baseline", "rules": []})
            entry = {"file": "B0.json", "kind": "baseline", "sha256": file_hash(directory / "B0.json")}
            write(directory / "selection.json", {"frozen": {"B0": entry, "B1": entry, "B2": entry}})
            write(directory / "B0.json", {"kind": "baseline", "rules": ["changed"]})
            client = RecordingClient()
            with self.assertRaises(ValueError):
                run_test(ROOT / "data/pilot", directory, client, directory, "fp")
            self.assertEqual(client.calls, [])

    def test_all_stage_settings_participate_in_fingerprint(self):
        config = read(ROOT / "configs/local.example.json")
        before = fingerprint(config, ROOT / "data/pilot")
        for stage in STAGES:
            changed = copy.deepcopy(config)
            changed["stages"][stage]["max_tokens"] += 1
            self.assertNotEqual(before, fingerprint(changed, ROOT / "data/pilot"))

    def test_three_conditions_share_facts_and_mock_scores_are_null(self):
        row = retrieve(question())
        results = [evaluate([row], rules, RecordingClient(), lambda: {"q1": "truth"})
                   for rules in ([], ["manual"], ["learned"])]
        self.assertEqual(len({r[0]["facts_sha256"] for r in results}), 1)
        self.assertIsNone(metrics(results[0], True)["accuracy_on_valid"])
        self.assertEqual(metrics(results[0], True)["valid_model_scores"], 0)

    def test_frozen_real_data_and_rules(self):
        manifest = read(ROOT / "data/pilot/manifest.json")
        self.assertEqual({k: len(v) for k, v in manifest["splits"].items()}, {"train": 20, "validation": 10, "test": 20})
        self.assertTrue(all(n == 0 for pair in manifest["overlaps"].values() for n in pair.values()))
        for split in manifest["splits"]:
            rows = load_split(ROOT / "data/pilot", split)
            self.assertTrue(any(r["question_id"].endswith("_abs") for r in rows))
            self.assertEqual(len({r["task"] for r in rows}), 6)


class TransportTests(unittest.TestCase):
    def test_cli_options_reach_every_http_stage_and_usage_is_recorded(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"])) ))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"model": "fixture", "choices": [{"message": {"content": "yes"}, "finish_reason": "stop"}],
                                             "usage": {"prompt_tokens": 3, "completion_tokens": 1}}).encode())
            def log_message(self, *args):
                pass
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            args = argparse.Namespace(config=ROOT / "configs/local.example.json", mock=True,
                                      max_tokens=17, temperature=0.2, top_p=0.6)
            config = effective_config(args)
            config["backend"] = "local"
            config["answer"] = config["judge"] = {"base_url": f"http://127.0.0.1:{server.server_port}/v1", "model": "fixture"}
            with tempfile.TemporaryDirectory() as d:
                log = Path(d) / "calls.jsonl"
                client = Client(config, log)
                for stage in sorted(STAGES):
                    client.call(stage, "synthetic transport test", "q")
                events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
                self.assertEqual(len(events), 6)
                self.assertTrue(all(e["usage"]["prompt_tokens"] == 3 for e in events))
            self.assertEqual(len(received), 6)
            self.assertTrue(all((r["max_tokens"], r["temperature"], r["top_p"]) == (17, 0.2, 0.6) for r in received))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_unconfigured_service_is_disabled(self):
        with self.assertRaises(ValueError):
            validate_config(read(ROOT / "configs/local.example.json"))


if __name__ == "__main__":
    unittest.main()
