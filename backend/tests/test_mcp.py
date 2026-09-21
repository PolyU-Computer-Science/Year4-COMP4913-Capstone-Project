"""MCP tool permissions + runtime tests (Sprint 4)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from email_assistant.core.mcp_runtime import MCPClientManager, ToolDescriptor
from email_assistant.core.observability_store import ObservabilityStore
from email_assistant.core.settings_store import SettingsStore
from email_assistant.core.tool_permissions import (
    ToolPermission,
    ToolPermissionService,
    default_risk_level,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_SETTINGS_DB", str(tmp_path / "settings.db"))
    monkeypatch.setenv("OBSERVABILITY_DB", str(tmp_path / "observability.db"))
    monkeypatch.delenv("SETTINGS_ENCRYPTION_KEY", raising=False)
    ObservabilityStore().clear()
    yield


def test_default_risk_level_classification() -> None:
    assert default_risk_level("read_issue") == "read"
    assert default_risk_level("create_issue") == "write"
    assert default_risk_level("delete_file") == "destructive"


def test_permission_service_default_deny() -> None:
    service = ToolPermissionService()
    assert service.is_allowed("unknown_tool") is False
    ok, reason = service.authorize("unknown_tool")
    assert ok is False


def test_permission_service_allows_enabled() -> None:
    service = ToolPermissionService(
        {"crm.get_customer": ToolPermission("crm.get_customer", enabled=True)}
    )
    assert service.is_allowed("crm.get_customer") is True
    ok, _ = service.authorize("crm.get_customer")
    assert ok is True


def test_visible_tools_filters_denied() -> None:
    tools = [
        ToolDescriptor(connector_id=1, name="a.read", description="", risk_level="read"),
        ToolDescriptor(connector_id=1, name="b.write", description="", risk_level="write"),
    ]
    service = ToolPermissionService(
        {"a.read": ToolPermission("a.read", enabled=True)}
    )
    visible = service.visible_tools(tools)
    assert [t.name for t in visible] == ["a.read"]


class _FakeTransport:
    def __init__(self):
        self.calls = []

    def list_tools(self, server):
        return [
            {"name": "crm.get_customer", "description": "get", "risk_level": "read"},
            {"name": "crm.delete_customer", "description": "delete", "risk_level": "destructive"},
        ]

    def call_tool(self, server, tool_name, arguments):
        self.calls.append((tool_name, arguments))
        return {"ok": True}


def test_mcp_discovery_and_permissions_roundtrip() -> None:
    mailbox_id = client.post(
        "/api/mailboxes", json={"name": "Support", "address": "s@x.com"}
    ).json()["id"]
    connector = client.post(
        "/api/mailboxes/connectors", json={"name": "CRM", "type": "mcp", "server": "crm"}
    ).json()
    connector_id = connector["id"]
    client.put(
        f"/api/mailboxes/{mailbox_id}/connectors/{connector_id}",
        json={"enabled": True, "allowed_tools": ""},
    )

    # Discover tools (default NoopTransport -> no tools), then set permissions.
    discovered = client.post(
        f"/api/mailboxes/{mailbox_id}/connectors/{connector_id}/discover"
    ).json()
    assert discovered == []

    # Set a permission explicitly.
    client.put(
        f"/api/mailboxes/{mailbox_id}/connectors/{connector_id}/permissions",
        json={
            "permissions": [
                {"tool_name": "crm.get_customer", "enabled": True, "permission_level": "read"}
            ]
        },
    )
    perms = SettingsStore().list_tool_permissions(mailbox_id, connector_id)
    assert perms["crm.get_customer"]["enabled"] is True


def test_audit_log_redacts_secrets() -> None:
    store = ObservabilityStore()
    store.audit_tool_call(
        mailbox_id=1,
        connector_id=1,
        tool_name="crm.login",
        arguments={"username": "bob", "password": "supersecret", "api_token": "abc"},
        status="success",
    )
    logs = store.list_audit_logs(1)
    assert len(logs) == 1
    redacted = logs[0]["arguments_json_redacted"]
    assert "supersecret" not in redacted
    assert "abc" not in redacted


def test_mcp_manager_uses_transport() -> None:
    transport = _FakeTransport()
    manager = MCPClientManager(transport)
    connector = {"id": 1, "server": "crm"}
    tools = manager.discover_tools(connector)
    assert {t.name for t in tools} == {"crm.get_customer", "crm.delete_customer"}

    result = manager.execute_tool(connector, "crm.get_customer", {"id": 1})
    assert result == {"ok": True}
    assert transport.calls == [("crm.get_customer", {"id": 1})]
