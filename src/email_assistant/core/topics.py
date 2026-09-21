"""Topic resolution and validation.

The classifier emits a free-form topic string. This module resolves that
string against the mailbox's configured topics so that invalid or
hallucinated topics are handled explicitly instead of being written verbatim.
"""

from __future__ import annotations

import re
from typing import Any


def normalize_topic(value: str) -> str:
    """Normalize a topic for case/whitespace-insensitive comparison."""
    return re.sub(r"[_\-\s]+", " ", str(value or "").strip().lower())


def resolve_topic(
    topics: list[dict[str, Any]], raw_topic: str
) -> tuple[int | None, str]:
    """Resolve a raw topic string to (topic_id, canonical_name).

    Returns ``(None, raw_topic)`` when the raw topic does not match any
    active configured topic — callers should treat this as "unclassified".
    """
    target = normalize_topic(raw_topic)
    if not target:
        return None, ""

    for topic in topics:
        if topic.get("status", "active") != "active":
            continue
        if normalize_topic(topic.get("name", "")) == target:
            return int(topic["id"]), topic.get("name", "")

    return None, raw_topic


def format_topics_prompt(topics: list[dict[str, Any]]) -> str:
    """Render the mailbox's active topics as classifier prompt context."""
    active = [t for t in topics if t.get("status", "active") == "active"]
    if not active:
        return ""

    lines = ["Available topics for this mailbox:"]
    for topic in active:
        name = topic.get("name", "").strip()
        description = (topic.get("description") or "").strip()
        if description:
            lines.append(f"- {name}: {description}")
        else:
            lines.append(f"- {name}")
    return "\n".join(lines)
