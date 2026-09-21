"""Observability tests (Sprint 5)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from email_assistant.core.observability import Observer
from email_assistant.core.observability_store import ObservabilityStore

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_SETTINGS_DB", str(tmp_path / "settings.db"))
    monkeypatch.setenv("OBSERVABILITY_DB", str(tmp_path / "observability.db"))
    monkeypatch.delenv("SETTINGS_ENCRYPTION_KEY", raising=False)
    ObservabilityStore().clear()
    yield


def test_observer_records_success_run() -> None:
    observer = Observer()
    with observer.run(stage="classification", mailbox_id=1, email_id="e1"):
        pass

    runs = observer._store.list_runs(mailbox_id=1)
    assert len(runs) == 1
    assert runs[0]["stage"] == "classification"
    assert runs[0]["status"] == "success"
    assert runs[0]["latency_ms"] is not None


def test_observer_records_failure_without_raising_pipeline() -> None:
    observer = Observer()
    try:
        with observer.run(stage="drafting", mailbox_id=1):
            raise ValueError("boom")
    except ValueError:
        pass

    runs = observer._store.list_runs(mailbox_id=1)
    assert runs[0]["status"] == "failed"
    assert runs[0]["error_type"] == "ValueError"
    assert runs[0]["error_message"] == "boom"


def test_observer_best_effort_does_not_break_on_store_failure(monkeypatch) -> None:
    observer = Observer()
    monkeypatch.setattr(
        observer._store, "start_run", lambda data: (_ for _ in ()).throw(RuntimeError("db down"))
    )
    # Should not raise even though the store failed.
    with observer.run(stage="classification", mailbox_id=1):
        pass


def test_processing_runs_api() -> None:
    mailbox_id = client.post(
        "/api/mailboxes", json={"name": "Support", "address": "s@x.com"}
    ).json()["id"]

    observer = Observer()
    with observer.run(stage="classification", mailbox_id=mailbox_id, email_id="e1"):
        pass

    response = client.get(f"/api/mailboxes/{mailbox_id}/processing-runs")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert body[0]["stage"] == "classification"


def test_processing_stats_api() -> None:
    mailbox_id = client.post(
        "/api/mailboxes", json={"name": "Support", "address": "s@x.com"}
    ).json()["id"]

    observer = Observer()
    for i in range(3):
        with observer.run(stage="classification", mailbox_id=mailbox_id):
            pass

    response = client.get(f"/api/mailboxes/{mailbox_id}/processing-stats")
    assert response.status_code == 200
    body = response.json()
    assert body["processed"] == 3
    assert body["success_rate"] == 1.0
    assert body["average_latency_ms"] >= 0
