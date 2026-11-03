"""Prepare offline source/memory review material; never generate or judge answers.

The output contains frozen scoring labels and conversation text. Keep it in the
ignored output directory; publish only the separate annotation/aggregate report.
"""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import pickle
import random
import re
import sqlite3
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class StoredPoint:
    def __setstate__(self, state):
        self.value = state["__dict__"]


class PointReader(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) == ("qdrant_client.http.models.models", "PointStruct"):
            return StoredPoint
        raise ValueError(f"Unexpected serialized class: {module}.{name}")


def archive_rows(path, entry):
    with zipfile.ZipFile(path) as archive:
        return [json.loads(line) for line in archive.read(entry).splitlines()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--event-archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    config = read(ROOT / "configs/locomo-smoke.json")
    if digest(args.source.read_bytes()) != config["source"]["sha256"]:
        raise ValueError("Official LoCoMo source hash mismatch")
    expected = read(ROOT / "reports/structmem-complete-handoff.json")
    if digest(args.event_archive.read_bytes()) != expected["sha256"]:
        raise ValueError("C event archive hash mismatch")
    args.out.mkdir(parents=True, exist_ok=False)
    raw = {row["sample_id"]: row for row in read(args.source)
           if row["sample_id"] in config["splits"]["development"]}
    messages = {}
    for sid, row in raw.items():
        conversation = row["conversation"]
        for session in sorted((k for k in conversation if re.fullmatch(r"session_\d+", k)),
                              key=lambda k: int(k.split("_")[1])):
            turns = conversation[session]
            for i, turn in enumerate(turns):
                messages[f"{sid}/{turn['dia_id']}"] = {
                    **turn, "session": session, "date": conversation[session + "_date_time"],
                    "neighbors": turns[max(0, i-1):i+2],
                }
    events = {}
    with zipfile.ZipFile(args.event_archive) as archive:
        file_hashes = json.loads(archive.read("complete-handoff/files.sha256.json"))
        for path, sha in file_hashes.items():
            if digest(archive.read("complete-handoff/" + path)) != sha:
                raise ValueError(f"C archive member hash mismatch: {path}")
        for sid in config["splits"]["development"]:
            member = f"{sid}/qdrant/collection/{sid.replace('-', '_')}_events/storage.sqlite"
            local = args.out / f"{sid}.sqlite"
            local.write_bytes(archive.read("complete-handoff/" + member))
            connection = sqlite3.connect(f"file:{local.resolve()}?mode=ro", uri=True)
            for blob, in connection.execute("SELECT point FROM points"):
                point = PointReader(io.BytesIO(blob)).load().value
                payload = point["payload"]
                key = f"{sid}/event/{point['id']}"
                source = payload["source_key"]
                if source not in messages or payload["source_sample_id"] != sid:
                    raise ValueError("Event source binding mismatch")
                events[key] = {"id": key, "payload": payload, "source": messages[source]}
            connection.close()
    if len(events) != expected["entry_count"]:
        raise ValueError("Event count mismatch")
    predictions = {}
    archive_hashes = {}
    frozen_archives = {Path(r["archive_path"]).name: r["archive_sha256"]
                       for r in read(ROOT / "reports/phase2-context-audit-20261103.json")["results"]}
    for method, filename, entry in (
        ("S0", "s0-predictions-for-E-20261019.zip", "predictions.jsonl"),
        ("S2", "s2-predictions-for-E-20261020.zip", "predictions30.jsonl"),
    ):
        path = ROOT / "reports/artifacts" / filename
        if digest(path.read_bytes()) != frozen_archives[filename]:
            raise ValueError(f"Prediction archive hash mismatch: {filename}")
        predictions[method] = {(r["sample_id"], r["qa_index"]): r for r in archive_rows(path, entry)}
        archive_hashes[filename] = digest(path.read_bytes())
    judgments = read(ROOT / "reports/e-judge-audit-handoff-20261021.json")["records"]
    marks = {}
    for row in judgments:
        key = (row["sample_id"], row["qa_index"])
        question = raw[key[0]]["qa"][key[1]]
        pred = predictions[row["method"]][key]
        binding = {"question": question["question"], "reference_answer": question["answer"],
                   "model_answer": pred["prediction"]}
        actual = digest(json.dumps(binding, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
        if actual != row["input_sha256"]:
            raise ValueError(f"Judge input binding mismatch: {row['method']}/{key}")
        marks[(row["method"], *key)] = row["raw_judgment"]
    by_source = {}
    for event in events.values():
        by_source.setdefault(event["payload"]["source_key"], []).append(event)
    questions = []
    unique_summaries = {}
    selected_events = set()
    for frozen in config["questions"]:
        sid, qi = frozen["sample_id"], frozen["qa_index"]
        q = raw[sid]["qa"][qi]
        s2 = predictions["S2"][(sid, qi)]
        contexts = s2["contexts"]
        positions = {c["source_ids"][0]: i+1 for i, c in enumerate(contexts)}
        for context in contexts:
            identity = context["source_ids"][0]
            if context["kind"] == "event":
                selected_events.add(identity)
                if events[identity]["payload"]["memory"] not in context["text"]:
                    raise ValueError("Retrieved event differs from C snapshot")
            else:
                if identity in unique_summaries and unique_summaries[identity] != context:
                    raise ValueError("Synthesis content changed across questions")
                unique_summaries[identity] = context
        evidence = []
        for mid in q["evidence"]:
            source_key = f"{sid}/{mid}"
            evidence.append({"source_key": source_key, "raw": messages[source_key],
                             "events": [{"id": e["id"], "text": e["payload"]["memory"],
                                         "selected_rank": positions.get(e["id"])}
                                        for e in by_source.get(source_key, [])]})
        questions.append({"sample_id": sid, "qa_index": qi, "category": q["category"],
                          "question": q["question"], "reference": q["answer"], "evidence": evidence,
                          "s0_prediction": predictions["S0"][(sid, qi)]["prediction"],
                          "s2_prediction": s2["prediction"], "s0_raw": marks[("S0",sid,qi)],
                          "s2_raw": marks[("S2",sid,qi)], "contexts": contexts})
    rng = random.Random(20261103)
    sample = []
    for sid in config["splits"]["development"]:
        population = sorted(k for k in events if k.startswith(sid + "/"))
        sample.extend(events[k] for k in rng.sample(population, 20))
    cue_patterns = {
        "negation": r"\b(?:not|never|no longer|haven't|hasn't|don't|doesn't|can't|couldn't|wouldn't|didn't)\b",
        "modality": r"\b(?:if|wish|might|would|could)\b",
        "relative_time": r"\b(?:yesterday|tomorrow|last (?:week|year|month|friday|sunday|wednesday)|next (?:week|month|saturday))\b",
    }
    cue_rng, used, cue_items, cue_counts = random.Random(20261103), set(), [], {}
    for group, pattern in cue_patterns.items():
        pool = sorted(k for k in by_source if re.search(pattern, messages[k]["text"], re.I))
        cue_counts[group] = len(pool)
        for key in cue_rng.sample([k for k in pool if k not in used], 8):
            used.add(key)
            cue_items.append({"cue_group": group, "source_key": key, "raw": messages[key],
                              "events": [{"id": e["id"], "text": e["payload"]["memory"]}
                                         for e in by_source[key]]})
    missing_sources = [{"source_key": key, "raw": value} for key, value in messages.items()
                       if key not in by_source]
    manifest = {
        "date": "2026-11-03", "api_calls": 0, "source_sha256": config["source"]["sha256"],
        "event_archive_sha256": expected["sha256"], "event_archive_members_verified": len(file_hashes),
        "prediction_archives": archive_hashes, "judge_bindings_verified": len(marks),
        "conversations": config["splits"]["development"], "messages": len(messages),
        "event_population": len(events), "retrieved_unique_events": len(selected_events),
        "retrieved_unique_syntheses": len(unique_summaries), "questions": len(questions),
        "s2_raw_judgments": dict(Counter(q["s2_raw"] for q in questions)),
        "event_sample": {"seed": 20261103, "per_conversation": 20, "total": len(sample),
                         "ids": [e["id"] for e in sample]},
        "cue_sample": {"seed": 20261103, "pool_counts": cue_counts, "total": len(cue_items),
                       "source_keys": [x["source_key"] for x in cue_items]},
        "messages_without_event": len(missing_sources),
        "reference_source_occurrences": sum(len(q["evidence"]) for q in questions),
        "unique_reference_sources": len({e["source_key"] for q in questions for e in q["evidence"]}),
        "reference_associated_events": len({e["id"] for q in questions for s in q["evidence"] for e in s["events"]}),
        "limitations": ["The event sample is descriptive and conversation-stratified.",
                        "Only the 69 retrieved syntheses, not the full 91-item synthesis store, are available.",
                        "Semantic review is AI-assisted, not member acceptance or a causal intervention."],
    }
    dump(args.out / "manifest.json", manifest)
    dump(args.out / "questions.json", questions)
    dump(args.out / "event-sample.json", sample)
    dump(args.out / "events.json", events)
    dump(args.out / "summaries.json", unique_summaries)
    dump(args.out / "cue-sample.json", {"seed": 20261103, "pool_counts": cue_counts,
                                      "patterns": cue_patterns, "items": cue_items})
    dump(args.out / "sources-without-event.json", missing_sources)
    print(json.dumps({k: v for k, v in manifest.items() if k not in ("event_sample", "cue_sample")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
