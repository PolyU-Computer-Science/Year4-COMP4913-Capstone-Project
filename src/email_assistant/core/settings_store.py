"""SQLite-backed settings store with Fernet-encrypted secrets.

Stores:
- ``ai_configs`` — multiple LLM configurations, one marked active.
- ``settings`` — global per-stage settings (system prompt, task prompt,
  generation params) for the ``classification`` and ``draft`` stages.
- ``mail_accounts`` — IMAP mail accounts.

Environment variables remain the defaults; values saved here override them at
runtime. API keys and mail passwords are encrypted with Fernet before being
written to disk.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv(override=False)

STAGES = ("classification", "draft")
STAGE_FIELDS = ("role", "goal", "backstory", "prompt", "max_tokens", "temperature")

SECRETS_DIR_FILENAME = ".secret_key"


def _db_path() -> str:
    return os.environ.get("SQLITE_SETTINGS_DB", "data/settings.db")


def _load_encryption_key() -> bytes:
    """Return the Fernet key from env, else a persisted key file."""
    from_env = os.environ.get("SETTINGS_ENCRYPTION_KEY", "").strip()
    if from_env:
        return from_env.encode()

    data_dir = Path(_db_path()).parent
    data_dir.mkdir(parents=True, exist_ok=True)
    secret_file = data_dir / SECRETS_DIR_FILENAME

    if secret_file.exists():
        return secret_file.read_text().strip().encode()

    key = Fernet.generate_key().decode()
    secret_file.write_text(key)
    return key.encode()


class SettingsStore:
    """Persistent store for AI configs, stage settings, and mail accounts."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or _db_path()
        self._lock = threading.Lock()
        self._fernet = Fernet(_load_encryption_key())
        self._init_db()

    # ---- infrastructure ----

    def _connect(self) -> sqlite3.Connection:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS settings "
                    "(key TEXT PRIMARY KEY, value TEXT)"
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ai_configs (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        model TEXT NOT NULL,
                        base_url TEXT,
                        api_key TEXT,
                        timeout REAL,
                        max_tokens INTEGER,
                        temperature REAL,
                        enabled INTEGER DEFAULT 0
                    )
                    """
                )
                for column, col_type in (("max_tokens", "INTEGER"), ("temperature", "REAL")):
                    try:
                        conn.execute(
                            f"ALTER TABLE ai_configs ADD COLUMN {column} {col_type}"
                        )
                    except sqlite3.OperationalError:
                        pass
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mail_accounts (
                        id INTEGER PRIMARY KEY,
                        address TEXT NOT NULL,
                        imap_host TEXT,
                        imap_port INTEGER,
                        smtp_host TEXT,
                        smtp_port INTEGER,
                        password TEXT,
                        folder TEXT DEFAULT 'INBOX',
                        max_emails INTEGER DEFAULT 50,
                        enabled INTEGER DEFAULT 1
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def _encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def _decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()

    # ---- AI configs ----

    def _ai_row_to_dict(
        self, row: sqlite3.Row, mask_secrets: bool
    ) -> dict[str, Any]:
        account = dict(row)
        account["enabled"] = bool(account["enabled"])
        account["max_tokens"] = int(account.get("max_tokens") or 8000)
        account["temperature"] = float(account.get("temperature") or 0.2)
        encrypted = account.get("api_key") or ""
        if mask_secrets:
            account["api_key"] = ""
            account["has_api_key"] = bool(encrypted)
        elif encrypted:
            account["api_key"] = self._decrypt(encrypted)
        return account

    def list_ai_configs(self, mask_secrets: bool = True) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT * FROM ai_configs ORDER BY id"
                ).fetchall()
            finally:
                conn.close()

        return [
            self._ai_row_to_dict(row, mask_secrets) for row in rows
        ]

    def get_ai_config(
        self, config_id: int, mask_secrets: bool = True
    ) -> dict[str, Any] | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM ai_configs WHERE id = ?", (config_id,)
                ).fetchone()
            finally:
                conn.close()

        if row is None:
            return None
        return self._ai_row_to_dict(row, mask_secrets)

    def get_active_ai_config(self) -> dict[str, Any] | None:
        """Return the active config with a decrypted api key."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM ai_configs WHERE enabled = 1 "
                    "ORDER BY id LIMIT 1"
                ).fetchone()
            finally:
                conn.close()

        if row is None:
            return None
        return self._ai_row_to_dict(row, mask_secrets=False)

    def _deactivate_all(self, conn: sqlite3.Connection) -> None:
        conn.execute("UPDATE ai_configs SET enabled = 0")

    def create_ai_config(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            conn = self._connect()
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM ai_configs"
                ).fetchone()[0]
                enabled = 1 if (data.get("enabled") or count == 0) else 0
                if enabled:
                    self._deactivate_all(conn)

                password = str(data.get("api_key") or "")
                encrypted = self._encrypt(password) if password else ""
                cur = conn.execute(
                    """
                    INSERT INTO ai_configs
                        (name, provider, model, base_url, api_key,
                         timeout, max_tokens, temperature, enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(data.get("name", "")),
                        str(data.get("provider", "")),
                        str(data.get("model", "")),
                        str(data.get("base_url", "")),
                        encrypted,
                        float(data.get("timeout", 120)),
                        int(data.get("max_tokens", 8000)),
                        float(data.get("temperature", 0.2)),
                        enabled,
                    ),
                )
                config_id = cur.lastrowid
                conn.commit()
            finally:
                conn.close()

        config = self.get_ai_config(config_id)  # type: ignore[arg-type]
        assert config is not None
        return config

    def update_ai_config(
        self, config_id: int, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        existing = self.get_ai_config(config_id, mask_secrets=False)
        if existing is None:
            return None

        merged = {**existing, **data}
        if str(data.get("api_key") or "") == "":
            merged["api_key"] = existing["api_key"]  # keep existing

        with self._lock:
            conn = self._connect()
            try:
                if merged.get("enabled"):
                    self._deactivate_all(conn)
                password = str(merged.get("api_key") or "")
                encrypted = self._encrypt(password) if password else ""
                conn.execute(
                    """
                    UPDATE ai_configs
                    SET name = ?, provider = ?, model = ?, base_url = ?,
                        api_key = ?, timeout = ?, max_tokens = ?,
                        temperature = ?, enabled = ?
                    WHERE id = ?
                    """,
                    (
                        str(merged.get("name", "")),
                        str(merged.get("provider", "")),
                        str(merged.get("model", "")),
                        str(merged.get("base_url", "")),
                        encrypted,
                        float(merged.get("timeout", 120)),
                        int(merged.get("max_tokens", 8000)),
                        float(merged.get("temperature", 0.2)),
                        1 if merged.get("enabled") else 0,
                        config_id,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        return self.get_ai_config(config_id)

    def delete_ai_config(self, config_id: int) -> bool:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "DELETE FROM ai_configs WHERE id = ?", (config_id,)
                )
                conn.commit()
            finally:
                conn.close()
        return cur.rowcount > 0  # type: ignore[possibly-undefined]

    def set_active_ai_config(self, config_id: int) -> dict[str, Any] | None:
        if self.get_ai_config(config_id) is None:
            return None

        with self._lock:
            conn = self._connect()
            try:
                self._deactivate_all(conn)
                conn.execute(
                    "UPDATE ai_configs SET enabled = 1 WHERE id = ?",
                    (config_id,),
                )
                conn.commit()
            finally:
                conn.close()

        return self.get_ai_config(config_id)

    def ensure_default_ai_config(self) -> dict[str, Any] | None:
        """Seed a default AI config from env when none exist. Returns it, or None."""
        with self._lock:
            conn = self._connect()
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM ai_configs"
                ).fetchone()[0]
            finally:
                conn.close()

        if count > 0:
            return None

        from email_assistant.service import LLMSettings

        try:
            settings = LLMSettings.from_env()
        except Exception:
            return None

        api_key = settings.api_key.get_secret_value() if settings.api_key else ""
        return self.create_ai_config(
            {
                "name": "Default",
                "provider": settings.provider.value,
                "model": settings.model,
                "base_url": settings.base_url or "",
                "api_key": api_key,
                "timeout": settings.timeout,
                "max_tokens": settings.max_tokens,
                "temperature": settings.temperature,
                "enabled": True,
            }
        )

    # ---- stage settings ----

    def get_stage_settings(self, stage: str) -> dict[str, Any]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT key, value FROM settings WHERE key LIKE ?",
                    (f"stage.{stage}.%",),
                ).fetchall()
            finally:
                conn.close()

        prefix = f"stage.{stage}."
        raw = {row["key"][len(prefix):]: row["value"] for row in rows}

        result: dict[str, Any] = {
            "role": "",
            "goal": "",
            "backstory": "",
            "prompt": "",
            "max_tokens": None,
            "temperature": None,
        }
        for field in ("role", "goal", "backstory", "prompt"):
            result[field] = raw.get(field, "")
        if raw.get("max_tokens", ""):
            result["max_tokens"] = int(raw["max_tokens"])
        if raw.get("temperature", ""):
            result["temperature"] = float(raw["temperature"])
        return result

    def set_stage_settings(self, stage: str, data: dict[str, Any]) -> None:
        with self._lock:
            conn = self._connect()
            try:
                for field in STAGE_FIELDS:
                    if field not in data:
                        continue
                    value = data[field]
                    key = f"stage.{stage}.{field}"
                    if value is None or (isinstance(value, str) and not value.strip()):
                        conn.execute(
                            "DELETE FROM settings WHERE key = ?", (key,)
                        )
                        continue
                    conn.execute(
                        "INSERT INTO settings (key, value) VALUES (?, ?) "
                        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                        (key, str(value)),
                    )
                conn.commit()
            finally:
                conn.close()

    # ---- mail accounts ----

    def list_mail_accounts(self, mask_secrets: bool = True) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT * FROM mail_accounts ORDER BY id"
                ).fetchall()
            finally:
                conn.close()

        accounts = []
        for row in rows:
            account = dict(row)
            account["enabled"] = bool(account["enabled"])
            encrypted = account.get("password") or ""
            if mask_secrets:
                account["password"] = ""
                account["has_password"] = bool(encrypted)
            elif encrypted:
                account["password"] = self._decrypt(encrypted)
            accounts.append(account)
        return accounts

    def get_mail_account(
        self, account_id: int, mask_secrets: bool = True
    ) -> dict[str, Any] | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM mail_accounts WHERE id = ?", (account_id,)
                ).fetchone()
            finally:
                conn.close()

        if row is None:
            return None

        account = dict(row)
        account["enabled"] = bool(account["enabled"])
        encrypted = account.get("password") or ""
        if mask_secrets:
            account["password"] = ""
            account["has_password"] = bool(encrypted)
        elif encrypted:
            account["password"] = self._decrypt(encrypted)
        return account

    def get_enabled_mail_account(self) -> dict[str, Any] | None:
        """Return the first enabled mail account with a decrypted password."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM mail_accounts WHERE enabled = 1 ORDER BY id LIMIT 1"
                ).fetchone()
            finally:
                conn.close()

        if row is None:
            return None

        account = dict(row)
        account["enabled"] = bool(account["enabled"])
        encrypted = account.get("password") or ""
        account["password"] = self._decrypt(encrypted) if encrypted else ""
        return account

    def create_mail_account(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            conn = self._connect()
            try:
                password = str(data.get("password") or "")
                encrypted = self._encrypt(password) if password else ""
                cur = conn.execute(
                    """
                    INSERT INTO mail_accounts
                        (address, imap_host, imap_port, smtp_host, smtp_port,
                         password, folder, max_emails, enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(data.get("address", "")),
                        str(data.get("imap_host", "")),
                        int(data.get("imap_port", 993)),
                        str(data.get("smtp_host", "")),
                        int(data.get("smtp_port", 587)),
                        encrypted,
                        str(data.get("folder", "INBOX") or "INBOX"),
                        int(data.get("max_emails", 50)),
                        1 if data.get("enabled", True) else 0,
                    ),
                )
                account_id = cur.lastrowid
                conn.commit()
            finally:
                conn.close()

        account = self.get_mail_account(account_id)  # type: ignore[arg-type]
        assert account is not None
        return account

    def update_mail_account(
        self, account_id: int, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        existing = self.get_mail_account(account_id, mask_secrets=False)
        if existing is None:
            return None

        merged = {**existing, **data}
        if str(data.get("password") or "") == "":
            merged["password"] = existing["password"]  # keep existing

        with self._lock:
            conn = self._connect()
            try:
                password = str(merged.get("password") or "")
                encrypted = self._encrypt(password) if password else ""
                conn.execute(
                    """
                    UPDATE mail_accounts
                    SET address = ?, imap_host = ?, imap_port = ?,
                        smtp_host = ?, smtp_port = ?, password = ?,
                        folder = ?, max_emails = ?, enabled = ?
                    WHERE id = ?
                    """,
                    (
                        str(merged.get("address", "")),
                        str(merged.get("imap_host", "")),
                        int(merged.get("imap_port", 993)),
                        str(merged.get("smtp_host", "")),
                        int(merged.get("smtp_port", 587)),
                        encrypted,
                        str(merged.get("folder", "INBOX") or "INBOX"),
                        int(merged.get("max_emails", 50)),
                        1 if merged.get("enabled", True) else 0,
                        account_id,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        return self.get_mail_account(account_id)

    def delete_mail_account(self, account_id: int) -> bool:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "DELETE FROM mail_accounts WHERE id = ?", (account_id,)
                )
                conn.commit()
            finally:
                conn.close()
        return cur.rowcount > 0  # type: ignore[possibly-undefined]
