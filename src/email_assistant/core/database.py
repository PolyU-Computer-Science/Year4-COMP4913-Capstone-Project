"""Database layer for persisting emails, classifications, and drafts.

Currently a placeholder — will be expanded with SQLite operations
in future phases.
"""

from __future__ import annotations


class Database:
    """Handles all database operations for the email assistant."""

    def __init__(self, db_path: str = "data/emails.db") -> None:
        self.db_path = db_path

    def init_db(self) -> None:
        """Initialize the database schema."""
        pass  # TODO: Create tables

    def save_email(self, email_data: dict) -> None:
        """Save a fetched email to the database."""
        pass  # TODO: Insert email record

    def save_classification(
        self, email_id: str, classification: dict
    ) -> None:
        """Save the classification result for an email."""
        pass  # TODO: Insert classification record

    def save_draft(self, email_id: str, draft: str, approved: bool = False) -> None:
        """Save an AI-generated draft reply."""
        pass  # TODO: Insert draft record
