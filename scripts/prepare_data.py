"""Freeze a disjoint pilot and retrieve once for all three conditions."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from metamem_pilot.data import audit, file_hash, overlap_report, read, retrieve, split_rows, write
from download_data import EXPECTED_SHA256


def main():
    source = ROOT / "data/raw/longmemeval_s_cleaned.json"
    if file_hash(source) != EXPECTED_SHA256:
        raise ValueError("Dataset differs from pinned release")
    dest = ROOT / "data/pilot"
    if dest.exists():
        raise FileExistsError("Pilot exists; use its frozen manifest, do not overwrite")
    rows = read(source)
    report = audit(rows)
    excluded = {e.get("id") for e in report["issues"]}
    if None in excluded:
        raise ValueError("Dataset-wide audit error")
    splits = split_rows(rows, excluded)
    overlaps = overlap_report(splits)
    if any(n for pair in overlaps.values() for n in pair.values()):
        raise ValueError("Cross-split leakage")
    manifest = {"source_sha256": EXPECTED_SHA256, "seed": 42,
                "selection": "sorted IDs, seed 42 shuffle, seven strata round-robin; interleave train/validation/test, reject overlap with other splits",
                "excluded_issues": report["issues"], "overlaps": overlaps,
                "retrieval": {"method": "BM25", "k1": 1.5, "b": 0.75, "top_k": 20,
                              "max_chars": 12000, "chunk_words": 180}, "splits": {}, "files": {},
                "manual_rules_sha256": file_hash(ROOT / "configs/rules-b1.json")}
    for split, selected in splits.items():
        manifest["splits"][split] = [{"question_id": r["question_id"], "task": r["question_type"]} for r in selected]
        write(dest / f"{split}.inputs.json", [retrieve(r) for r in selected])
        write(dest / f"{split}.labels.json", {r["question_id"]: str(r["answer"]) for r in selected})
        for kind in ("inputs", "labels"):
            name = f"{split}.{kind}.json"
            manifest["files"][name] = file_hash(dest / name)
    write(dest / "manifest.json", manifest)
    write(ROOT / "data/audit.json", {**report, "source_sha256": EXPECTED_SHA256})
    print({"counts": {k: len(v) for k, v in splits.items()}, "overlaps": overlaps,
           "manifest_sha256": file_hash(dest / "manifest.json")})


if __name__ == "__main__":
    main()
