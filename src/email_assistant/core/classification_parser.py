"""Tolerant parser for the classifier's structured output.

Local reasoning models (e.g. Qwen3) often emit the classification as a
Python-style literal (``category='spam' topic='...'``) instead of JSON, which
CrewAI's ``output_pydantic`` parser rejects. This module recovers the
structured result from either format.
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from email_assistant.models import EmailClassification


def _strip_code_fences(text: str) -> str:
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text.strip()


def _extract_json(text: str) -> dict | None:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _extract_json_object(text: str) -> dict | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return _extract_json(text[start : end + 1])


def _extract_python_literal(text: str) -> dict | None:
    def string_field(name: str) -> str | None:
        match = re.search(name + r"\s*=\s*'([^']*)'", text)
        return match.group(1) if match else None

    def int_field(name: str) -> int | None:
        match = re.search(name + r"\s*=\s*(-?\d+)", text)
        return int(match.group(1)) if match else None

    category = string_field("category")
    topic = string_field("topic")
    priority = string_field("priority")
    summary = string_field("summary")

    if category is None and topic is None and summary is None:
        return None

    return {
        "category": category,
        "topic": topic or "",
        "priority": priority or "normal",
        "urgency_score": int_field("urgency_score") or 0,
        "summary": summary or "",
        "custom": {},
    }


def parse_classification(text: str) -> EmailClassification | None:
    """Parse a classifier answer into an EmailClassification, or None."""
    if not text:
        return None

    cleaned = _strip_code_fences(text)

    for candidate in (_extract_json(cleaned), _extract_json_object(cleaned)):
        if candidate is not None:
            try:
                return EmailClassification(**candidate)
            except ValidationError:
                continue

    literal = _extract_python_literal(cleaned)
    if literal is None:
        return None
    try:
        return EmailClassification(**literal)
    except ValidationError:
        return None
