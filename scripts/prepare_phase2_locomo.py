"""Rebuild the Phase 2 LoCoMo manifest and label-isolated local files."""

import argparse
from collections import Counter, deque
import json
from pathlib import Path
import random

from prepare_locomo import ROOT, SEED, clean_conversation, encode, freeze, load_source, sha256


CATEGORIES = (1, 2, 3, 4)
QUOTA = 25


def select_questions(by_id, heldout):
    rng = random.Random(SEED)
    queues = {}
    for category in CATEGORIES:
        pools = []
        for cid in heldout:
            indices = [i for i, qa in enumerate(by_id[cid]["qa"]) if qa["category"] == category]
            rng.shuffle(indices)
            pools.append(indices)
        start = category - 1
        active = deque(i for i in range(start, start + len(heldout)) if pools[i % len(heldout)])
        ordered = deque()
        while active:
            i = active.popleft() % len(heldout)
            ordered.append({"sample_id": heldout[i], "qa_index": pools[i].pop(), "category": category})
            if pools[i]:
                active.append(i)
        queues[category] = ordered

    selected = []
    for _ in range(QUOTA):
        for category in CATEGORIES:
            if queues[category]:
                selected.append(queues[category].popleft())
    # Fill any deficit from the remaining categories in the same fixed rotation.
    target = QUOTA * len(CATEGORIES)
    while len(selected) < target and any(queues.values()):
        for category in CATEGORIES:
            if queues[category] and len(selected) < target:
                selected.append(queues[category].popleft())
    if {q["sample_id"] for q in selected} != set(heldout):
        raise ValueError("Selection misses a held-out conversation")
    return selected


def prepare(rows, development):
    if freeze(rows) != development:
        raise ValueError("Phase 1 manifest does not match the pinned source and selection")
    by_id = {r["sample_id"]: r for r in rows}
    heldout = development["splits"]["heldout"]
    selected = select_questions(by_id, heldout)
    inputs, labels, conversations, stats = [], [], [], {}
    for key in selected:
        qa = by_id[key["sample_id"]]["qa"][key["qa_index"]]
        inputs.append({**key, "question": qa["question"]})
        labels.append({**key, "answer": qa["answer"], "evidence": qa["evidence"]})
    for cid in heldout:
        conversation = clean_conversation(by_id[cid])
        conversations.append({"sample_id": cid, "conversation": conversation})
        sessions = [turns for turns in conversation.values() if isinstance(turns, list)]
        counts = Counter(q["category"] for q in selected if q["sample_id"] == cid)
        stats[cid] = {"sessions": len(sessions), "messages": sum(map(len, sessions)),
                      "questions": sum(counts.values()),
                      "by_category": {str(c): counts[c] for c in CATEGORIES}}
    first = development["questions"][0]
    example = {**first, "question": by_id[first["sample_id"]]["qa"][first["qa_index"]]["question"]}
    files = {"model/development.one.inputs.json": [example], "model/heldout.inputs.json": inputs,
             "model/heldout.conversations.json": conversations, "scoring/heldout.labels.json": labels}
    manifest = {"schema_version": 1, "seed": SEED, "target_per_category": QUOTA,
                "source": development["source"], "phase1_manifest_sha256": sha256(encode(development)),
                "splits": development["splits"], "question_count": len(selected),
                "category_counts": {str(c): sum(q["category"] == c for q in selected) for c in CATEGORIES},
                "conversations": stats, "questions": selected,
                "output_sha256": {name: sha256(encode(data)) for name, data in files.items()}}
    return manifest, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/raw/locomo10.json")
    parser.add_argument("--manifest", type=Path, default=ROOT / "configs/locomo-phase2-heldout.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/locomo-phase2")
    parser.add_argument("--freeze", action="store_true", help="Create the manifest once")
    parser.add_argument("--with-labels", action="store_true", help="Also materialize E's scoring file")
    args = parser.parse_args()
    phase1 = json.loads((ROOT / "configs/locomo-smoke.json").read_text(encoding="utf-8"))
    manifest, files = prepare(load_source(args.source), phase1)
    frozen = encode(manifest)
    if args.freeze:
        with args.manifest.open("xb") as stream:
            stream.write(frozen)
    elif json.loads(args.manifest.read_text(encoding="utf-8")) != manifest:
        raise ValueError("Phase 2 manifest differs from the reproducible selection or hashes")
    outputs = {args.output_dir / name: encode(value) for name, value in files.items()
               if name.startswith("model/") or args.with_labels}
    for path, data in outputs.items():
        if path.exists() and path.read_bytes() != data:
            raise FileExistsError(f"Frozen output differs: {path}")
    for path, data in outputs.items():
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)
    print(json.dumps({"questions": manifest["question_count"], "conversations": manifest["conversations"],
                      "written_or_verified": [str(path) for path in outputs]}, indent=2))


if __name__ == "__main__":
    main()
