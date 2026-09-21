"""Unified Mailbox runtime context.

A mailbox is an isolated business context. This module centralises loading
everything the AI pipeline needs for a given mailbox — topics, custom field
definitions, AI configuration, knowledge sources and connectors — so that
agents never load mailbox resources piecemeal across the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MailboxRuntimeContext:
    """All runtime-relevant resources for a single mailbox."""

    mailbox: dict[str, Any]
    topics: list[dict[str, Any]] = field(default_factory=list)
    fields: list[dict[str, Any]] = field(default_factory=list)
    ai_configs: list[dict[str, Any]] = field(default_factory=list)
    knowledge_sources: list[dict[str, Any]] = field(default_factory=list)
    connectors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def mailbox_id(self) -> int:
        return int(self.mailbox["id"])

    @property
    def active_topics(self) -> list[dict[str, Any]]:
        return [t for t in self.topics if t.get("status", "active") == "active"]

    @property
    def active_fields(self) -> list[dict[str, Any]]:
        return [f for f in self.fields if f.get("status", "active") == "active"]


class MailboxContextService:
    """Loads a full MailboxRuntimeContext from the settings store."""

    def load(self, mailbox_id: int) -> MailboxRuntimeContext | None:
        from email_assistant.core.settings_store import SettingsStore

        store = SettingsStore()
        mailbox = store.get_mailbox(mailbox_id)
        if mailbox is None:
            return None

        return MailboxRuntimeContext(
            mailbox=mailbox,
            topics=store.list_topics(mailbox_id),
            fields=store.list_custom_fields(mailbox_id),
            ai_configs=store.list_ai_configs(),
            knowledge_sources=store.list_mailbox_knowledge(mailbox_id),
            connectors=store.list_mailbox_connectors(mailbox_id),
        )


def load_mailbox_context(mailbox_id: int) -> MailboxRuntimeContext | None:
    """Convenience helper: load a mailbox runtime context or None."""
    return MailboxContextService().load(mailbox_id)
