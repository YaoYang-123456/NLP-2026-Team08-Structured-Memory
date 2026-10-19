"""LoCoMo raw-turn vector retrieval for S0; no answer labels or answer model."""

import hashlib
import json
import math
import re
from pathlib import Path


SESSION = re.compile(r"session_(\d+)$")
QUESTION_KEYS = {"sample_id", "qa_index", "question", "category"}


def json_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def load_questions(path):
    """Read A's selected original QA IDs, without gold answers or evidence."""
    path = Path(path)
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("Frozen A question file must be a JSON array")
        numbered = enumerate(data, 1)
    elif path.suffix == ".jsonl":
        lines = path.read_text(encoding="utf-8").splitlines()
        if any(not line.strip() for line in lines):
            raise ValueError("Blank line in question JSONL")
        numbered = ((i, json.loads(line)) for i, line in enumerate(lines, 1))
    else:
        raise ValueError("Question file must be .json (A's format) or .jsonl")
    rows, seen = [], set()
    for lineno, row in numbered:
        if not isinstance(row, dict) or set(row) != QUESTION_KEYS:
            raise ValueError(f"Selection line {lineno}: expected only {sorted(QUESTION_KEYS)}")
        sid, idx, question, category = (row[key] for key in
                                        ("sample_id", "qa_index", "question", "category"))
        if (not isinstance(sid, str) or not sid.strip() or type(idx) is not int or idx < 0 or
                not isinstance(question, str) or not question.strip() or
                type(category) is not int or category not in (1, 2, 3, 4)):
            raise ValueError(f"Selection line {lineno}: invalid QA identity or category")
        if (sid, idx) in seen:
            raise ValueError(f"Selection line {lineno}: repeated QA key")
        seen.add((sid, idx))
        rows.append(row)
    if not rows:
        raise ValueError("Empty selected question list")
    return rows

def load_samples(path):
    """Load official LoCoMo; caller only accesses conversation, never qa labels."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Expected official LoCoMo JSON list")
    samples = {}
    for sample in raw:
        if not isinstance(sample, dict) or not isinstance(sample.get("sample_id"), str):
            raise ValueError("Invalid LoCoMo sample identifier")
        sid = sample["sample_id"]
        if sid in samples or not isinstance(sample.get("conversation"), dict):
            raise ValueError("Duplicate ID or missing conversation: " + sid)
        samples[sid] = sample["conversation"]
    return samples


def split_text(text, limit):
    """Split long turns on spaces where possible, without changing characters."""
    if not isinstance(text, str) or not text.strip():
        return []
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        edge = text.rfind(" ", 0, limit + 1)
        cut = edge + 1 if edge >= limit // 2 else limit
        parts.append(text[:cut])
        text = text[cut:]
    return parts


def raw_chunks(sample_id, conversation, chunk_chars=480):
    if type(chunk_chars) is not int or chunk_chars < 80:
        raise ValueError("chunk_chars must be an integer >= 80")
    sessions = sorted(((int(m.group(1)), key) for key in conversation
                       if (m := SESSION.fullmatch(key))), key=lambda pair: pair[0])
    if not sessions:
        raise ValueError(f"No sessions in conversation {sample_id}")
    chunks, sources = [], set()
    for _, key in sessions:
        turns = conversation[key]
        date = conversation.get(key + "_date_time")
        if not isinstance(turns, list) or not isinstance(date, str) or not date.strip():
            raise ValueError(f"Invalid session or timestamp: {sample_id}/{key}")
        for i, turn in enumerate(turns):
            if not isinstance(turn, dict):
                raise ValueError(f"Malformed turn: {sample_id}/{key}/{i}")
            dia_id = turn.get("dia_id")
            speaker = turn.get("speaker")
            body = turn.get("text", turn.get("clean_text"))
            if not isinstance(dia_id, str) or not dia_id.strip() or not isinstance(speaker, str) or not speaker.strip():
                raise ValueError(f"Missing speaker or original dialog ID: {sample_id}/{key}/{i}")
            if not isinstance(body, str) or not body.strip():
                raise ValueError(f"Missing turn text: {sample_id}/{key}/{dia_id}")
            if dia_id in sources:
                raise ValueError(f"Duplicate original dialog ID: {sample_id}/{dia_id}")
            sources.add(dia_id)
            caption = turn.get("blip_caption")
            if isinstance(caption, str) and caption.strip():
                body += "\n(image description: " + caption + ")"
            for j, fragment in enumerate(split_text(body, chunk_chars)):
                chunks.append({"source_ids": [f"{sample_id}:{key}:{dia_id}:{j}"],
                               "kind": "raw", "text": f"({date}) {speaker}: {fragment}"})
    if not chunks:
        raise ValueError(f"No turns in conversation {sample_id}")
    return chunks


def normalized(vector):
    if not isinstance(vector, list) or not vector or any(type(x) not in (float, int) or not math.isfinite(x)
                                                         for x in vector):
        raise ValueError("Embedding must be a nonempty finite numeric vector")
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        raise ValueError("Zero embedding cannot be ranked")
    return [x / norm for x in vector]


class SentenceTransformerEmbeddings:
    """Use A's exact pinned local MiniLM model; never silently change or download it."""

    def __init__(self, spec, cache_dir, local_files_only=True):
        from sentence_transformers import SentenceTransformer

        required = {"model_id", "revision", "dimensions", "normalize_embeddings",
                    "max_seq_length", "device_for_check"}
        if (not isinstance(spec, dict) or set(spec) != required or
                not isinstance(spec["model_id"], str) or not spec["model_id"].strip() or
                not isinstance(spec["revision"], str) or not spec["revision"].strip() or
                type(spec["dimensions"]) is not int or spec["dimensions"] <= 0 or
                spec["normalize_embeddings"] is not True or
                type(spec["max_seq_length"]) is not int or spec["max_seq_length"] <= 0 or
                spec["device_for_check"] != "cpu"):
            raise ValueError("Embedding specification must match A's fixed normalized CPU model")
        self.model = spec["model_id"]
        self.revision = spec["revision"]
        self.dimensions = spec["dimensions"]
        self.max_seq_length = spec["max_seq_length"]
        self.device = spec["device_for_check"]
        self.encoder = SentenceTransformer(
            self.model, revision=self.revision, device=self.device,
            cache_folder=str(cache_dir), local_files_only=local_files_only,
            trust_remote_code=False)
        if (self.encoder.get_sentence_embedding_dimension() != self.dimensions or
                self.encoder.max_seq_length != self.max_seq_length):
            raise ValueError("Loaded embeddings differ from A's pinned dimensions/sequence length")

    def encode(self, texts):
        if not texts:
            return []
        # The encoder would silently truncate at 256 tokens; reject instead.
        token_ids = self.encoder.tokenizer(texts, padding=False, truncation=False)["input_ids"]
        if any(len(ids) > self.max_seq_length for ids in token_ids):
            raise ValueError("Embedding text exceeds A's 256-token limit; reduce --chunk-chars")
        vectors = self.encoder.encode(texts, batch_size=32, normalize_embeddings=True,
                                      convert_to_numpy=True, show_progress_bar=False)
        rows = vectors.tolist()
        if len(rows) != len(texts) or any(len(v) != self.dimensions for v in rows):
            raise ValueError("Embedding count/dimensions mismatch")
        return rows

def embed_chunks(chunks, encoder, cache_dir=None):
    """Cache by embedding model and exact source text; never cache answer labels."""
    texts = [chunk["text"] for chunk in chunks]
    model = getattr(encoder, "model", type(encoder).__name__)
    identity = {"model": model, "revision": getattr(encoder, "revision", None),
                "max_seq_length": getattr(encoder, "max_seq_length", None),
                "dimensions": getattr(encoder, "dimensions", None)}
    key = json_hash({"embedding": identity, "texts": texts})
    target = Path(cache_dir) / (key + ".json") if cache_dir else None
    if target is not None and target.is_file():
        saved = json.loads(target.read_text(encoding="utf-8"))
        if saved.get("key") != key or saved.get("embedding") != identity:
            raise ValueError("Embedding cache metadata mismatch")
        vectors = saved["vectors"]
    else:
        vectors = encoder.encode(texts)
        if len(vectors) != len(texts):
            raise ValueError("Embedding count mismatch")
        vectors = [normalized(vector) for vector in vectors]
        if target is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({"key": key, "embedding": identity, "vectors": vectors}) + "\n",
                              encoding="utf-8", newline="\n")
    if len(vectors) != len(texts):
        raise ValueError("Cached embedding count mismatch")
    vectors = [normalized(vector) for vector in vectors]
    if len({len(v) for v in vectors}) != 1 or (getattr(encoder, "dimensions", None) is not None
                                                  and len(vectors[0]) != encoder.dimensions):
        raise ValueError("Inconsistent embedding dimensions")
    return vectors


def rank_chunks(chunks, vectors, query_vector, top_k=60):
    if type(top_k) is not int or top_k < 1 or len(chunks) != len(vectors):
        raise ValueError("Invalid retrieval inputs/top_k")
    query = normalized(query_vector)
    if not vectors or any(len(v) != len(query) for v in vectors):
        raise ValueError("Query/corpus embedding dimensions mismatch")
    scores = [sum(a * b for a, b in zip(query, vec)) for vec in vectors]
    order = sorted(range(len(chunks)), key=lambda i: (-scores[i], i))[:top_k]
    return [{"rank": n + 1, "score": scores[i], "source_ids": chunks[i]["source_ids"]}
            for n, i in enumerate(order)], [chunks[i] for i in order]


def prepare_retrieval(samples, questions, encoder, top_k=60, chunk_chars=480, cache_dir=None):
    """Group by conversation, embedding raw turns once; emit exactly F's five fields."""
    missing = {r["sample_id"] for r in questions} - set(samples)
    if missing:
        raise ValueError("Missing selected LoCoMo sample(s): " + ", ".join(sorted(missing)))
    by_sample = {}
    for row in questions:
        by_sample.setdefault(row["sample_id"], []).append(row)
    output, audits = {}, {}
    for sid, selected in by_sample.items():
        chunks = raw_chunks(sid, samples[sid], chunk_chars)
        vectors = embed_chunks(chunks, encoder, cache_dir)
        queries = encoder.encode([row["question"] for row in selected])
        if len(queries) != len(selected):
            raise ValueError("Question embedding count mismatch")
        for row, query in zip(selected, queries):
            diagnostics, contexts = rank_chunks(chunks, vectors, query, top_k)
            identity = (sid, row["qa_index"])
            output[identity] = {**row, "contexts": contexts}
            audits[identity] = {"sample_id": sid, "qa_index": row["qa_index"],
                                "corpus_chunks": len(chunks), "ranking": diagnostics}
    return [output[r["sample_id"], r["qa_index"]] for r in questions], [
        audits[r["sample_id"], r["qa_index"]] for r in questions]
