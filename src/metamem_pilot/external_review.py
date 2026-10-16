"""File-only external AI assessment; no network judge or human-gold claim."""
import time
import uuid
from pathlib import Path
from .data import digest, read, write_atomic
from .client import Client, RunStopped
from third_party.metamem_judge import get_anscheck_prompt

STANDARD = "upstream-66232c1-external-ai-v1"
REVIEWER = {"type": "external_ai_app", "identity": "Codex, GPT-6 family per application instructions",
            "exact_model_version": "unknown", "human_gold": False,
            "review_mode": "labels_hidden_not_fully_blind"}


def make_item(question, reference, response, task, abstention):
    standard = get_anscheck_prompt(task, question, reference, response, abstention).split("\n\nQuestion:")[0]
    payload = {"sample_id": uuid.uuid4().hex, "question": question, "reference": reference,
               "response": response, "standard": standard, "standard_version": STANDARD}
    return {**payload, "input_sha256": digest(payload)}


def validate_reviews(queue, document):
    if document.get("standard_version") != STANDARD or document.get("queue_sha256") != digest(queue):
        raise ValueError("Wrong standard or queue hash")
    reviewer = document.get("reviewer", {})
    if (reviewer.get("type") != "external_ai_app" or reviewer.get("human_gold") is not False or
            not reviewer.get("identity") or not reviewer.get("exact_model_version")):
        raise ValueError("Explicit AI reviewer identity and non-human provenance required")
    expected = {r["sample_id"]: r for r in queue}
    if len(expected) != len(queue):
        raise ValueError("Duplicate queued ID")
    result = {}
    for row in document.get("results", []):
        sid = row.get("sample_id")
        if sid not in expected or sid in result:
            raise ValueError("Unknown or duplicate review ID")
        item = expected[sid]
        if item["input_sha256"] != digest({k: v for k, v in item.items() if k != "input_sha256"}):
            raise ValueError("Queued input was modified")
        if row.get("input_sha256") != item["input_sha256"]:
            raise ValueError("Review input hash mismatch")
        if row.get("label") not in ("Yes", "No", "uncertain") or not str(row.get("reason", "")).strip():
            raise ValueError("Label and reason required")
        if row.get("unsupported_expansion") not in ("yes", "no", "unknown") or not str(row.get("quality_reason", "")).strip():
            raise ValueError("Separate quality assessment required")
        result[sid] = row
    if set(result) != set(expected):
        raise ValueError("Missing review results")
    return result


class ExternalClient(Client):
    def __init__(self, config, log, deadline_epoch, stop_file, review_dir, max_requests=300):
        super().__init__(config, log, deadline_epoch, stop_file, max_requests)
        self.review_dir = Path(review_dir)
        self.review_dir.mkdir(parents=True, exist_ok=False)
        self.queue_count = 0
        self.review_count = 0
        self.generate_only = False

    def call(self, stage, *args, **kwargs):
        if stage == "judge":
            raise ValueError("External protocol forbids local judge requests")
        return super().call(stage, *args, **kwargs)

    def wait_file(self, path):
        while not path.exists():
            if self.stop_file.exists() or time.time() >= self.deadline_epoch:
                raise RunStopped("Stopped while awaiting external AI file; no automatic resume")
            time.sleep(0.5)
        return read(path)

    def review(self, rows, outputs, labels):
        if self.generate_only:
            return outputs
        queued, mapping = [], []
        for i, result in enumerate(outputs):
            if result["status"] != "generated":
                continue
            row = next(r for r in rows if r["question_id"] == result["question_id"])
            item = make_item(row["question"], labels[row["question_id"]], result["response"],
                             row["task"], row["question_id"].endswith("_abs"))
            queued.append(item)
            mapping.append({"sample_id": item["sample_id"], "output_index": i,
                            "question_id": result["question_id"], "attempt": result["attempt"]})
        if not queued:
            return outputs
        # Opaque IDs/order hide condition names, rules and previous grades from the reviewer file.
        queued.sort(key=lambda r: r["sample_id"])
        index = self.queue_count
        self.queue_count += 1
        queue_path = self.review_dir / f"queue-{index:03d}.json"
        response_path = self.review_dir / f"review-{index:03d}.json"
        write_atomic(self.review_dir / f"mapping-{index:03d}.private.json", mapping)
        write_atomic(queue_path, queued)
        write_atomic(self.review_dir / "awaiting.json", {"queue": queue_path.name, "response": response_path.name,
                                                        "count": len(queued), "queue_sha256": digest(queued)})
        document = self.wait_file(response_path)
        reviewed = validate_reviews(queued, document)
        for item in mapping:
            result = outputs[item["output_index"]]
            assessment = reviewed[item["sample_id"]]
            result.update(external_ai_review=assessment, reviewer=document["reviewer"],
                          scoring_standard_version=STANDARD, human_review=None,
                          status="judge_uncertain" if assessment["label"] == "uncertain" else "valid",
                          correct=None if assessment["label"] == "uncertain" else assessment["label"] == "Yes")
        self.review_count += len(reviewed)
        write_atomic(self.review_dir / f"accepted-{index:03d}.json", document)
        return outputs
