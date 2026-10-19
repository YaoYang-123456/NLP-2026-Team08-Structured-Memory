"""Download the official pinned cleaned S release; never overwrite existing data."""
import hashlib
import json
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REVISION = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
EXPECTED_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
URL = ("https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/"
       + REVISION + "/longmemeval_s_cleaned.json")
ROOT = Path(__file__).resolve().parents[1]


def main():
    dest = ROOT / "data/raw/longmemeval_s_cleaned.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise SystemExit("Already exists; verify its manifest instead of overwriting.")
    temp = dest.with_suffix(".json.partial")
    with urllib.request.urlopen(URL, timeout=60) as response, temp.open("xb") as out:
        shutil.copyfileobj(response, out, length=1024 * 1024)
    with temp.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit("SHA-256 differs from the official pinned LFS object.")
    temp.rename(dest)
    manifest = {
        "url": URL, "revision": REVISION,
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "filename": dest.name, "bytes": dest.stat().st_size, "sha256": digest,
    }
    dest.with_suffix(".source.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
