"""Pytest configuration: ensure the settings DB is hermetic per test."""

import pytest


@pytest.fixture(autouse=True)
def _hermetic_settings_db(tmp_path, monkeypatch):
    """Point the stores at temp DBs so tests never touch data/."""
    monkeypatch.setenv("SQLITE_EMAIL_DB", str(tmp_path / "emails.db"))
    monkeypatch.setenv("SQLITE_SETTINGS_DB", str(tmp_path / "settings.db"))
    monkeypatch.delenv("SETTINGS_ENCRYPTION_KEY", raising=False)
