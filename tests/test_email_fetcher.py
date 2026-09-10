from __future__ import annotations

import pytest

from email_assistant.core.email_fetcher import (
    EmailSettings,
    fetch_emails,
)


def _imap_settings() -> EmailSettings:
    return EmailSettings(
        enabled=True,
        server="imap.gmail.com",
        port=993,
        address="a@b.com",
        password="pw",
    )


def test_fetch_emails_returns_empty_when_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        "email_assistant.core.email_fetcher.load_email_settings",
        lambda: EmailSettings(enabled=False),
    )

    assert fetch_emails() == []


def test_fetch_emails_returns_empty_when_imap_has_no_mail(monkeypatch) -> None:
    monkeypatch.setattr(
        "email_assistant.core.email_fetcher.load_email_settings",
        _imap_settings,
    )
    monkeypatch.setattr(
        "email_assistant.core.email_fetcher.fetch_via_imap",
        lambda settings: [],
    )

    assert fetch_emails() == []


def test_fetch_emails_raises_on_imap_error(monkeypatch) -> None:
    monkeypatch.setattr(
        "email_assistant.core.email_fetcher.load_email_settings",
        _imap_settings,
    )

    def boom(settings: EmailSettings) -> list:
        raise RuntimeError("connection refused")

    monkeypatch.setattr(
        "email_assistant.core.email_fetcher.fetch_via_imap",
        boom,
    )

    with pytest.raises(RuntimeError, match="connection refused"):
        fetch_emails()
