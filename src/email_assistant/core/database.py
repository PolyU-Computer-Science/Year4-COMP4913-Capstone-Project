"""SQLite persistence layer for emails, classifications, and drafts.

Emails are stored as tickets with standard fields (status, priority, category,
topic) plus the AI classification result and the generated draft reply. The
database path is resolved from the ``SQLITE_EMAIL_DB`` environment variable
(default ``data/emails.db``) and can be overridden per instance for testing.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(override=False)


def _db_path() -> str:
    return os.environ.get("SQLITE_EMAIL_DB", "data/emails.db")


def make_email_id(sender: str, subject: str, timestamp: str) -> str:
    """Derive a stable id for an email from its identifying fields."""
    raw = f"{sender}\x00{subject}\x00{timestamp}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


_SCHEMA = """
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    sender TEXT NOT NULL,
    subject TEXT,
    body TEXT,
    timestamp TEXT,
    html TEXT,
    status TEXT DEFAULT 'new',
    category TEXT,
    topic TEXT,
    priority TEXT,
    urgency_score INTEGER,
    summary TEXT,
    custom TEXT,
    draft TEXT,
    created_at TEXT,
    sent_at TEXT
)
"""

_ATTACHMENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY,
    email_id TEXT NOT NULL,
    cid TEXT,
    content_type TEXT,
    filename TEXT,
    data BLOB,
    UNIQUE(email_id, cid)
)
"""

_EMAIL_COLUMNS = "id, sender, subject, body, timestamp, html"

_CASE_COLUMNS = (
    f"{_EMAIL_COLUMNS}, status, category, topic, priority, urgency_score, "
    "summary, custom, draft, created_at, sent_at"
)


def _row_to_email(row: sqlite3.Row) -> dict[str, str]:
    return {
        "id": row["id"],
        "sender": row["sender"],
        "subject": row["subject"] or "",
        "body": row["body"] or "",
        "timestamp": row["timestamp"] or "",
        "html": row["html"] or "",
        "status": row["status"] or "new",
    }


def _row_to_case(row: sqlite3.Row) -> dict[str, Any]:
    custom_raw = row["custom"] or ""
    try:
        custom = json.loads(custom_raw) if custom_raw else {}
    except json.JSONDecodeError:
        custom = {}

    return {
        "id": row["id"],
        "email": _row_to_email(row),
        "classification": {
            "category": row["category"] or "unknown",
            "topic": row["topic"] or "",
            "priority": row["priority"] or "normal",
            "urgency_score": int(row["urgency_score"] or 0),
            "summary": row["summary"] or "",
            "custom": custom,
        },
        "draft": row["draft"] or "",
        "created_at": row["created_at"] or "",
        "sent_at": row["sent_at"] if row["sent_at"] is not None else None,
    }


class Database:
    """Handles all database operations for the email assistant."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()

    def _connect(self) -> sqlite3.Connection:
        path = self._db_path or _db_path()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute(_SCHEMA)
        conn.execute(_ATTACHMENTS_SCHEMA)
        try:
            conn.execute("ALTER TABLE emails ADD COLUMN html TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE emails ADD COLUMN sent_at TEXT")
        except sqlite3.OperationalError:
            pass
        conn.commit()
        return conn

    def upsert_email(self, email: dict) -> bool:
        """Insert an email if not already present. Returns True if newly added."""
        email_id = make_email_id(
            str(email.get("sender", "Unknown")),
            str(email.get("subject", "(no subject)")),
            str(email.get("timestamp", "")),
        )
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO emails
                        (id, sender, subject, body, timestamp, html)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        email_id,
                        email.get("sender", "Unknown"),
                        email.get("subject", "(no subject)"),
                        email.get("body", ""),
                        email.get("timestamp", ""),
                        email.get("html", ""),
                    ),
                )
                added = cur.rowcount > 0
                if added:
                    for att in email.get("attachments") or []:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO attachments
                                (email_id, cid, content_type, filename, data)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                email_id,
                                str(att.get("cid", "")),
                                str(att.get("content_type", "")),
                                str(att.get("filename", "")),
                                att.get("data") or b"",
                            ),
                        )
                conn.commit()
                return added
            finally:
                conn.close()

    def get_attachment(
        self, email_id: str, cid: str
    ) -> tuple[str, bytes] | None:
        """Return (content_type, data) for an inline attachment, or None."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT content_type, data FROM attachments "
                    "WHERE email_id = ? AND cid = ?",
                    (email_id, cid),
                ).fetchone()
            finally:
                conn.close()

        if row is None:
            return None
        return row["content_type"] or "application/octet-stream", row["data"]

    def list_emails(self) -> list[dict[str, str]]:
        """Return all stored emails, newest first."""
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    f"SELECT {_EMAIL_COLUMNS}, status FROM emails "
                    "ORDER BY timestamp DESC, rowid DESC"
                ).fetchall()
            finally:
                conn.close()
        return [_row_to_email(row) for row in rows]

    def get_email(self, email_id: str) -> dict[str, str] | None:
        """Return a single email by id, or None."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    f"SELECT {_EMAIL_COLUMNS}, status FROM emails WHERE id = ?",
                    (email_id,),
                ).fetchone()
            finally:
                conn.close()
        return _row_to_email(row) if row is not None else None

    def mark_processing(self, email_id: str) -> bool:
        """Mark an email as being processed. Returns True if the email exists."""
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "UPDATE emails SET status = 'processing' WHERE id = ?",
                    (email_id,),
                )
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()

    def mark_failed(self, email_id: str) -> bool:
        """Reset a processing email back to 'new' after a failure."""
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "UPDATE emails SET status = 'new' "
                    "WHERE id = ? AND status = 'processing'",
                    (email_id,),
                )
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()

    def list_pending_ids(self) -> list[str]:
        """Return ids of all emails that have not been processed yet."""
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT id FROM emails "
                    "WHERE status IN ('new', 'processing') "
                    "ORDER BY timestamp ASC, rowid ASC"
                ).fetchall()
            finally:
                conn.close()
        return [row["id"] for row in rows]

    def save_processing(
        self,
        email_id: str,
        classification: dict[str, Any],
        draft: str,
    ) -> dict[str, Any] | None:
        """Persist the classification and draft for an email. Returns the case."""
        created_at = datetime.now(timezone.utc).isoformat()
        custom_json = json.dumps(classification.get("custom") or {})

        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    """
                    UPDATE emails
                    SET status = 'processed',
                        category = ?,
                        topic = ?,
                        priority = ?,
                        urgency_score = ?,
                        summary = ?,
                        custom = ?,
                        draft = ?,
                        created_at = ?,
                        sent_at = NULL
                    WHERE id = ?
                    """,
                    (
                        classification.get("category", "unknown"),
                        classification.get("topic", ""),
                        classification.get("priority", "normal"),
                        int(classification.get("urgency_score", 0)),
                        classification.get("summary", ""),
                        custom_json,
                        draft,
                        created_at,
                        email_id,
                    ),
                )
                conn.commit()
                if cur.rowcount == 0:
                    return None

                row = conn.execute(
                    f"SELECT {_CASE_COLUMNS} FROM emails WHERE id = ?",
                    (email_id,),
                ).fetchone()
            finally:
                conn.close()

        return _row_to_case(row) if row is not None else None

    def get_case(self, email_id: str) -> dict[str, Any] | None:
        """Return a single processed case by email id, or None."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    f"SELECT {_CASE_COLUMNS} FROM emails "
                    "WHERE id = ? AND draft IS NOT NULL",
                    (email_id,),
                ).fetchone()
            finally:
                conn.close()
        return _row_to_case(row) if row is not None else None

    def save_draft(self, email_id: str, draft: str) -> dict[str, Any] | None:
        """Update only the draft text for a processed email."""
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "UPDATE emails SET draft = ? WHERE id = ? AND draft IS NOT NULL",
                    (draft, email_id),
                )
                conn.commit()
                if cur.rowcount == 0:
                    return None
                row = conn.execute(
                    f"SELECT {_CASE_COLUMNS} FROM emails WHERE id = ?",
                    (email_id,),
                ).fetchone()
            finally:
                conn.close()
        return _row_to_case(row) if row is not None else None

    def mark_sent(self, email_id: str) -> dict[str, Any] | None:
        """Mark a processed case as sent. Returns the updated case."""
        sent_at = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "UPDATE emails SET status = 'sent', sent_at = ? "
                    "WHERE id = ? AND draft IS NOT NULL",
                    (sent_at, email_id),
                )
                conn.commit()
                if cur.rowcount == 0:
                    return None
                row = conn.execute(
                    f"SELECT {_CASE_COLUMNS} FROM emails WHERE id = ?",
                    (email_id,),
                ).fetchone()
            finally:
                conn.close()
        return _row_to_case(row) if row is not None else None

    def list_cases(self) -> list[dict[str, Any]]:
        """Return all processed cases (emails with a draft), newest first."""
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    f"SELECT {_CASE_COLUMNS} "
                    "FROM emails WHERE draft IS NOT NULL "
                    "ORDER BY created_at DESC, rowid DESC"
                ).fetchall()
            finally:
                conn.close()
        return [_row_to_case(row) for row in rows]

    def clear(self) -> None:
        """Delete all rows (used by tests)."""
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM emails")
                conn.execute("DELETE FROM attachments")
                conn.commit()
            finally:
                conn.close()
