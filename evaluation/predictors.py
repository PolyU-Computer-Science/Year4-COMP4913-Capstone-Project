"""Predictor adapters bridging the evaluation harness to the runtime clients.

These wrap the MiMo structured client (classification), the OpenRouter
embedding client + retriever (retrieval), and the MCP gateway (tool planning).
They are thin — the harness is model-agnostic and these are the real adapters.
"""

from __future__ import annotations

from typing import Any


class StructuredClassificationPredictor:
    """Classification predictor backed by MiMo structured output + validators."""

    def __init__(self, client: Any, topics: list[dict], fields: list[dict] | None = None) -> None:
        from email_assistant.core.structured_classification import StructuredClassifier

        self._classifier = StructuredClassifier(client)
        self._topics = topics
        self._fields = fields or []

    def predict(self, subject: str, body: str) -> dict[str, Any]:
        email_content = f"Subject: {subject}\n\n{body}"
        outcome = self._classifier.classify(email_content, self._topics, self._fields)
        return {
            "category": outcome.category,
            "topic": outcome.topic,
            "topic_resolved": outcome.topic_resolved,
        }


class RetrieverPredictor:
    """Retrieval predictor backed by the OpenRouter embedding retriever."""

    def __init__(self, mailbox_id: int, retriever: Any) -> None:
        self._mailbox_id = mailbox_id
        self._retriever = retriever

    def search(self, query: str, top_k: int) -> list[str]:
        results = self._retriever.search(self._mailbox_id, query, top_k=top_k)
        return [r.source_id for r in results]


class FieldExtractionPredictor:
    """Field extraction predictor backed by the structured extraction service."""

    def __init__(self, client: Any, topics: list[dict], fields: list[dict]) -> None:
        from email_assistant.core.extraction import FakeExtractionClient  # noqa: F401
        from email_assistant.core.extraction_service import ExtractionService

        self._service = ExtractionService(client)
        self._topics = topics
        self._fields = fields

    def extract(self, subject: str, body: str) -> dict[str, Any]:
        email_content = f"Subject: {subject}\n\n{body}"
        outcome = self._service.extract(email_content, self._topics, self._fields)
        return {str(f.field_id): f.value for f in outcome.fields if f.status == "accepted"}
