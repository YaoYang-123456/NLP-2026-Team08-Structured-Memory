import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from metamem_pilot.data import audit, file_hash, read, write

if __name__ == "__main__":
    source = ROOT / "data/raw/longmemeval_s_cleaned.json"
    report = audit(read(source))
    report["source_sha256"] = file_hash(source)
    write(ROOT / "data/audit.json", report)
    print(__import__("json").dumps(report, indent=2))
