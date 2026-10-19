"""Generate answer-free S0 retrieval JSONL for F's shared QA runner."""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from flat_rag import SentenceTransformerEmbeddings, json_hash, load_questions, load_samples, prepare_retrieval


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(conversations, selection, out, encoder, *, top_k=60, chunk_chars=480,
        cache_dir=None, expected_hashes=None):
    if expected_hashes is not None:
        for path in (conversations, selection):
            name = Path(path).name
            if name not in expected_hashes or sha256(path) != expected_hashes[name]:
                raise ValueError(f"Input does not match A's frozen SHA-256: {name}")
    questions = load_questions(selection)
    samples = load_samples(conversations)
    if Path(out).exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {out}")
    predictions, audits = prepare_retrieval(samples, questions, encoder, top_k=top_k,
                                            chunk_chars=chunk_chars, cache_dir=cache_dir)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    for filename, rows in (("s0.inputs.jsonl", predictions), ("s0.retrieval.jsonl", audits)):
        with (out / filename).open("x", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    manifest = {"task": "S0 raw-conversation retrieval", "status": "retrieval_only_no_answers",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "data_sha256": sha256(conversations), "selection_sha256": sha256(selection),
                "question_set_sha256": json_hash(questions), "questions": len(questions),
                "model": encoder.model, "model_revision": getattr(encoder, "revision", None),
                "embedding_dimensions": getattr(encoder, "dimensions", None),
                "top_k": top_k, "chunk_chars": chunk_chars,
                "sample_ids": sorted({row["sample_id"] for row in questions}),
                "contexts_per_question": [len(row["contexts"]) for row in predictions],
                "answer_generation_calls": 0, "accuracy": None}
    (out / "s0.manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8", newline="\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conversations", type=Path, default=ROOT / "data/locomo/development.conversations.json",
                        help="A's frozen answer-free development conversations")
    parser.add_argument("--selection", type=Path, default=ROOT / "data/locomo/smoke.inputs.json",
                        help="A's frozen selected 5 or 30 question JSON array")
    parser.add_argument("--embedding-config", type=Path, default=ROOT / "configs/locomo-smoke.json",
                        help="A's frozen source and embedding manifest")
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    parser.add_argument("--model-cache-dir", type=Path, default=ROOT / "data/model-cache")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "output/s0-embeddings")
    parser.add_argument("--top-k", type=int, default=60)
    parser.add_argument("--chunk-chars", type=int, default=480)
    args = parser.parse_args()
    frozen = json.loads(args.embedding_config.read_text(encoding="utf-8"))
    encoder = SentenceTransformerEmbeddings(frozen["embedding"], args.model_cache_dir,
                                            local_files_only=True)
    manifest = run(args.conversations, args.selection, args.out, encoder, top_k=args.top_k,
                   chunk_chars=args.chunk_chars, cache_dir=args.cache_dir,
                   expected_hashes=frozen["output_sha256"])
    print(json.dumps({key: manifest[key] for key in ("task", "status", "questions", "top_k",
                                                     "answer_generation_calls")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
