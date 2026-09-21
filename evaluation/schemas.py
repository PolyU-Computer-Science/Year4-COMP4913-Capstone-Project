"""Pydantic schemas for evaluation dataset records.

Each record type has a strict schema; the validators reject any record that
does not conform, has a duplicate ID, duplicates a normalized email body, or
references a mailbox/topic/field/source that does not exist in the fixtures.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ClassificationRecord(BaseModel):
    id: str
    mailbox: str
    split: str = Field(pattern="^(dev|test)$")
    category: str
    topic: str
    subject: str
    body: str


class FieldExtractionRecord(BaseModel):
    id: str
    mailbox: str
    split: str = Field(pattern="^(dev|test)$")
    subject: str
    body: str
    expected_fields: dict[str, Any] = Field(default_factory=dict)


class RetrievalRecord(BaseModel):
    id: str
    mailbox: str
    split: str = Field(pattern="^(dev|test)$")
    query: str
    relevant_source_ids: list[str] = Field(default_factory=list)
    answerable: bool


class DraftingRecord(BaseModel):
    id: str
    mailbox: str
    split: str = Field(pattern="^(dev|test)$")
    subject: str
    body: str
    relevant_sources: list[str] = Field(default_factory=list)
    required_facts: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    expected_action: str = Field(default="draft_reply")


class SafetyRecord(BaseModel):
    id: str
    mailbox: str
    split: str = Field(pattern="^(dev|test)$")
    subject: str
    body: str
    must_not: list[str] = Field(default_factory=list)
    must: list[str] = Field(default_factory=list)


class ToolPlanningRecord(BaseModel):
    id: str
    mailbox: str
    split: str = Field(pattern="^(dev|test)$")
    subject: str
    body: str
    tool_required: bool
    expected_connector: str = ""
    expected_tool_capability: str = ""
    expected_arguments: dict[str, Any] = Field(default_factory=dict)
