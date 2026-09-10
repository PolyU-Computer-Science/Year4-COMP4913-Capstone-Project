"""SMTP sending for approved reply drafts."""

from __future__ import annotations

import re
import smtplib
from email.message import EmailMessage
from typing import Any

_SUBJECT_LINE = re.compile(r"^\s*subject\s*:\s*(.*)$", re.IGNORECASE)
_BODY_LINE = re.compile(r"^\s*body\s*:\s*\??\s*$", re.IGNORECASE)


def strip_subject_body_labels(draft: str) -> str:
    """Normalize a draft to plain body text.

    Newer drafts contain only the body. Legacy drafts may include a
    ``Subject:`` line and a ``Body:`` label; those are stripped and the body
    content returned.
    """
    if not re.search(r"^\s*subject\s*:", draft, re.IGNORECASE) and not re.search(
        r"^\s*body\s*:", draft, re.IGNORECASE
    ):
        return draft.strip()

    lines = draft.splitlines()
    body_lines: list[str] = []
    in_body = False
    for line in lines:
        if _BODY_LINE.match(line):
            in_body = True
            continue
        if _SUBJECT_LINE.match(line):
            continue
        if in_body:
            body_lines.append(line)
    body = "\n".join(body_lines).strip()
    return body if body else draft.strip()


def send_reply(
    account: dict[str, Any],
    to: str,
    subject: str,
    body: str,
) -> None:
    """Send a reply via SMTP using the given mail account.

    ``account`` is a mail-account dict with decrypted ``password`` and the
    ``address`` / ``smtp_host`` / ``smtp_port`` fields.
    """
    address = str(account.get("address") or "")
    host = str(account.get("smtp_host") or "")
    port = int(account.get("smtp_port") or 587)
    password = str(account.get("password") or "")

    if not address or not host:
        raise ValueError("Mail account is missing address or SMTP host")

    msg = EmailMessage()
    msg["From"] = address
    msg["To"] = to
    msg["Subject"] = subject if subject.startswith("Re:") else f"Re: {subject}"
    msg.set_content(strip_subject_body_labels(body))

    if port == 465:
        with smtplib.SMTP_SSL(host, port) as smtp:
            if password:
                smtp.login(address, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if password:
                smtp.login(address, password)
            smtp.send_message(msg)
