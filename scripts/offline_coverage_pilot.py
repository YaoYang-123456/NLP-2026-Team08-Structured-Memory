"""Frozen, local-only retrieval pilot. Full traces/annotations belong in output/.

Selection reads label-free questions, native event vectors and the fixed five
synthesis texts. Evaluation is a separate command and consumes reviewed support
units only after selections have been written. No answer or judge API is used.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from audit_development_memory import PointReader, archive_rows, digest, dump, read
from flat_rag import SentenceTransformerEmbeddings
from structmem_retrieve import load_questions, memory_text, validate_vector

STOP = set("a an the is are was were be been being do does did has have had can could would should will may might to of in on at by for from with and or but as it its his her their them he she they you your i me my we our what which who when where why how both any kind around currently recently recent get got go went use instead together".split())
MONTHS = "january february march april may june july august september october november december".split()
TEMPORAL = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|yesterday|tomorrow|last|next|week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday|" + "|".join(MONTHS) + r")\b", re.I)


def tokenizer(cache):
    # Refuse a download during a pilot run; the pinned counter asset is prepared once.
    url = "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"
    if not (cache / hashlib.sha1(url.encode()).hexdigest()).is_file():
        raise ValueError("Prepare the cl100k_base asset in --tokenizer-cache before running offline")
    os.environ["TIKTOKEN_CACHE_DIR"] = str(cache)
    import tiktoken
    return tiktoken.get_encoding("cl100k_base")


def words(text, stemmer):
    return [stemmer.stem(w) for w in re.findall(r"[a-z]+|\d+", text.lower()) if w not in STOP]


def facets(question, names, stemmer, weights):
    result = [("keyword", w, weights["keyword"]) for w in sorted(set(words(question, stemmer)))]
    for name in sorted(names):
        if re.search(r"\b" + re.escape(name) + r"\b", question, re.I):
            result.append(("entity", name.lower(), weights["entity"]))
    # An explicit date is a soft *recording-date* match, never an asserted event date.
    lower = question.lower()
    for i, month in enumerate(MONTHS, 1):
        full = re.search(r"\b(\d{1,2})\s+" + month + r"\s+(\d{4})\b", lower)
        partial = re.search(r"\b" + month + r"\s+(\d{4})\b", lower)
        if full:
            value = f"{int(full[2]):04d}-{i:02d}-{int(full[1]):02d}"
            result.append(("recording_date", value, weights["explicit_date"]))
        elif partial:
            result.append(("recording_date", f"{int(partial[1]):04d}-{i:02d}", weights["explicit_date"]))
    if re.search(r"\bwhen\b", lower):
        result.append(("temporal_attribute", "temporal", weights["temporal_attribute"]))
    return result


def facet_matches(event, features, stemmer):
    body = event["payload"]["memory"]
    terms = set(words(body, stemmer))
    matched = []
    for kind, value, _ in features:
        if kind == "keyword":
            matched.append(value in terms)
        elif kind == "entity":
            matched.append(bool(re.search(r"\b" + re.escape(value) + r"\b", body, re.I)))
        elif kind == "recording_date":
            matched.append(event["payload"]["time_stamp"].startswith(value))
        else:
            matched.append(bool(TEMPORAL.search(body)))
    return matched


def bm25(documents, query, config):
    counts = [Counter(d) for d in documents]
    df = Counter(w for d in documents for w in set(d))
    average = sum(map(len, documents)) / len(documents)
    scores = []
    for terms, doc in zip(counts, documents):
        score = 0.0
        for word in set(query):
            frequency = terms[word]
            idf = math.log(1 + (len(documents) - df[word] + 0.5) / (df[word] + 0.5))
            denominator = frequency + config["bm25_k1"] * (1 - config["bm25_b"] + config["bm25_b"] * len(doc) / average)
            score += idf * frequency * (config["bm25_k1"] + 1) / denominator
        scores.append(score)
    return scores


def select(args):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import numpy as np
    from nltk.stem import PorterStemmer
    from importlib.metadata import version
    config = read(args.config)
    frozen = read(ROOT / "configs/locomo-smoke.json")
    questions = load_questions(args.questions)
    if [(r["sample_id"], r["qa_index"]) for r in questions] != [(r["sample_id"], r["qa_index"]) for r in frozen["questions"]]:
        raise ValueError("Expected the ordered frozen development30 questions")
    archive = ROOT / "reports/artifacts/s2-predictions-for-E-20261020.zip"
    expected = read(ROOT / "reports/phase2-memory-audit-20261103.json")["inputs"]["prediction_archives"][archive.name]
    if digest(archive.read_bytes()) != expected:
        raise ValueError("S2 archive hash mismatch")
    # Drop predictions, categories, scores and event lists before constructing inputs.
    summaries = {(r["sample_id"], r["qa_index"]): [c for c in r["contexts"] if c["kind"] == "synthesis"]
                 for r in archive_rows(archive, "predictions30.jsonl")}
    enc = tokenizer(args.tokenizer_cache)
    encoder = SentenceTransformerEmbeddings(frozen["embedding"], args.model_cache)
    vectors = encoder.encode([r["question"] for r in questions])
    args.out.mkdir(parents=True, exist_ok=False)
    dump(args.out / "query-vectors.json", {"embedding": frozen["embedding"], "vectors": vectors})
    stemmer = PorterStemmer()
    events_by_sample, hashes = {}, {}
    for sid in frozen["splits"]["development"]:
        path = args.events / f"{sid}.sqlite"
        hashes[path.name] = digest(path.read_bytes())
        conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
        events = []
        for blob, in conn.execute("SELECT point FROM points"):
            point = PointReader(io.BytesIO(blob)).load().value
            validate_vector(point["vector"])
            if point["payload"]["source_sample_id"] != sid:
                raise ValueError("Cross-conversation event")
            point["id"] = f"{sid}/event/{point['id']}"
            point["text"] = memory_text(point, "event")
            events.append(point)
        conn.close()
        events_by_sample[sid] = sorted(events, key=lambda p: p["id"])
    if sum(map(len, events_by_sample.values())) != 3712:
        raise ValueError("Incomplete development event bank")
    rows = []
    for row, query in zip(questions, vectors):
        started = time.perf_counter()
        sid, qi = row["sample_id"], row["qa_index"]
        events = events_by_sample[sid]
        matrix = np.asarray([p["vector"] for p in events], dtype=np.float64)
        matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
        dense = matrix @ (np.asarray(query) / np.linalg.norm(query))
        docs = [words(p["text"], stemmer) for p in events]
        lexical = bm25(docs, words(row["question"], stemmer), config)
        dense_order = sorted(range(len(events)), key=lambda i: (-float(dense[i]), events[i]["id"]))[:config["dense_top_k"]]
        lex_order = [i for i in sorted(range(len(events)), key=lambda i: (-lexical[i], events[i]["id"])) if lexical[i] > 0][:config["lexical_top_k"]]
        ranks = [{i: r + 1 for r, i in enumerate(order)} for order in (dense_order, lex_order)]
        rrf = {i: sum(1 / (config["rrf_k"] + rank[i]) for rank in ranks if i in rank) for i in set(dense_order) | set(lex_order)}
        candidates = sorted(rrf, key=lambda i: (-rrf[i], events[i]["id"]))
        relevance = {i: rrf[i] / max(rrf.values()) for i in candidates}
        sim = np.clip(matrix[candidates] @ matrix[candidates].T, 0, 1)
        position = {i: j for j, i in enumerate(candidates)}
        features = facets(row["question"], {p["payload"]["speaker_name"] for p in events}, stemmer, config["facet_weights"])
        matches = {i: facet_matches(events[i], features, stemmer) for i in candidates}
        groups = {i: events[i]["payload"]["source_key"] for i in candidates}
        group_relevance = defaultdict(float)
        for i in candidates:
            group_relevance[groups[i]] = max(group_relevance[groups[i]], relevance[i])
        fixed = summaries[sid, qi]
        if len(fixed) != 5:
            raise ValueError("Expected five fixed synthesis texts")
        blocks = [f"[S{j+1:03d}]\n{c['text']}\n\n" for j, c in enumerate(fixed)]
        fixed_tokens = sum(len(enc.encode(b)) for b in blocks)
        if fixed_tokens >= config["budget"]:
            raise ValueError("Fixed synthesis consumes the full budget")
        # Stable evidence IDs come from common candidate order, not selection order.
        event_blocks = {i: f"[E{position[i]+1:03d}]\n{events[i]['text']}\n\n" for i in candidates}
        costs = {i: len(enc.encode(event_blocks[i])) for i in candidates}
        selections = {}
        for method in ("hybrid", "mmr", "complementary"):
            chosen, steps, rejected = [], [], []
            remaining, used = list(candidates), fixed_tokens
            counts, source_counts = Counter(), Counter()
            while remaining:
                utility = {}
                components = {}
                for i in remaining:
                    redundancy = max((float(sim[position[i], position[j]]) for j in chosen), default=0.0)
                    gain = sum(weight / (1 + counts[n]) for n, (_, _, weight) in enumerate(features) if matches[i][n]) / sum(f[2] for f in features)
                    group_gain = group_relevance[groups[i]] / (1 + source_counts[groups[i]])
                    components[i] = {"relevance": relevance[i], "facet_gain": gain, "source_gain": group_gain, "redundancy": redundancy}
                    weights = config[method] if method != "hybrid" else {"relevance": 1.0}
                    utility[i] = sum((-1 if key == "redundancy" else 1) * value * components[i][key] for key, value in weights.items())
                i = min(remaining, key=lambda j: (-utility[j], events[j]["id"]))
                remaining.remove(i)
                if used + costs[i] > config["budget"]:
                    rejected.append(events[i]["id"])
                    continue
                chosen.append(i)
                used += costs[i]
                source_counts[groups[i]] += 1
                counts.update(n for n in range(len(features)) if matches[i][n])
                steps.append({"id": events[i]["id"], "proxy_tokens": costs[i], "utility": utility[i], **components[i]})
            rendered = "".join(blocks + [event_blocks[i] for i in chosen])
            if len(enc.encode(rendered)) > config["budget"]:
                raise AssertionError("Rendered context exceeds the proxy budget")
            selections[method] = {
                "event_ids": [events[i]["id"] for i in chosen], "steps": steps,
                "synthesis_ids": [c["source_ids"][0] for c in fixed],
                "budget_skipped_ids": rejected, "proxy_tokens": used,
                "rendered_proxy_tokens": len(enc.encode(rendered)), "utf8_bytes": len(rendered.encode()),
                "distinct_sources": len(source_counts),
                "duplicate_source_excess": len(chosen) - len(source_counts),
                "high_similarity_pairs": sum(float(sim[position[i], position[j]]) >= 0.85 for k, i in enumerate(chosen) for j in chosen[:k]),
                "contexts": fixed + [{"source_ids": [events[i]["id"], groups[i]], "kind": "event", "text": events[i]["text"]} for i in chosen],
                "rendered": rendered,
            }
        rows.append({"sample_id": sid, "qa_index": qi, "question": row["question"], "facets": features,
                     "candidate_ids": [events[i]["id"] for i in candidates],
                     "candidate_scores": [{"id": events[i]["id"], "dense_rank": ranks[0].get(i), "lexical_rank": ranks[1].get(i), "rrf": rrf[i]} for i in candidates],
                     "fixed_synthesis_proxy_tokens": fixed_tokens, "methods": selections,
                     "selection_seconds": time.perf_counter() - started})
    dump(args.out / "selections.json", rows)
    dump(args.out / "manifest.json", {
        "config": config, "config_sha256": digest(args.config.read_bytes()),
        "script_sha256": digest(Path(__file__).read_bytes()), "questions_sha256": digest(args.questions.read_bytes()),
        "event_sqlite_sha256": hashes, "s2_archive_sha256": expected, "embedding": frozen["embedding"],
        "packages": {n: version(n) for n in ("numpy", "nltk", "tiktoken", "sentence-transformers", "torch", "transformers")},
        "selections_sha256": digest((args.out / "selections.json").read_bytes()),
        "event_population": sum(map(len, events_by_sample.values())), "questions": len(rows),
        "answer_calls": 0, "judge_calls": 0,
    })
    print(json.dumps({"questions": len(rows), "output": str(args.out), "answer_calls": 0}))


def evaluate(args):
    rows, annotations = read(args.selections), read(args.annotations)
    annotations = {(r["sample_id"], r["qa_index"]): r for r in annotations}
    if set(annotations) != {(r["sample_id"], r["qa_index"]) for r in rows}:
        raise ValueError("Support annotations must cover exactly all 30 questions")
    results = []
    for row in rows:
        annotation = annotations[row["sample_id"], row["qa_index"]]
        per_method = {}
        for method, selected in row["methods"].items():
            context = {c["source_ids"][0]: c["text"] for c in selected["contexts"]}
            covered, witnesses = [], {}
            for unit in annotation["units"]:
                # Each alternative is a conjunction of audited text passages. IDs alone
                # cannot pass; every quoted substring is checked against actual input.
                valid = [alt for alt in unit["alternatives"] if all(
                    item["id"] in context and item["quote"] in context[item["id"]] for item in alt)]
                if valid:
                    covered.append(unit["name"])
                    witnesses[unit["name"]] = valid
            per_method[method] = {"covered": covered, "total": len(annotation["units"]),
                                  "complete": len(covered) == len(annotation["units"]), "witnesses": witnesses}
        results.append({"sample_id": row["sample_id"], "qa_index": row["qa_index"],
                        "scope": annotation["scope"], "methods": per_method})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        raise FileExistsError(args.out)
    dump(args.out, {"selections_sha256": digest(args.selections.read_bytes()),
                    "annotations_sha256": digest(args.annotations.read_bytes()), "questions": results})
    print(json.dumps({"questions": len(results), "output": str(args.out)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("select")
    run.add_argument("--config", type=Path, default=ROOT / "configs/phase2-coverage-pilot.json")
    for name in ("questions", "events", "model-cache", "tokenizer-cache", "out"):
        run.add_argument("--" + name, type=Path, required=True)
    review = sub.add_parser("evaluate")
    for name in ("selections", "annotations", "out"):
        review.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    (select if args.command == "select" else evaluate)(args)


if __name__ == "__main__":
    main()
