from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Self

from dotenv import load_dotenv
from imap_tools import AND, MailBox, MailMessage
import os

SAMPLE_EMAILS: list[dict[str, str]] = [
    {
        "sender": "sarah.chen@example.com",
        "subject": "Meeting Request \u2014 Project Q3 Review",
        "body": (
            "Hi team,\n\n"
            "I'd like to schedule a Q3 project review meeting next week. "
            "Please let me know your availability for Tuesday or Wednesday "
            "afternoon.\n\n"
            "Best regards,\n"
            "Sarah Chen"
        ),
        "timestamp": "2026-07-28T14:30:00Z",
    },
    {
        "sender": "notifications@secureplatform.com",
        "subject": "Action Required: Verify Your Account Email Address",
        "body": (
            "Hello,\n\n"
            "We recently detected a login attempt from a new device. To ensure "
            "the security of your account, please verify your email address by "
            "clicking the link below.\n\n"
            "This link will expire in 24 hours. If you did not attempt to log "
            "in, please ignore this email or contact our support team "
            "immediately.\n\n"
            "Thank you for keeping your account secure.\n\n"
            "Best regards,\n"
            "Security Team"
        ),
        "timestamp": "2026-07-29T09:15:43Z",
    },
    {
        "sender": "newsletter@dealsdaily.com",
        "subject": "\U0001f525 70% OFF Everything \u2014 Limited Time!",
        "body": (
            "Don't miss out on our biggest sale of the year! "
            "70% off storewide, plus free shipping on orders over $50. "
            "Shop now at dealsdaily.com/sale."
        ),
        "timestamp": "2026-07-30T06:00:00Z",
    },
]


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
            print("WARNING: EMAIL_ENABLED=true but EMAIL_ADDRESS is not set. Falling back to sample data.")
            enabled = False

        if enabled and not password:
            print("WARNING: EMAIL_ENABLED=true but EMAIL_PASSWORD is not set. Falling back to sample data.")
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


def _convert_message(msg: MailMessage) -> dict[str, str]:
    """Convert an imap_tools MailMessage to the internal email dict format."""
    from_dt = msg.date
    if from_dt:
        if from_dt.tzinfo is None:
            from_dt = from_dt.replace(tzinfo=timezone.utc)
        timestamp = from_dt.isoformat()
    else:
        timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "sender": msg.from_,
        "subject": msg.subject or "(no subject)",
        "body": msg.text or msg.html or "",
        "timestamp": timestamp,
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


def fetch_emails() -> list[dict[str, str]]:
    """Fetch unread emails from the inbox via IMAP, falling back to sample data.

    If EMAIL_ENABLED is true and valid credentials are configured, this
    function connects to the IMAP server and retrieves unread emails.
    Otherwise it returns the static SAMPLE_EMAILS for development and
    testing.
    """
    settings = EmailSettings.from_env()

    if settings.enabled and settings.address:
        try:
            emails = fetch_via_imap(settings)
            if emails:
                return emails
        except Exception as e:
            print(f"IMAP fetch failed: {e}")
            print("Falling back to sample data.")

    print("Using sample email data for development.")
    return SAMPLE_EMAILS
