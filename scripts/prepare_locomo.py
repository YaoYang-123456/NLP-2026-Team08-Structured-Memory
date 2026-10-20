"""Prepare the team's frozen LoCoMo subset without exposing scoring labels."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "cbfbc1dba6bc53d00625212a0f22d55ffee7c1fc"
SOURCE_SHA256 = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
SOURCE_URL = f"https://raw.githubusercontent.com/snap-research/locomo/{SOURCE_REVISION}/data/locomo10.json"
LIGHTMEM_REVISION = "8449d574df6bae1bdf3314a1564da65e2f37e046"
SEED = 42


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encode(value))


def load_source(path):
    data = path.read_bytes()
    if sha256(data) != SOURCE_SHA256:
        raise ValueError("Source SHA-256 differs from the pinned official file")
    rows = json.loads(data)
    audit_source(rows)
    return rows


def clean_conversation(row):
    """Keep only original conversation fields consumed by B/C (never summaries)."""
    source = row["conversation"]
    result = {key: source[key] for key in ("speaker_a", "speaker_b")}
    keys = sorted((k for k in source if re.fullmatch(r"session_\d+", k)),
                  key=lambda k: int(k.split("_")[1]))
    if not keys:
        raise ValueError(f"No sessions: {row['sample_id']}")
    seen = set()
    for key in keys:
        timestamp = source[key + "_date_time"]
        if not isinstance(timestamp, str) or not timestamp.strip() or not source[key]:
            raise ValueError(f"Empty session or timestamp: {row['sample_id']}/{key}")
        result[key + "_date_time"] = timestamp
        messages = []
        for turn in source[key]:
            if (not isinstance(turn.get("dia_id"), str) or turn["dia_id"] in seen
                    or turn.get("speaker") not in (source["speaker_a"], source["speaker_b"])
                    or not isinstance(turn.get("text"), str) or not turn["text"].strip()):
                raise ValueError(f"Invalid/duplicate turn: {row['sample_id']}/{key}")
            seen.add(turn["dia_id"])
            message = {k: turn[k] for k in ("dia_id", "speaker", "text")}
            if turn.get("blip_caption"):
                if not isinstance(turn["blip_caption"], str):
                    raise ValueError("Invalid image description")
                message["blip_caption"] = turn["blip_caption"]
            messages.append(message)
        result[key] = messages
    return result


def audit_source(rows):
    if not isinstance(rows, list) or len(rows) != 10:
        raise ValueError("Expected ten LoCoMo conversations")
    ids = [r["sample_id"] for r in rows]
    if any(not isinstance(i, str) or not re.fullmatch(r"conv-\d+", i) for i in ids) or len(set(ids)) != 10:
        raise ValueError("Invalid/duplicate conversation IDs")
    for row in rows:
        clean_conversation(row)
        for q in row["qa"]:
            if type(q["category"]) is not int or q["category"] not in range(1, 6):
                raise ValueError("Invalid category")
            if not isinstance(q["question"], str) or not q["question"].strip():
                raise ValueError("Empty question")
            if q["category"] != 5 and ("answer" not in q or q["answer"] is None or q["answer"] == ""):
                raise ValueError("Missing scoring answer")
            if not isinstance(q["evidence"], list):
                raise ValueError("Invalid evidence list")


def make_selection(rows):
    ids = sorted(r["sample_id"] for r in rows)
    rng = random.Random(SEED)
    rng.shuffle(ids)
    dev, heldout = ids[:3], ids[3:]
    by_id = {r["sample_id"]: r for r in rows}
    pools = {}
    for category in (1, 2, 3, 4):
        for cid in dev:
            pool = [i for i, q in enumerate(by_id[cid]["qa"]) if q["category"] == category]
            rng.shuffle(pool)
            pools[category, cid] = pool
    selected = []
    for i in range(30):
        category = i % 4 + 1
        cid = dev[(i // 4 + i % 4) % 3]
        if not pools[category, cid]:
            raise ValueError(f"Insufficient questions: {cid}/category {category}")
        qi = pools[category, cid].pop()
        selected.append({"sample_id": cid, "qa_index": qi, "category": category})
    return {"development": dev, "heldout": heldout}, selected


def build_payloads(rows, splits, selected):
    by_id = {r["sample_id"]: r for r in rows}
    if (len(splits["development"]) != 3 or len(splits["heldout"]) != 7
            or set(splits["development"]) & set(splits["heldout"])
            or set(splits["development"] + splits["heldout"]) != set(by_id)):
        raise ValueError("Invalid 3/7 conversation split")
    if len(selected) != 30 or len({(q["sample_id"], q["qa_index"]) for q in selected}) != 30:
        raise ValueError("Expected thirty unique questions")
    inputs, labels = [], []
    for item in selected:
        cid, qi = item["sample_id"], item["qa_index"]
        if cid not in splits["development"] or type(qi) is not int or not 0 <= qi < len(by_id[cid]["qa"]):
            raise ValueError("Question outside development split")
        q = by_id[cid]["qa"][qi]
        if item["category"] != q["category"] or q["category"] == 5:
            raise ValueError("Question ID/category mismatch")
        inputs.append({**item, "question": q["question"]})
        labels.append({**item, "answer": q["answer"], "evidence": q["evidence"]})
    if set(Counter(q["category"] for q in inputs)) != {1, 2, 3, 4}:
        raise ValueError("Four-category coverage missing")
    conversations = [{"sample_id": cid, "conversation": clean_conversation(by_id[cid])}
                     for cid in splits["development"]]
    return {"development.conversations.json": conversations,
            "development.inputs.json": inputs, "smoke.inputs.json": inputs[:5],
            "development.labels.json": labels, "smoke.labels.json": labels[:5]}


def freeze(rows):
    splits, selected = make_selection(rows)
    payloads = build_payloads(rows, splits, selected)
    return {"schema_version": 1, "seed": SEED,
            "source": {"repository": "snap-research/locomo", "revision": SOURCE_REVISION,
                       "path": "data/locomo10.json", "url": SOURCE_URL,
                       "bytes": 2805274, "sha256": SOURCE_SHA256,
                       "git_blob_sha1": "d95b872480b413d935821fdc3c84f8a8f5f29e73"},
            "lightmem": {"repository": "zjunlp/LightMem", "revision": LIGHTMEM_REVISION},
            "embedding": {"model_id": "sentence-transformers/all-MiniLM-L6-v2",
                          "revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
                          "dimensions": 384, "normalize_embeddings": True,
                          "max_seq_length": 256, "device_for_check": "cpu"},
            "selection": "sorted conversation IDs; Random(42) shuffle; first 3 development; category/conversation round-robin from seeded shuffled pools; original zero-based qa_index",
            "splits": splits, "questions": selected,
            "smoke_question_keys": [[q["sample_id"], q["qa_index"]] for q in selected[:5]],
            "output_sha256": {name: sha256(encode(value)) for name, value in payloads.items()}}


def materialize(source, config, dest):
    rows = load_source(source)
    expected = freeze(rows)
    if config != expected:
        raise ValueError("Config differs from frozen selection/version/hash contract")
    payloads = build_payloads(rows, config["splits"], config["questions"])
    # Check all existing outputs before writing, so a changed run cannot overwrite the freeze.
    for name, value in payloads.items():
        target = dest / name
        if target.exists() and target.read_bytes() != encode(value):
            raise FileExistsError(f"Frozen output differs; use a new directory: {target}")
    for name, value in payloads.items():
        save(dest / name, value)
    return {"source_sha256": SOURCE_SHA256,
            "development_conversations": config["splits"]["development"],
            "heldout_conversations": config["splits"]["heldout"],
            "questions": 30, "smoke_questions": 5,
            "category_counts": dict(Counter(q["category"] for q in config["questions"])),
            "conversation_overlap": 0, "output_sha256": config["output_sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/raw/locomo10.json")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/locomo-smoke.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/locomo")
    parser.add_argument("--download", action="store_true", help="Download only if the pinned source is absent")
    parser.add_argument("--freeze", action="store_true", help="Create initial config once; never replace it")
    args = parser.parse_args()
    if args.download and not args.source.exists():
        with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
            data = response.read()
        if sha256(data) != SOURCE_SHA256:
            raise ValueError("Downloaded SHA-256 mismatch")
        args.source.parent.mkdir(parents=True, exist_ok=True)
        args.source.write_bytes(data)
    if args.freeze:
        config = freeze(load_source(args.source))
        args.config.parent.mkdir(parents=True, exist_ok=True)
        with args.config.open("xb") as stream:
            stream.write(encode(config))
    config = json.loads(args.config.read_text(encoding="utf-8"))
    print(json.dumps(materialize(args.source, config, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
