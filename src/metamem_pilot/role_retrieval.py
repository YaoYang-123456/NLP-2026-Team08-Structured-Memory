"""BM25 with equal user/non-user fact budgets; no labels or evidence annotations."""
from .data import retrieve


def retrieve_balanced(row, top_k=20, max_chars=12000, chunk_words=180):
    if top_k < 2 or max_chars < 2:
        raise ValueError("Both role groups need a positive budget")
    # Reuse exactly the baseline tokenizer, scoring, tie order and chunking.
    turns = [(sid, ti, turn) for sid, session in zip(row["haystack_session_ids"], row["haystack_sessions"])
             for ti, turn in enumerate(session)]
    count = sum((len(t["content"].split()) + chunk_words - 1) // chunk_words for _, _, t in turns)
    if not count:
        raise ValueError("Empty history")
    roles = {(sid, ti): t["role"] for sid, ti, t in turns}
    ranked = retrieve(row, top_k=count, max_chars=10**12, chunk_words=chunk_words)
    used, blocks, selected = [0, 0], [0, 0], []
    char_caps = [max_chars // 2, max_chars - max_chars // 2]
    block_caps = [top_k // 2, top_k - top_k // 2]
    for fact in ranked["facts"]:
        sid, turn, _ = fact["fact_id"].rsplit(":", 2)
        group = 0 if roles[sid, int(turn)] == "user" else 1
        remaining = char_caps[group] - used[group]
        if blocks[group] >= block_caps[group] or remaining <= 0:
            continue
        text = fact["text"][:remaining]
        selected.append({**fact, "text": text})
        blocks[group] += 1
        used[group] += len(text)
    return {**ranked, "facts": selected}
