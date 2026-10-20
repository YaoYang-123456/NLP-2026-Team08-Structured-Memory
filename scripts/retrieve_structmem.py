"""Retrieve from completed native StructMem exports; never call an answering API."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from structmem_retrieve import (EMBEDDING, UPSTREAM_REVISION, file_hash, load_memory_index,
                               load_questions, local_embedder, prepare_inputs, read_json)


def run(inputs, frozen_config, memory_index, cache, out):
    questions = load_questions(inputs)
    config = read_json(frozen_config)
    if config["lightmem"]["revision"] != UPSTREAM_REVISION:
        raise ValueError("A LightMem version changed")
    if any(config["embedding"][key] != value for key, value in EMBEDDING.items()):
        raise ValueError("A embedding contract changed")
    expected = {(q["sample_id"], q["qa_index"], q["category"]) for q in config["questions"]}
    keys = [(q["sample_id"], q["qa_index"]) for q in questions]
    if keys == [tuple(key) for key in config["smoke_question_keys"]]:
        name = "smoke.inputs.json"
    elif keys == [(q["sample_id"], q["qa_index"]) for q in config["questions"]]:
        name = "development.inputs.json"
    else:
        raise ValueError("Input is neither the ordered frozen 5 nor 30 question set")
    if file_hash(inputs) != config["output_sha256"][name]:
        raise ValueError("Question text/identity differs from the frozen A file")
    for q in questions:
        if ((q["sample_id"], q["qa_index"], q["category"]) not in expected or
                q["sample_id"] not in config["splits"]["development"]):
            raise ValueError("Question outside the development freeze")
    if read_json(memory_index).get("source_conversations_sha256") != config["output_sha256"]["development.conversations.json"]:
        raise ValueError("Memory source differs from A's frozen development conversations")
    memories, hashes = load_memory_index(memory_index, dict.fromkeys(q["sample_id"] for q in questions))
    out = Path(out)
    if out.exists():
        raise FileExistsError(out)
    embed = local_embedder(cache)
    rows, traces = prepare_inputs(questions, memories, embed)
    out.mkdir(parents=True, exist_ok=False)
    with (out / "retrieval.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
    metadata = {"method": "S2", "status": "retrieval_only", "synthetic": False,
                "created_utc": datetime.now(timezone.utc).isoformat(), "questions": len(rows),
                "inputs_sha256": file_hash(inputs), "frozen_config_sha256": file_hash(frozen_config),
                "memory_index_sha256": file_hash(memory_index), "memory_sha256": hashes,
                "upstream_revision": UPSTREAM_REVISION, "embedding": EMBEDDING,
                "event_limit": 60, "summary_limit": 5, "answer_api_calls": 0,
                "code_sha256": {p.name: file_hash(p) for p in
                                (Path(__file__), ROOT / "src/structmem_retrieve.py")}}
    for name, value in (("run.json", metadata), ("provenance.json", traces)):
        with (out / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--frozen-config", type=Path, required=True)
    parser.add_argument("--memory-index", type=Path, required=True)
    parser.add_argument("--model-cache", type=Path, default=ROOT / "data/model-cache")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.frozen_config, args.memory_index, args.model_cache, args.out),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
