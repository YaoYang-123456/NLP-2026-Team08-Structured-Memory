"""Audit source fields without exposing answers and build reproducible inputs."""
import hashlib
import json
import re
import math
import random
from collections import Counter, defaultdict
from pathlib import Path


def encoded(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(obj):
    return hashlib.sha256(encoded(obj)).hexdigest()


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def normalize(text):
    return " ".join(text.lower().split())


def clean_session(session):
    # Whitelist input fields: has_answer and other annotations never reach retrieval.
    return [{"role": t["role"], "content": t["content"]} for t in session]


def keys(row):
    return {
        "question": {digest(normalize(row["question"]))},
        "session_id": set(row["haystack_session_ids"]),
        "session_content": {digest(clean_session(s)) for s in row["haystack_sessions"]},
        "history": {digest([clean_session(s) for s in row["haystack_sessions"]])},
    }


def components(rows, fields):
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, row in enumerate(rows):
        row_keys = keys(row)
        for field in fields:
            for value in row_keys[field]:
                key = field, value
                if key in seen:
                    parent[find(i)] = find(seen[key])
                else:
                    seen[key] = i
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[find(i)].append(row["question_id"])
    return sorted(groups.values(), key=lambda g: (-len(g), sorted(g)))


def audit(rows):
    required = {"question_id", "question_type", "question", "answer", "question_date",
                "haystack_session_ids", "haystack_dates", "haystack_sessions", "answer_session_ids"}
    issues = []
    id_counts = Counter()
    fields = Counter()
    answer_types = Counter()
    session_variants = defaultdict(set)
    counts = {k: Counter() for k in ["question", "session_id", "session_content", "history"]}
    for row in rows:
        fields.update(row.keys())
        qid = row.get("question_id")
        if required - row.keys():
            issues.append({"id": qid, "missing": sorted(required - row.keys())})
            continue
        id_counts[qid] += 1
        answer_types[type(row["answer"]).__name__] += 1
        for field in ("question_id", "question_type", "question", "question_date"):
            if not isinstance(row[field], str) or not row[field].strip():
                issues.append({"id": qid, "invalid": field})
        if row["answer"] is None or row["answer"] == "":
            issues.append({"id": qid, "invalid": "answer"})
        if not (len(row["haystack_session_ids"]) == len(row["haystack_dates"]) == len(row["haystack_sessions"])):
            issues.append({"id": qid, "invalid": "history alignment"})
        if len(set(row["haystack_session_ids"])) != len(row["haystack_session_ids"]):
            issues.append({"id": qid, "invalid": "duplicate session within history"})
        for sid, session in zip(row["haystack_session_ids"], row["haystack_sessions"]):
            if not session or any(t.get("role") not in ("user", "assistant", "system") or
                                  not isinstance(t.get("content"), str) or not t["content"].strip()
                                  for t in session):
                issues.append({"id": qid, "invalid": "empty or malformed session"})
            session_variants[sid].add(digest(clean_session(session)))
        for k, values in keys(row).items():
            counts[k].update(values)
    if any(v > 1 for v in id_counts.values()):
        issues.append({"invalid": "duplicate question_id"})
    return {
        "rows": len(rows), "fields": dict(fields), "issues": issues,
        "unique_question_ids": len(id_counts), "answer_types": dict(answer_types),
        "tasks": dict(Counter(r["question_type"] for r in rows)),
        "abstention": sum(r["question_id"].endswith("_abs") for r in rows),
        "repeated_keys_across_questions": {k: sum(n > 1 for n in c.values()) for k, c in counts.items()},
        "session_ids_with_multiple_content_versions": sum(len(v) > 1 for v in session_variants.values()),
        "full_overlap_component_sizes": [len(g) for g in components(rows, tuple(counts))],
        "question_history_component_sizes": [len(g) for g in components(rows, ("question", "history"))],
        "user_id_available": any("user_id" in r for r in rows),
    }


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def split_rows(rows, excluded, seed=42, sizes=(20, 10, 20)):
    """Select an induced subset with no cross-split overlap; omitted rows are unused."""
    pool = sorted((r for r in rows if r["question_id"] not in excluded), key=lambda r: r["question_id"])
    random.Random(seed).shuffle(pool)
    footprints = {r["question_id"]: {(k, v) for k, vs in keys(r).items() for v in vs} for r in pool}
    splits = {name: [] for name in ("train", "validation", "test")}
    used = {name: set() for name in splits}
    strata = sorted({"abstention" if r["question_id"].endswith("_abs") else r["question_type"] for r in pool})
    for i in range(max(sizes)):
        for name, size in zip(splits, sizes):
            if i >= size:
                continue
            others = set().union(*(values for split, values in used.items() if split != name))
            own = {r["question_id"] for r in splits[name]}
            available = [r for r in pool if r["question_id"] not in own and not footprints[r["question_id"]] & others]
            if not available:
                continue
            stratum = strata[i % len(strata)]
            row = next((r for r in available if
                        ("abstention" if r["question_id"].endswith("_abs") else r["question_type"]) == stratum),
                       available[0])
            splits[name].append(row)
            used[name].update(footprints[row["question_id"]])
    if any(not rows for rows in splits.values()):
        raise ValueError("No disjoint rows remain for one of the splits")
    return splits


def overlap_report(splits):
    footprints = {}
    for name, rows in splits.items():
        fp = defaultdict(set)
        for row in rows:
            fp["question_id"].add(row["question_id"])
            for key, values in keys(row).items():
                fp[key].update(values)
        footprints[name] = fp
    return {a + ":" + b: {key: len(footprints[a][key] & footprints[b][key]) for key in footprints[a]}
            for a in footprints for b in footprints if a < b}


def retrieve(row, top_k=20, max_chars=12000, chunk_words=180):
    docs = []
    for sid, date, session in zip(row["haystack_session_ids"], row["haystack_dates"], row["haystack_sessions"]):
        for ti, turn in enumerate(clean_session(session)):
            words = turn["content"].split()
            for offset in range(0, len(words), chunk_words):
                text = f"{date} {turn['role']}: " + " ".join(words[offset:offset + chunk_words])
                docs.append({"fact_id": f"{sid}:{ti}:{offset // chunk_words}", "text": text})
    counters = [Counter(tokenize(d["text"])) for d in docs]
    df = Counter(t for c in counters for t in c)
    lengths = [sum(c.values()) for c in counters]
    avg = sum(lengths) / len(lengths)
    query = set(tokenize(row["question"]))
    scores = []
    for i, (c, length) in enumerate(zip(counters, lengths)):
        score = sum(math.log(1 + (len(docs) - df[t] + 0.5) / (df[t] + 0.5)) *
                    c[t] * 2.5 / (c[t] + 1.5 * (0.25 + 0.75 * length / avg))
                    for t in query if c[t])
        scores.append((score, i))
    facts = []
    used = 0
    for score, i in sorted(scores, key=lambda x: (-x[0], x[1]))[:top_k]:
        text = docs[i]["text"][:max_chars - used]
        if not text:
            break
        facts.append({**docs[i], "text": text, "score": score})
        used += len(text)
    return {"question_id": row["question_id"], "task": row["question_type"],
            "question": row["question"], "question_date": row["question_date"], "facts": facts}
