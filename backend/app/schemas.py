"""Pydantic schemas for the FastAPI layer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EmailItem(BaseModel):
    """A single fetched email."""

    id: str
    sender: str
    subject: str
    body: str
    timestamp: str
    html: str = ""
    status: str = "new"


class ProcessRequest(BaseModel):
    """Payload for processing a single email through the AI crew."""

    email: EmailItem


class ClassificationOut(BaseModel):
    """Structured classification result returned by the classifier agent."""

    category: str
    topic: str
    priority: str
    urgency_score: int
    summary: str
    custom: dict = Field(default_factory=dict)


class CaseOut(BaseModel):
    """A processed email case with its classification and draft reply."""

    id: str
    email: EmailItem
    classification: ClassificationOut
    draft: str
    created_at: str
    sent_at: str | None = None


class DraftIn(BaseModel):
    """Payload for updating a case's draft reply."""

    draft: str


class ProcessResponse(BaseModel):
    """Result of processing a single email."""

    case: CaseOut


class EmailsResponse(BaseModel):
    """List of fetched emails."""

    emails: list[EmailItem]
    count: int


class SyncResponse(BaseModel):
    """Result of syncing the inbox (fetch + persist)."""

    synced: int
    emails: list[EmailItem]
    count: int


class CasesResponse(BaseModel):
    """List of processed cases."""

    cases: list[CaseOut]
    count: int


class StatsOut(BaseModel):
    """Dashboard statistics computed from the case store."""

    total_emails: int
    processed: int
    pending: int
    success_rate: float
    category_distribution: list[dict]
    recent_activity: list[dict]


class AIConfig(BaseModel):
    """An AI configuration as exposed to the frontend (api key masked)."""

    id: int
    name: str = ""
    provider: str = ""
    model: str = ""
    base_url: str = ""
    api_key: str = ""
    has_api_key: bool = False
    timeout: float = 120
    max_tokens: int = 8000
    temperature: float = 0.2
    enabled: bool = False


class AIConfigIn(BaseModel):
    """Payload for creating or updating an AI configuration."""

    name: str
    provider: str
    model: str
    base_url: str = ""
    api_key: str = ""
    timeout: float = 120
    max_tokens: int = 8000
    temperature: float = 0.2
    enabled: bool = False


class StageConfig(BaseModel):
    """Per-stage settings (system prompt, task prompt, generation params)."""

    role: str = ""
    goal: str = ""
    backstory: str = ""
    prompt: str = ""
    max_tokens: int | None = None
    temperature: float | None = None


class StagesSettings(BaseModel):
    """Global per-stage settings for classification and drafting."""

    classification: StageConfig
    draft: StageConfig


class TestResult(BaseModel):
    """Result of a settings test / connection check."""

    ok: bool
    message: str


class MailAccount(BaseModel):
    """A mail account as exposed to the frontend (password masked)."""

    id: int
    address: str
    imap_host: str = ""
    imap_port: int = 993
    smtp_host: str = ""
    smtp_port: int = 587
    password: str = ""
    has_password: bool = False
    folder: str = "INBOX"
    max_emails: int = 50
    enabled: bool = True


class MailAccountIn(BaseModel):
    """Payload for creating or updating a mail account."""

    address: str
    imap_host: str = ""
    imap_port: int = 993
    smtp_host: str = ""
    smtp_port: int = 587
    password: str = ""
    folder: str = "INBOX"
    max_emails: int = 50
    enabled: bool = True
