"""Structured extraction service.

Runs AI extraction, then resolves the topic and validates every field against
the mailbox's definitions. This is a *partial success* pipeline: an invalid
field never blocks valid ones, and manual values are protected from AI
overwrites.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from email_assistant.core.extraction import ExtractionClient, ExtractionResult
from email_assistant.core.field_validation import validate_field_value
from email_assistant.core.topics import resolve_topic


@dataclass
class FieldOutcome:
    field_id: int
    status: str  # accepted | rejected | skipped
    reason: str = ""
    value: Any = None


@dataclass
class ExtractionOutcome:
    topic: str = ""
    topic_id: int | None = None
    topic_resolved: bool = False
    topic_raw: str = ""
    fields: list[FieldOutcome] = field(default_factory=list)

    @property
    def fields_proposed(self) -> int:
        return len(self.fields)

    @property
    def fields_accepted(self) -> int:
        return sum(1 for f in self.fields if f.status == "accepted")

    @property
    def fields_rejected(self) -> int:
        return sum(1 for f in self.fields if f.status == "rejected")

    def accepted_values(self) -> dict[int, Any]:
        return {
            f.field_id: f.value for f in self.fields if f.status == "accepted"
        }


class ExtractionService:
    """Coordinates AI extraction with server-side validation."""

    def __init__(self, client: ExtractionClient) -> None:
        self._client = client

    def extract(
        self,
        email_content: str,
        topics: list[dict[str, Any]],
        fields: list[dict[str, Any]],
    ) -> ExtractionOutcome:
        try:
            result = self._client.extract(email_content, topics, fields)
        except Exception as error:  # noqa: BLE001 - extraction failure must not crash
            return ExtractionOutcome(topic_raw="", fields=[])

        outcome = ExtractionOutcome()

        # Topic resolution.
        raw_topic = result.topic or ""
        topic_id, canonical = resolve_topic(topics, raw_topic)
        outcome.topic_raw = raw_topic
        outcome.topic = canonical if canonical else raw_topic
        outcome.topic_id = topic_id
        outcome.topic_resolved = topic_id is not None

        # Field validation, partial success.
        fields_by_id = {
            int(f["id"]): f
            for f in fields
            if f.get("status", "active") == "active"
        }
        for item in result.fields:
            try:
                field_id = int(item.get("field_id"))
            except (TypeError, ValueError):
                outcome.fields.append(
                    FieldOutcome(field_id=-1, status="rejected", reason="invalid field_id")
                )
                continue

            definition = fields_by_id.get(field_id)
            if definition is None:
                outcome.fields.append(
                    FieldOutcome(
                        field_id=field_id,
                        status="rejected",
                        reason="field does not belong to this mailbox",
                    )
                )
                continue

            value = item.get("value")
            ok, error = validate_field_value(definition, value)
            if not ok:
                outcome.fields.append(
                    FieldOutcome(field_id=field_id, status="rejected", reason=error)
                )
                continue

            outcome.fields.append(
                FieldOutcome(field_id=field_id, status="accepted", value=value)
            )

        return outcome


def outcome_to_values_json(outcome: ExtractionOutcome) -> dict[int, str]:
    """Convert accepted values to {field_id: value_json} for persistence."""
    return {
        field_id: json.dumps(value)
        for field_id, value in outcome.accepted_values().items()
    }
