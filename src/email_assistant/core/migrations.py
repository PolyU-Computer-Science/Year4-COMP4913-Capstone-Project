"""Data migrations for mailbox context boundary.

Legacy emails predate the ``mailbox_id`` column and therefore have NULL
values. This module provides an idempotent migration that assigns those rows
to a dedicated "Legacy" mailbox so that no email is silently orphaned.
"""

from __future__ import annotations

from email_assistant.core.settings_store import SettingsStore

LEGACY_MAILBOX_NAME = "Legacy"


def migrate_legacy_emails() -> int:
    """Backfill NULL-mailbox emails into a "Legacy" mailbox.

    Returns the number of emails migrated. Idempotent: if no emails are
    missing a mailbox, it does nothing.
    """
    from backend.app.store import store

    missing = store.count_missing_mailbox_ids()
    if missing == 0:
        return 0

    settings = SettingsStore()
    mailbox = settings.get_mailbox_by_name(LEGACY_MAILBOX_NAME)
    if mailbox is None:
        mailbox = settings.create_mailbox(
            {
                "name": LEGACY_MAILBOX_NAME,
                "address": "",
                "purpose": "Migrated emails without original mailbox metadata",
                "is_system": True,
            }
        )
    elif not mailbox.get("is_system"):
        # Mark an existing (pre-flag) legacy mailbox as a system mailbox.
        settings.update_mailbox(
            int(mailbox["id"]), {"is_system": True}
        )
        mailbox = settings.get_mailbox(int(mailbox["id"]))

    return store.backfill_missing_mailbox_ids(int(mailbox["id"]))
