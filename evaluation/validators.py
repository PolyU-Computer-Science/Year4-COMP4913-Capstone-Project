"""Dataset validators.

Reject duplicate IDs, duplicate normalized email bodies, invalid
mailbox/topic/field/source references, malformed records, and train/test
leakage. These run over the generated JSONL files.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from evaluation import fixtures, schemas
from evaluation.fixtures import KNOWLEDGE, MAILBOXES, MTR_MAILBOX

_SCHEMA_BY_NAME = {
    "classification": schemas.ClassificationRecord,
    "field_extraction": schemas.FieldExtractionRecord,
    "retrieval": schemas.RetrievalRecord,
    "drafting": schemas.DraftingRecord,
    "safety": schemas.SafetyRecord,
    "tool_planning": schemas.ToolPlanningRecord,
}

_VALID_MAILBOXES = set(MAILBOXES.keys()) | {MTR_MAILBOX["id"]}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _valid_topic_ids(mailbox: str) -> set[str]:
    if mailbox == MTR_MAILBOX["id"]:
        return {t["id"] for t in MTR_MAILBOX["topics"]}
    if mailbox in MAILBOXES:
        return {t["id"] for t in MAILBOXES[mailbox]["topics"]}
    return set()


def _valid_field_ids(mailbox: str) -> set[str]:
    if mailbox == MTR_MAILBOX["id"]:
        return {f["id"] for f in MTR_MAILBOX["fields"]}
    if mailbox in MAILBOXES:
        return {f["id"] for f in MAILBOXES[mailbox]["fields"]}
    return set()


def _valid_source_ids(mailbox: str) -> set[str]:
    return {s["source_id"] for s in KNOWLEDGE.get(mailbox, [])}


def validate_dataset(name: str, records: list[dict]) -> list[str]:
    """Validate a single dataset's records. Returns a list of error strings."""
    errors: list[str] = []
    schema = _SCHEMA_BY_NAME[name]
    seen_ids: set[str] = set()
    seen_bodies: dict[str, str] = {}

    for i, raw in enumerate(records):
        try:
            record = schema(**raw)
        except Exception as error:  # noqa: BLE001
            errors.append(f"{name}[{i}]: schema error: {error}")
            continue

        # Duplicate ID.
        if record.id in seen_ids:
            errors.append(f"{name}[{i}]: duplicate id {record.id}")
        seen_ids.add(record.id)

        # Invalid mailbox reference.
        if record.mailbox not in _VALID_MAILBOXES:
            errors.append(f"{name}[{i}]: invalid mailbox {record.mailbox}")

        # Duplicate normalized body (for records with bodies).
        body = getattr(record, "body", None) or getattr(record, "query", None)
        if body is not None:
            norm = _normalize(body)
            if norm in seen_bodies:
                errors.append(
                    f"{name}[{i}]: duplicate body with {seen_bodies[norm]}"
                )
            seen_bodies[norm] = record.id

        # Type-specific reference checks.
        if name == "classification":
            if record.topic not in _valid_topic_ids(record.mailbox):
                errors.append(
                    f"{name}[{i}]: topic {record.topic} not valid for {record.mailbox}"
                )
            if record.mailbox in MAILBOXES and record.category not in MAILBOXES[record.mailbox]["categories"]:
                errors.append(f"{name}[{i}]: invalid category {record.category}")
        elif name == "field_extraction":
            for field_id in record.expected_fields:
                if field_id not in _valid_field_ids(record.mailbox):
                    errors.append(
                        f"{name}[{i}]: field {field_id} not valid for {record.mailbox}"
                    )
        elif name == "retrieval":
            for source_id in record.relevant_source_ids:
                if source_id not in _valid_source_ids(record.mailbox):
                    errors.append(
                        f"{name}[{i}]: source {source_id} not valid for {record.mailbox}"
                    )
            if record.answerable and not record.relevant_source_ids:
                errors.append(f"{name}[{i}]: answerable but no relevant sources")
        elif name == "drafting":
            for source_id in record.relevant_sources:
                if source_id not in _valid_source_ids(record.mailbox):
                    errors.append(
                        f"{name}[{i}]: source {source_id} not valid for {record.mailbox}"
                    )

    return errors


def validate_all(directory: Path) -> list[str]:
    errors: list[str] = []
    for name in _SCHEMA_BY_NAME:
        path = directory / f"{name}.jsonl"
        if not path.exists():
            errors.append(f"missing dataset {name}.jsonl")
            continue
        records = [
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        errors.extend(validate_dataset(name, records))
    return errors


def load_dataset(name: str, directory: Path) -> list[dict]:
    path = directory / f"{name}.jsonl"
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def splits(directory: Path, name: str) -> tuple[list[dict], list[dict]]:
    records = load_dataset(name, directory)
    dev = [r for r in records if r["split"] == "dev"]
    test = [r for r in records if r["split"] == "test"]
    return dev, test
