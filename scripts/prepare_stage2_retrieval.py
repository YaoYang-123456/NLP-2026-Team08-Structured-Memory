"""Freeze one selected retrieval candidate; only train and validation histories."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from metamem_pilot.data import read, write, digest, file_hash, retrieve, clean_session
from metamem_pilot.role_retrieval import retrieve_balanced


def safe_history(r):
    return {**{k: r[k] for k in ("question_id", "question_type", "question", "question_date", "haystack_dates", "haystack_session_ids")},
            "haystack_sessions": [clean_session(s) for s in r["haystack_sessions"]]}


def main():
    dest = ROOT / "output/stage2-retrieval"
    dest.mkdir(exist_ok=False)
    stats, diffs = {}, {}
    sources = {"train": read(ROOT / "output/stage2-preparation/train.history-inputs.json"),
               "validation": [safe_history(r) for r in read(ROOT / "output/stage1-evidence/validation-history.json")]}
    for split, histories in sources.items():
        old = read(ROOT / f"data/pilot/{split}.inputs.json")
        histories = {r["question_id"]: r for r in histories}
        improved, stats[split], diffs[split] = [], [], []
        for original in old:
            r = histories[original["question_id"]]
            assert retrieve(r) == original, "Baseline cannot be reproduced"
            candidate = retrieve_balanced(r)
            assert sum(len(f["text"]) for f in candidate["facts"]) <= 12000
            assert len(candidate["facts"]) <= 20
            improved.append(candidate)
            roles = {f"{sid}:{ti}": t["role"] for sid, session in zip(r["haystack_session_ids"], r["haystack_sessions"]) for ti, t in enumerate(session)}
            def metrics(row):
                facts = row["facts"]
                return {"blocks": len(facts), "characters": sum(len(f["text"]) for f in facts),
                        "user_characters": sum(len(f["text"]) for f in facts if roles[f["fact_id"].rsplit(":",1)[0]] == "user"),
                        "facts_sha256": digest(facts)}
            a, b = {f["fact_id"] for f in original["facts"]}, {f["fact_id"] for f in candidate["facts"]}
            stats[split].append({"question_id": r["question_id"], "baseline": metrics(original), "candidate": metrics(candidate), "added": len(b-a), "removed": len(a-b)})
            diffs[split].append({"question_id": r["question_id"], "added": [f for f in candidate["facts"] if f["fact_id"] not in a],
                                  "removed": [f for f in original["facts"] if f["fact_id"] not in b],
                                  "changed_text": [{"before": f, "after": g} for f in original["facts"] for g in candidate["facts"] if f["fact_id"] == g["fact_id"] and f["text"] != g["text"]]})
        write(dest / f"{split}.improved.inputs.json", improved)
    write(dest / "metrics.json", stats)
    write(dest / "facts-diff.json", diffs)
    paths = [ROOT / "data/pilot/validation.inputs.json", dest / "validation.improved.inputs.json", ROOT / "output/stage2-preparation/oracle.inputs.json"]
    write(dest / "inputs.frozen.json", {str(p.relative_to(ROOT)): file_hash(p) for p in paths})
    print({k: {"questions": len(v), "baseline_characters": sum(x["baseline"]["characters"] for x in v), "candidate_characters": sum(x["candidate"]["characters"] for x in v)} for k,v in stats.items()})


if __name__ == "__main__":
    main()
