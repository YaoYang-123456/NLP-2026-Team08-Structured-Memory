"""Verify and read C's single-session handoff copy without model/API calls."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def read_bundle(bundle):
    root = Path(bundle).resolve()
    manifest = json.loads((root / "handoff.json").read_text(encoding="utf-8"))
    for relative, expected in manifest["file_sha256"].items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Handoff file escapes bundle directory")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Handoff file hash mismatch: {relative}")
    prepared = json.loads((root / "input.json").read_text(encoding="utf-8"))
    records = json.loads((root / "memories.json").read_text(encoding="utf-8"))
    from qdrant_client import QdrantClient
    client = QdrantClient(path=str(root / "qdrant"))
    try:
        points, offset = client.scroll(manifest["collection"], limit=len(records) + 1,
                                       with_vectors=True)
        if offset is not None or len(points) != manifest["entry_count"]:
            raise ValueError("Database entry count mismatch")
        if {p.id: p.model_dump() for p in points} != {p["id"]: p for p in records}:
            raise ValueError("Database payload/vector differs from export")
        for point in points:
            payload = point.payload
            source = prepared["messages"][payload["source_id"]]
            if (payload["source_sample_id"] != prepared["sample_id"] or
                    payload["source_session_id"] != prepared["session_id"] or
                    payload["source_message_id"] != source["message_id"] or
                    payload["source_key"] != f"{prepared['sample_id']}/{source['message_id']}"):
                raise ValueError("Invalid source binding")
            if (len(point.vector) != manifest["embedding"]["dimensions"] or
                    abs(math.sqrt(sum(x*x for x in point.vector)) - 1) > 1e-5):
                raise ValueError("Embedding dimensions/normalization mismatch")
        types = dict(Counter(p.payload["entry_type"] for p in points))
        if types != manifest["entry_types"]:
            raise ValueError("Entry type counts differ from manifest")
    finally:
        client.close()
    return {"status": "verified", "sample_id": prepared["sample_id"],
            "session_id": prepared["session_id"], "entry_count": len(points),
            "entry_types": types, "conversation_complete": manifest["conversation_complete"],
            "source_messages_referenced": len({p.payload["source_key"] for p in points})}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", help="Extracted handoff directory; use D's own copy")
    args = parser.parse_args()
    print(json.dumps(read_bundle(args.bundle), ensure_ascii=False))
