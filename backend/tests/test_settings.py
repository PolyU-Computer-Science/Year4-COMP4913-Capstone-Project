"""Settings API and store tests (hermetic, tmp SQLite DB)."""

from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from email_assistant.core.settings_store import SettingsStore
from email_assistant.service import load_llm_settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def _tmp_settings_db(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_SETTINGS_DB", str(tmp_path / "settings.db"))
    monkeypatch.delenv("SETTINGS_ENCRYPTION_KEY", raising=False)
    yield tmp_path


# ---- SettingsStore unit tests (AI configs) ----

def _local_config(**overrides) -> dict:
    data = {
        "name": "Local Qwen",
        "provider": "local",
        "model": "test-model",
        "base_url": "http://localhost:11434/v1",
        "timeout": 120,
    }
    data.update(overrides)
    return data


def test_ai_config_api_key_encrypted_at_rest(tmp_path) -> None:
    db = tmp_path / "settings.db"
    store = SettingsStore(db_path=str(db))
    store.create_ai_config(_local_config(api_key="super-secret"))

    conn = sqlite3.connect(str(db))
    raw = conn.execute("SELECT api_key FROM ai_configs").fetchone()[0]
    conn.close()

    assert raw != "super-secret"
    assert store.get_ai_config(1, mask_secrets=False)["api_key"] == "super-secret"


def test_ai_config_masked_reading(tmp_path) -> None:
    store = SettingsStore(db_path=str(tmp_path / "settings.db"))
    store.create_ai_config(_local_config(api_key="super-secret"))

    data = store.get_ai_config(1, mask_secrets=True)
    assert data["api_key"] == ""
    assert data["has_api_key"] is True


def test_first_config_is_auto_active(tmp_path) -> None:
    store = SettingsStore(db_path=str(tmp_path / "settings.db"))
    config = store.create_ai_config(_local_config(enabled=False))

    assert config["enabled"] is True
    assert store.get_active_ai_config()["id"] == config["id"]


def test_single_active_enforced(tmp_path) -> None:
    store = SettingsStore(db_path=str(tmp_path / "settings.db"))
    first = store.create_ai_config(_local_config(name="First"))
    second = store.create_ai_config(_local_config(name="Second", enabled=True))

    assert store.get_active_ai_config()["id"] == second["id"]

    activated = store.set_active_ai_config(first["id"])
    assert activated is not None
    assert store.get_active_ai_config()["id"] == first["id"]
    assert store.get_ai_config(second["id"])["enabled"] is False


def test_stage_settings_roundtrip(tmp_path) -> None:
    store = SettingsStore(db_path=str(tmp_path / "settings.db"))
    store.set_stage_settings(
        "classification",
        {
            "role": "Classifier",
            "goal": "Categorize emails",
            "backstory": "Expert triage agent",
            "prompt": "Classify: {email_content}",
            "max_tokens": 300,
            "temperature": 0.1,
        },
    )

    data = store.get_stage_settings("classification")
    assert data["role"] == "Classifier"
    assert data["goal"] == "Categorize emails"
    assert data["prompt"] == "Classify: {email_content}"
    assert data["max_tokens"] == 300
    assert data["temperature"] == 0.1

    # unset fields return defaults
    assert store.get_stage_settings("draft")["max_tokens"] is None
    assert store.get_stage_settings("draft")["prompt"] == ""


# ---- SettingsStore unit tests (mail accounts) ----

def test_mail_password_encrypted_and_masked(tmp_path) -> None:
    store = SettingsStore(db_path=str(tmp_path / "settings.db"))
    account = store.create_mail_account(
        {"address": "a@b.com", "password": "pw123"}
    )

    assert account["password"] == ""
    assert account["has_password"] is True

    enabled = store.get_enabled_mail_account()
    assert enabled is not None
    assert enabled["password"] == "pw123"


def test_mail_update_blank_password_keeps_existing(tmp_path) -> None:
    store = SettingsStore(db_path=str(tmp_path / "settings.db"))
    account = store.create_mail_account(
        {"address": "a@b.com", "password": "pw123"}
    )

    updated = store.update_mail_account(account["id"], {"password": ""})
    assert updated is not None
    assert store.get_enabled_mail_account()["password"] == "pw123"


# ---- HTTP endpoint tests (AI configs) ----

def test_list_ai_configs_empty() -> None:
    response = client.get("/api/settings/ai")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_list_ai_config() -> None:
    created = client.post("/api/settings/ai", json=_local_config())
    assert created.status_code == 201
    assert created.json()["name"] == "Local Qwen"
    assert created.json()["has_api_key"] is False
    assert created.json()["enabled"] is True  # first config auto-active

    listed = client.get("/api/settings/ai")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_create_ai_rejects_missing_required_api_key() -> None:
    payload = {
        "name": "OpenAI",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
    }
    response = client.post("/api/settings/ai", json=payload)
    assert response.status_code == 422


def test_activate_ai_config() -> None:
    first = client.post(
        "/api/settings/ai", json=_local_config(name="First")
    ).json()
    second = client.post(
        "/api/settings/ai",
        json=_local_config(name="Second", enabled=True),
    ).json()

    assert second["enabled"] is True

    activated = client.post(f"/api/settings/ai/{first['id']}/activate")
    assert activated.status_code == 200
    assert activated.json()["enabled"] is True

    listed = client.get("/api/settings/ai").json()
    by_id = {c["id"]: c["enabled"] for c in listed}
    assert by_id[first["id"]] is True
    assert by_id[second["id"]] is False


def test_ai_test_endpoint_reports_failure_gracefully(monkeypatch) -> None:
    import backend.app.routers.settings as settings_router

    monkeypatch.setattr(
        settings_router,
        "create_llm",
        lambda settings: SimpleNamespace(
            call=lambda msg: (_ for _ in ()).throw(RuntimeError("cannot connect"))
        ),
    )

    response = client.post("/api/settings/ai/test", json=_local_config())
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "cannot connect" in response.json()["message"]


def test_stages_get_and_put() -> None:
    payload = {
        "classification": {
            "role": "Classifier",
            "goal": "Categorize",
            "backstory": "Expert",
            "prompt": "Classify: {email_content}",
            "max_tokens": 300,
            "temperature": 0.1,
        },
        "draft": {
            "role": "",
            "goal": "",
            "backstory": "",
            "prompt": "Write a reply",
            "max_tokens": 1000,
            "temperature": None,
        },
    }
    response = client.put("/api/settings/stages", json=payload)
    assert response.status_code == 200

    got = client.get("/api/settings/stages")
    assert got.status_code == 200
    body = got.json()
    assert body["classification"]["prompt"] == "Classify: {email_content}"
    assert body["classification"]["max_tokens"] == 300
    assert body["draft"]["prompt"] == "Write a reply"
    assert body["draft"]["max_tokens"] == 1000


# ---- HTTP endpoint tests (mail accounts) ----

def test_mail_crud_roundtrip() -> None:
    created = client.post(
        "/api/settings/mail",
        json={
            "address": "support@example.com",
            "imap_host": "imap.gmail.com",
            "imap_port": 993,
            "password": "secret-pass",
            "folder": "INBOX",
            "max_emails": 20,
            "enabled": True,
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["password"] == ""
    assert body["has_password"] is True
    account_id = body["id"]

    listed = client.get("/api/settings/mail")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    deleted = client.delete(f"/api/settings/mail/{account_id}")
    assert deleted.status_code == 200
    assert client.get("/api/settings/mail").json() == []


# ---- load_llm_settings fallback tests ----

def test_load_llm_settings_falls_back_to_env_when_no_active(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("LOCAL_MODEL", "env-model")
    monkeypatch.setenv("LOCAL_BASE_URL", "http://localhost:11434/v1")

    settings = load_llm_settings()
    assert settings.provider.value == "local"
    assert settings.model == "env-model"


def test_load_llm_settings_uses_active_config(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("LOCAL_MODEL", "env-model")
    monkeypatch.setenv("LOCAL_BASE_URL", "http://localhost:11434/v1")

    store = SettingsStore()
    store.create_ai_config(
        {
            "name": "DB Model",
            "provider": "local",
            "model": "db-model",
            "base_url": "http://localhost:11434/v1",
            "timeout": 90,
        }
    )

    settings = load_llm_settings()
    assert settings.model == "db-model"
    assert settings.timeout == 90


# ---- default config seeding tests ----

def test_ai_config_defaults_to_8000_tokens(tmp_path) -> None:
    store = SettingsStore(db_path=str(tmp_path / "settings.db"))
    config = store.create_ai_config(_local_config())

    assert config["max_tokens"] == 8000
    assert config["temperature"] == 0.2


def test_ensure_default_ai_config_seeds_once(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("LOCAL_MODEL", "env-model")
    monkeypatch.setenv("LOCAL_BASE_URL", "http://localhost:11434/v1")

    store = SettingsStore(db_path=str(tmp_path / "settings.db"))
    assert store.list_ai_configs() == []

    seeded = store.ensure_default_ai_config()
    assert seeded is not None
    assert seeded["name"] == "Default"
    assert seeded["enabled"] is True
    assert seeded["max_tokens"] == 8000

    # second call must not duplicate
    assert store.ensure_default_ai_config() is None
    assert len(store.list_ai_configs()) == 1


def test_ensure_default_ai_config_skips_when_env_invalid(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    store = SettingsStore(db_path=str(tmp_path / "settings.db"))
    assert store.ensure_default_ai_config() is None
    assert store.list_ai_configs() == []
