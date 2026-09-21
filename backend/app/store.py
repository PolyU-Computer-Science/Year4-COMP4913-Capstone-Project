"""Store for fetched emails and processed cases, backed by SQLite.

This replaces the earlier in-memory store so that fetched emails and processed
cases survive page navigation and backend restarts.
"""

from __future__ import annotations

from email_assistant.core.database import Database

from backend.app.schemas import (
    CaseOut,
    ClassificationOut,
    EmailItem,
    StatsOut,
)


class CaseStore:
    """SQLite-backed store for emails and processed cases."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db = Database(db_path)

    def sync_emails(
        self, raw_emails: list[dict], mailbox_id: int | None = None
    ) -> tuple[int, list[EmailItem]]:
        """Upsert raw fetched emails. Returns (newly added, all stored emails)."""
        added = 0
        for email in raw_emails:
            if mailbox_id is not None:
                email["mailbox_id"] = mailbox_id
            if self._db.upsert_email(email):
                added += 1
        return added, self.list_emails(mailbox_id)

    def list_emails(self, mailbox_id: int | None = None) -> list[EmailItem]:
        return [EmailItem(**email) for email in self._db.list_emails(mailbox_id)]

    def get_email(self, email_id: str) -> EmailItem | None:
        email = self._db.get_email(email_id)
        return EmailItem(**email) if email is not None else None

    def mark_processing(self, email_id: str) -> bool:
        return self._db.mark_processing(email_id)

    def mark_failed(self, email_id: str) -> bool:
        return self._db.mark_failed(email_id)

    def list_pending_ids(self, mailbox_id: int | None = None) -> list[str]:
        return self._db.list_pending_ids(mailbox_id)

    def get_attachment(
        self, email_id: str, cid: str
    ) -> tuple[str, bytes] | None:
        """Return (content_type, data) for an inline attachment."""
        return self._db.get_attachment(email_id, cid)

    def save_case(
        self,
        email_id: str,
        classification: ClassificationOut,
        draft: str,
    ) -> CaseOut | None:
        """Persist a processed email and return it as a case."""
        case = self._db.save_processing(
            email_id, classification.model_dump(), draft
        )
        return CaseOut(**case) if case is not None else None

    def get_cases(self, mailbox_id: int | None = None) -> list[CaseOut]:
        return [CaseOut(**case) for case in self._db.list_cases(mailbox_id)]

    def get_case(self, email_id: str) -> CaseOut | None:
        case = self._db.get_case(email_id)
        return CaseOut(**case) if case is not None else None

    def save_draft(self, email_id: str, draft: str) -> CaseOut | None:
        case = self._db.save_draft(email_id, draft)
        return CaseOut(**case) if case is not None else None

    def mark_sent(self, email_id: str) -> CaseOut | None:
        case = self._db.mark_sent(email_id)
        return CaseOut(**case) if case is not None else None

    def get_case_field_values(self, case_id: str) -> dict[int, str]:
        return self._db.get_case_field_values(case_id)

    def set_case_field_values(self, case_id: str, values: dict[int, str]) -> None:
        self._db.set_case_field_values(case_id, values)

    def fill_ai_case_field_values(self, case_id: str, values: dict[int, str]) -> None:
        """Fill AI-extracted values only into empty fields (protects manual)."""
        self._db.set_ai_case_field_values(case_id, values)

    def clear(self) -> None:
        """Reset the store (used by tests)."""
        self._db.clear()

    def backfill_missing_mailbox_ids(self, mailbox_id: int) -> int:
        """Assign legacy emails (NULL mailbox_id) to the given mailbox."""
        return self._db.backfill_missing_mailbox_ids(mailbox_id)

    def count_missing_mailbox_ids(self) -> int:
        """Number of emails still without a mailbox_id."""
        return self._db.count_missing_mailbox_ids()

    def stats(self, mailbox_id: int | None = None) -> StatsOut:
        emails = self._db.list_emails(mailbox_id)
        cases = self._db.list_cases(mailbox_id)

        total = len(emails)
        processed = len(cases)
        pending = max(total - processed, 0)
        success_rate = round((processed / total) * 100, 1) if total else 0.0

        category_counts: dict[str, int] = {}
        for case in cases:
            category = case["classification"]["category"]
            category_counts[category] = category_counts.get(category, 0) + 1

        category_distribution = [
            {"name": category.title(), "value": count}
            for category, count in category_counts.items()
        ]

        recent_activity = [
            {
                "email": case["email"]["subject"],
                "topic": case["classification"]["topic"],
                "category": case["classification"]["category"],
                "priority": case["classification"]["priority"],
                "status": "Processed",
                "time": case["created_at"],
            }
            for case in sorted(
                cases, key=lambda c: c["created_at"], reverse=True
            )[:10]
        ]

        return StatsOut(
            total_emails=total,
            processed=processed,
            pending=pending,
            success_rate=success_rate,
            category_distribution=category_distribution,
            recent_activity=recent_activity,
        )


store = CaseStore()
