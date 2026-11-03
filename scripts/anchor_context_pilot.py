"""Compare whole, sentence and anchor-preserving context packing offline.

All methods rank the same retrieval units. Only the expansion from a selected
synthesis sentence to returned context differs. Frozen evaluation annotations
are deliberately not read here; use offline_coverage_pilot.py evaluate later.
"""
import argparse
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from audit_development_memory import PointReader, digest, dump, read
from flat_rag import SentenceTransformerEmbeddings
from offline_coverage_pilot import bm25, tokenizer, words
from structmem_retrieve import memory_text, validate_vector

ANAPHORA = re.compile(r"^(?:He|She|They|It|His|Her|Their|This|That|These|Those|The (?:picture|photo|story|experience|event|trip|visit|conversation|exchange|support|producers))\b", re.I)
RELATIVE = re.compile(r"\b(?:yesterday|tomorrow|last|previous|next|day before|week before|year before)\b", re.I)
EXPLICIT_DATE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2},? \d{4})\b", re.I)


def split_summary(text):
    header, body = text.split("\n", 1)
    if not header.startswith("Time range:"):
        raise ValueError("Synthesis time-range header missing")
    spans = [x for x in re.split(r"(?<=[.!?])\s+|\n+", body) if x]
    return header, spans


def dependencies(spans):
    edges = {}
    for i, span in enumerate(spans):
        parents = set()
        if i and ANAPHORA.search(span):
            parents.add(i - 1)
        if RELATIVE.search(span):
            earlier = [j for j in range(i) if EXPLICIT_DATE.search(spans[j])]
            if earlier:
                parents.add(earlier[-1])
        edges[i] = sorted(parents)
    return edges


def closure(index, edges):
    result, stack = set(), [index]
    while stack:
        i = stack.pop()
        if i not in result:
            result.add(i)
            stack.extend(edges[i])
    return result


def render(selected, units, parents):
    contexts, blocks = [], []
    # Keep each summary's fragments in original order and mark omissions.
    parent_ids = sorted({units[i]["parent"] for i in selected if units[i]["kind"] == "synthesis"})
    for parent in parent_ids:
        record = parents[parent]
        indices = sorted(units[i]["sentence"] for i in selected if units[i]["parent"] == parent)
        pieces, previous = [], -1
        for i in indices:
            if i > previous + 1:
                pieces.append("[...]")
            pieces.append(record["spans"][i])
            previous = i
        if previous < len(record["spans"]) - 1:
            pieces.append("[...]")
        text = record["header"] + "\n" + "\n".join(pieces)
        contexts.append({"source_ids": record["source_ids"], "kind": "synthesis", "text": text})
        blocks.append(f"[S{record['number']:03d}]\n{text}\n\n")
    for i in sorted(selected):
        unit = units[i]
        if unit["kind"] == "event":
            contexts.append({"source_ids": unit["source_ids"], "kind": "event", "text": unit["text"]})
            blocks.append(f"[E{i+1:03d}]\n{unit['text']}\n\n")
    return contexts, "".join(blocks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/phase2-anchor-pilot.json")
    for name in ("baseline-run", "events", "model-cache", "tokenizer-cache", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import numpy as np
    from nltk.stem import PorterStemmer
    from importlib.metadata import version
    config = read(args.config)
    baseline = read(args.baseline_run / "selections.json")
    provenance = read(args.baseline_run / "manifest.json")
    if digest((args.baseline_run / "selections.json").read_bytes()) != provenance["selections_sha256"]:
        raise ValueError("Baseline selections hash mismatch")
    enc = tokenizer(args.tokenizer_cache)
    encoder = SentenceTransformerEmbeddings(provenance["embedding"], args.model_cache)
    bank = {}
    for filename, expected in provenance["event_sqlite_sha256"].items():
        path = args.events / filename
        if digest(path.read_bytes()) != expected:
            raise ValueError("Event database differs from baseline")
        sid = path.stem
        conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
        for blob, in conn.execute("SELECT point FROM points"):
            point = PointReader(io.BytesIO(blob)).load().value
            validate_vector(point["vector"])
            point["id"] = f"{sid}/event/{point['id']}"
            bank[point["id"]] = point
        conn.close()
    all_summaries = {c["source_ids"][0]: c for r in baseline for c in r["methods"]["mmr"]["contexts"] if c["kind"] == "synthesis"}
    documents = {uid: split_summary(c["text"]) for uid, c in all_summaries.items()}
    sentence_keys = [(uid, i) for uid in sorted(documents) for i in range(len(documents[uid][1]))]
    sentence_vectors = dict(zip(sentence_keys, encoder.encode([documents[uid][1][i] for uid, i in sentence_keys])))
    queries = encoder.encode([r["question"] for r in baseline])
    args.out.mkdir(parents=True, exist_ok=False)
    dump(args.out / "sentence-vectors.json", {"keys": sentence_keys, "vectors": [sentence_vectors[k] for k in sentence_keys]})
    stemmer = PorterStemmer()
    rows, metadata = [], []
    for row, query in zip(baseline, queries):
        units, parents = [], {}
        for uid in row["candidate_ids"]:
            point = bank[uid]
            units.append({"id": uid, "kind": "event", "parent": None, "text": memory_text(point, "event"),
                          "vector": point["vector"], "source_ids": [uid, point["payload"]["source_key"]]})
        original = [c for c in row["methods"]["mmr"]["contexts"] if c["kind"] == "synthesis"]
        for number, context in enumerate(original, 1):
            uid = context["source_ids"][0]
            header, spans = documents[uid]
            edges = dependencies(spans)
            offsets = {}
            for i, span in enumerate(spans):
                offsets[i] = len(units)
                units.append({"id": f"{uid}/sentence/{i}", "kind": "synthesis", "parent": uid,
                              "sentence": i, "text": span, "vector": sentence_vectors[uid, i]})
            parents[uid] = {"header": header, "spans": spans, "edges": edges, "offsets": offsets,
                            "source_ids": context["source_ids"], "number": number}
        matrix = np.asarray([u["vector"] for u in units], dtype=np.float64)
        matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
        dense = matrix @ (np.asarray(query) / np.linalg.norm(query))
        lexical = bm25([words(u["text"], stemmer) for u in units], words(row["question"], stemmer), config["ranking"])
        dense_order = sorted(range(len(units)), key=lambda i: (-float(dense[i]), units[i]["id"]))
        lex_order = [i for i in sorted(range(len(units)), key=lambda i: (-lexical[i], units[i]["id"])) if lexical[i] > 0]
        ranks = [{i: r+1 for r, i in enumerate(order)} for order in (dense_order, lex_order)]
        relevance = np.asarray([sum(1/(config["ranking"]["rrf_k"] + rank[i]) for rank in ranks if i in rank) for i in range(len(units))])
        relevance /= relevance.max()
        similarity = np.clip(matrix @ matrix.T, 0, 1)
        expansions = {}
        for mode in config["packing"]:
            expansions[mode] = []
            for i, unit in enumerate(units):
                if unit["kind"] == "event" or mode == "sentence":
                    expanded = {i}
                else:
                    parent = parents[unit["parent"]]
                    indices = range(len(parent["spans"])) if mode == "whole" else closure(unit["sentence"], parent["edges"])
                    expanded = {parent["offsets"][j] for j in indices}
                expansions[mode].append(expanded)
        methods = {}
        for budget in config["budgets"]:
            for mode in config["packing"]:
                selected, rejected, steps = set(), set(), []
                for _ in range(len(units)):
                    remaining = set(range(len(units))) - selected - rejected
                    if not remaining:
                        break
                    redundancy = similarity[:, sorted(selected)].max(axis=1) if selected else np.zeros(len(units))
                    utility = config["ranking"]["mmr_relevance"] * relevance - config["ranking"]["mmr_redundancy"] * redundancy
                    i = min(remaining, key=lambda j: (-float(utility[j]), units[j]["id"]))
                    added = expansions[mode][i] - selected
                    contexts, rendered = render(selected | added, units, parents)
                    cost = len(enc.encode(rendered))
                    if cost > budget:
                        rejected.add(i)
                        continue
                    selected.update(added)
                    steps.append({"seed": units[i]["id"], "added": [units[j]["id"] for j in sorted(added)], "proxy_tokens": cost})
                contexts, rendered = render(selected, units, parents)
                cost = len(enc.encode(rendered))
                assert cost <= budget
                missing = []
                for i in sorted(selected):
                    if units[i]["kind"] == "synthesis":
                        needs = expansions["anchor"][i] - selected
                        if needs:
                            missing.append({"sentence": units[i]["id"], "missing": [units[j]["id"] for j in sorted(needs)]})
                methods[f"{mode}_{budget}"] = {"contexts": contexts, "rendered": rendered, "proxy_tokens": cost,
                    "event_ids": [units[i]["id"] for i in sorted(selected) if units[i]["kind"] == "event"],
                    "sentence_ids": [units[i]["id"] for i in sorted(selected) if units[i]["kind"] == "synthesis"],
                    "synthesis_proxy_tokens": sum(len(enc.encode(f"[S{parents[c['source_ids'][0]]['number']:03d}]\n{c['text']}\n\n")) for c in contexts if c["kind"] == "synthesis"),
                    "declared_dependency_gaps": missing, "steps": steps}
        rows.append({"sample_id": row["sample_id"], "qa_index": row["qa_index"], "question": row["question"],
                     "candidate_ids": [u["id"] for u in units], "methods": methods})
        metadata.append({"sample_id": row["sample_id"], "qa_index": row["qa_index"],
                         "parents": parents, "relevance": relevance.tolist(), "units": [{k:v for k,v in u.items() if k != "vector"} for u in units]})
    dump(args.out / "selections.json", rows)
    dump(args.out / "metadata.json", metadata)
    dump(args.out / "manifest.json", {"config": config, "config_sha256": digest(args.config.read_bytes()),
        "script_sha256": digest(Path(__file__).read_bytes()), "baseline_selections_sha256": provenance["selections_sha256"],
        "event_sqlite_sha256": provenance["event_sqlite_sha256"], "embedding": provenance["embedding"],
        "packages": {n:version(n) for n in ("numpy", "nltk", "tiktoken", "sentence-transformers", "torch", "transformers")},
        "selections_sha256": digest((args.out / "selections.json").read_bytes()), "questions": len(rows),
        "configurations": len(config["budgets"])*len(config["packing"]), "answer_calls": 0, "judge_calls": 0})
    print(json.dumps({"questions": len(rows), "configurations": len(methods), "out": str(args.out)}))


if __name__ == "__main__":
    main()
