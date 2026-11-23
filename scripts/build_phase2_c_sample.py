"""Build the Phase 2/C development handoff from the frozen conv-48/86 archive."""
import argparse
from datetime import date, datetime
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "reports/artifacts/s2-predictions-for-E-20261020.zip"
ARCHIVE_SHA256 = "21a6e76a0f097193cdf5bb746dda76008d4237fae8a5d92028dcce1c51c12de6"
SAMPLE_ID = "conv-48"
QA_INDEX = 86
PREDICTIONS = "predictions30.jsonl"
# Use the offline pilot's sentence boundaries, retaining offsets into the original text.
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")
MESSAGE_ID = re.compile(r"D\d+:\d+\Z")


def read_contexts(archive):
    data = archive.read_bytes()
    if sha256(data).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("S2 archive SHA-256 does not match the frozen handoff")
    with ZipFile(BytesIO(data)) as bundle:
        matching = []
        for raw in bundle.read(PREDICTIONS).splitlines():
            row = json.loads(raw)
            if (row["sample_id"], row["qa_index"]) == (SAMPLE_ID, QA_INDEX):
                matching.append(row["contexts"])
    if len(matching) != 1:
        raise ValueError("Expected exactly one archived conv-48/86 context list")
    contexts = matching[0]
    if [context["kind"] for context in contexts] != ["event"] * 60 + ["synthesis"] * 5:
        raise ValueError("Expected the original ordering of 60 events and five syntheses")
    return contexts


def read_message_index(handoff):
    manifest_data = (handoff / "files.sha256.json").read_bytes()
    manifest = json.loads(manifest_data)
    prefix = f"inputs/{SAMPLE_ID}/"
    sessions = sorted(name for name in manifest if name.startswith(prefix))
    if len(sessions) != 30:
        raise ValueError("Expected 30 frozen conv-48 session inputs")
    messages = {}
    for name in sessions:
        data = (handoff / name).read_bytes()
        if sha256(data).hexdigest() != manifest[name]:
            raise ValueError(f"Session SHA-256 mismatch: {name}")
        session = json.loads(data)
        if session["sample_id"] != SAMPLE_ID:
            raise ValueError(f"Unexpected sample identity in {name}")
        for position, message in enumerate(session["messages"], 1):
            source_id = f"{SAMPLE_ID}/{message['message_id']}"
            if source_id in messages:
                raise ValueError(f"Duplicate source message: {source_id}")
            messages[source_id] = {
                "path": name,
                "position": position,
                "speaker": message["speaker_name"],
                "session_start": session["timestamp"],
            }
    return messages, sha256(manifest_data).hexdigest()


def sentence_units(parent):
    text = parent["text"]
    start = text.index("\n") + 1
    spans = []
    for boundary in SENTENCE_BREAK.finditer(text, start):
        if boundary.start() > start:
            spans.append((start, boundary.start()))
        start = boundary.end()
    if start < len(text):
        spans.append((start, len(text)))
    if not spans:
        raise ValueError(f"Empty synthesis body: {parent['id']}")
    return [
        {
            "id": f"{parent['id']}/sentence/{position}",
            "kind": "synthesis",
            "text": text[start:end],
            "parent": parent["id"],
            "position": position,
            "char_span": [start, end],
            "time_range": parent["time_range"],
            "source_ids": [parent["id"]],
            "source_scope": "parent_synthesis",
        }
        for position, (start, end) in enumerate(spans, 1)
    ]


def review_cases(parents, units):
    by_position = {(unit["parent"], unit["position"]): unit for unit in units if unit["parent"]}
    parents_by_rank = {parent["archive_rank"]: parent for parent in parents}

    # Sample review decisions, keyed by frozen parent rank and sentence position.
    examples = [
        (62, 4, 3, "She shared a photo", "Deborah explained", "keep_antecedent"),
        (65, 6, 5, "She's been studying", "Jolene admitted", "keep_antecedent"),
        (62, 12, 1, "a year earlier", "On January 27, 2023", "use_parent_time_range"),
        (61, 10, 9, "This exchange", "Jolene, who had long wanted", "review_transition"),
    ]
    dependencies = {}
    cases = []
    for rank, position, prior_position, phrase, prior_phrase, decision in examples:
        parent = parents_by_rank[rank]
        unit = by_position[parent["id"], position]
        prior = by_position[parent["id"], prior_position]
        if phrase not in unit["text"] or prior_phrase not in prior["text"]:
            raise ValueError(f"Reviewed source text changed: {unit['id']}")
        if prior_position >= position:
            raise ValueError(f"Dependency does not point to an earlier sentence: {unit['id']}")
        if decision == "use_parent_time_range":
            header_date = datetime.fromisoformat(parent["time_range"]["start"]).date()
            body_date = date(2023, 1, 27)
            if header_date != body_date:
                raise ValueError(f"The reviewed date is absent from the time header: {parent['id']}")
        dependencies[unit["id"]] = [prior["id"]] if decision == "keep_antecedent" else []
        cases.append({"unit_id": unit["id"], "considered_unit_id": prior["id"], "decision": decision})
    return dependencies, cases


def build(archive, handoff):
    contexts = read_contexts(archive)
    messages, manifest_hash = read_message_index(handoff)
    # Event references outside this retrieval result are retained on their parent.
    known_events = {context["source_ids"][0] for context in contexts if context["kind"] == "event"}
    seen = set()
    parents, units = [], []
    used_messages = {}
    for rank, context in enumerate(contexts, 1):
        kind = context["kind"]
        identity, *sources = context["source_ids"]
        if not identity.startswith(f"{SAMPLE_ID}/{kind}/") or identity in seen:
            raise ValueError(f"Invalid or duplicate candidate identity: {identity}")
        seen.add(identity)
        for source_id in sources:
            conversation, _, part = source_id.partition("/")
            if conversation != SAMPLE_ID:
                raise ValueError(f"Source belongs to another conversation: {source_id}")
            if MESSAGE_ID.fullmatch(part):
                if source_id not in messages:
                    raise ValueError(f"Source is absent from verified inputs: {source_id}")
                used_messages[source_id] = messages[source_id]
            elif kind != "synthesis" or not part.startswith("event/"):
                raise ValueError(f"Unexpected source identifier: {source_id}")

        entry = {
            "id": identity,
            "kind": kind,
            "text": context["text"],
            "archive_rank": rank,
            "source_ids": context["source_ids"],
        }
        if kind == "event":
            speaker, recorded, body = context["text"].split("\n", 2)
            if not speaker.startswith("Speaker: ") or not recorded.startswith("Recorded: ") or not body.strip():
                raise ValueError(f"Invalid archived event display: {identity}")
            timestamp = recorded.removeprefix("Recorded: ").split(",", 1)[0]
            datetime.fromisoformat(timestamp)
            entry.update(parent=None, position=None, recorded_at=timestamp, source_scope="event")
            units.append(entry)
            continue

        header = context["text"].split("\n", 1)[0]
        if not header.startswith("Time range: "):
            raise ValueError(f"Missing archived synthesis time range: {identity}")
        start, end = header.removeprefix("Time range: ").split(" — ")
        if datetime.fromisoformat(start) > datetime.fromisoformat(end):
            raise ValueError(f"Reversed synthesis time range: {identity}")
        entry["time_range"] = {"start": start, "end": end}
        entry["available_event_ids"] = [source_id for source_id in sources if source_id in known_events]
        parents.append(entry)
        units.extend(sentence_units(entry))

    dependencies, cases = review_cases(parents, units)
    return {
        "scope": {
            "sample_id": SAMPLE_ID,
            "qa_index": QA_INDEX,
            "subset": "archived_s2_contexts",
            "archive_sha256": ARCHIVE_SHA256,
            "archive_member": PREDICTIONS,
            "event_handoff_manifest_sha256": manifest_hash,
            "dependency_coverage": "review_cases_only",
        },
        "units": units,
        "parents": parents,
        "source_messages": dict(sorted(used_messages.items())),
        "dependencies": dependencies,
        "review_cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--event-handoff", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = build(args.archive, args.event_handoff)
    args.out.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
