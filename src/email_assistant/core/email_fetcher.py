from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Self

from dotenv import load_dotenv
from imap_tools import AND, MailBox, MailMessage
import os


def format_email(email: dict[str, str]) -> str:
    """Render a structured email dict into a plain-text block for the LLM."""
    return (
        f"From: {email['sender']}\n"
        f"Subject: {email['subject']}\n"
        f"Date: {email['timestamp']}\n"
        f"\n"
        f"{email['body']}"
    )


@dataclass(frozen=True)
class EmailSettings:
    """Configuration for IMAP email fetching."""

    enabled: bool = False
    server: str = "imap.gmail.com"
    port: int = 993
    address: str = ""
    password: str = ""
    folder: str = "INBOX"
    max_emails: int = 50

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Self:
        if env is None:
            load_dotenv(override=False)
            source: Mapping[str, str] = os.environ
        else:
            source = env

        enabled = _get_str(source, "EMAIL_ENABLED", "false").lower() in ("true", "1", "yes")
        address = _get_str(source, "EMAIL_ADDRESS", "").strip()
        password = _get_str(source, "EMAIL_PASSWORD", "").strip()

        if enabled and not address:
            print("WARNING: EMAIL_ENABLED=true but EMAIL_ADDRESS is not set.")
            enabled = False

        if enabled and not password:
            print("WARNING: EMAIL_ENABLED=true but EMAIL_PASSWORD is not set.")
            enabled = False

        max_emails = 50
        raw_max = _get_str(source, "EMAIL_MAX_EMAILS", "50").strip()
        try:
            max_emails = int(raw_max)
            if max_emails < 1:
                max_emails = 50
        except ValueError:
            pass

        return cls(
            enabled=enabled,
            server=_get_str(source, "EMAIL_SERVER", "imap.gmail.com"),
            port=int(_get_str(source, "EMAIL_PORT", "993")),
            address=address,
            password=password,
            folder=_get_str(source, "EMAIL_FOLDER", "INBOX"),
            max_emails=max_emails,
        )


def _get_str(env: Mapping[str, str], name: str, default: str) -> str:
    value = env.get(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


def _convert_message(msg: MailMessage) -> dict:
    """Convert an imap_tools MailMessage to the internal email dict format."""
    from_dt = msg.date
    if from_dt:
        if from_dt.tzinfo is None:
            from_dt = from_dt.replace(tzinfo=timezone.utc)
        timestamp = from_dt.isoformat()
    else:
        timestamp = datetime.now(timezone.utc).isoformat()

    inline_attachments = []
    for att in msg.attachments:
        cid = (att.content_id or "").strip().strip("<>").strip()
        if cid and (att.content_type or "").startswith("image/"):
            inline_attachments.append(
                {
                    "cid": cid,
                    "content_type": att.content_type,
                    "filename": att.filename or "",
                    "data": att.payload,
                }
            )

    return {
        "sender": msg.from_,
        "subject": msg.subject or "(no subject)",
        "body": msg.text or msg.html or "",
        "html": msg.html or "",
        "timestamp": timestamp,
        "attachments": inline_attachments,
    }


def fetch_via_imap(settings: EmailSettings) -> list[dict[str, str]]:
    """Fetch unread emails from IMAP server."""
    print(f"Connecting to IMAP server: {settings.server}:{settings.port}")
    print(f"Fetching unread emails from folder: {settings.folder}")

    with MailBox(settings.server, port=settings.port).login(
        settings.address,
        settings.password,
        initial_folder=settings.folder,
    ) as mailbox:
        criteria = AND(seen=False)
        messages = list(mailbox.fetch(criteria, limit=settings.max_emails))

        if not messages:
            print("No unread emails found.")
            return []

        print(f"Found {len(messages)} unread email(s).")

        emails = []
        for msg in messages:
            email = _convert_message(msg)
            emails.append(email)

        return emails


def load_email_settings() -> EmailSettings:
    """Resolve email settings, preferring an enabled DB mail account over env."""
    from email_assistant.core.settings_store import SettingsStore

    account = SettingsStore().get_enabled_mail_account()
    if account is None:
        return EmailSettings.from_env()

    return EmailSettings(
        enabled=True,
        server=str(account.get("imap_host") or "imap.gmail.com"),
        port=int(account.get("imap_port") or 993),
        address=str(account.get("address") or ""),
        password=str(account.get("password") or ""),
        folder=str(account.get("folder") or "INBOX"),
        max_emails=int(account.get("max_emails") or 50),
    )


def fetch_emails() -> list[dict[str, str]]:
    """Fetch unread emails from the inbox via IMAP.

    If an enabled mail account is configured (settings DB) or EMAIL_ENABLED is
    true with valid credentials, this function connects to the IMAP server and
    retrieves unread emails, raising on connection/auth errors. Otherwise it
    returns an empty list.
    """
    settings = load_email_settings()

    if settings.enabled and settings.address:
        return fetch_via_imap(settings)

    print("No enabled mail account; no emails to fetch.")
    return []
