"""MCP connector discovery, permissions, and tool audit endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from email_assistant.core.mcp_runtime import MCPClientManager
from email_assistant.core.observability_store import ObservabilityStore
from email_assistant.core.settings_store import SettingsStore
from email_assistant.core.tool_permissions import default_risk_level

from backend.app.schemas import (
    ConnectorPermissionsIn,
    ToolAuditOut,
    ToolDescriptorOut,
)

router = APIRouter(prefix="/api/mailboxes", tags=["connectors"])


def _require_mailbox(mailbox_id: int) -> None:
    if SettingsStore().get_mailbox(mailbox_id) is None:
        raise HTTPException(status_code=404, detail="Mailbox not found")


def _require_mailbox_connector(mailbox_id: int, connector_id: int) -> dict:
    store = SettingsStore()
    connectors = store.list_mailbox_connectors(mailbox_id)
    for connector in connectors:
        if connector["id"] == connector_id:
            return connector
    raise HTTPException(
        status_code=404, detail="Connector not found for this mailbox"
    )


@router.post(
    "/{mailbox_id}/connectors/{connector_id}/discover",
    response_model=list[ToolDescriptorOut],
)
def discover_tools(mailbox_id: int, connector_id: int) -> list[ToolDescriptorOut]:
    _require_mailbox(mailbox_id)
    connector = _require_mailbox_connector(mailbox_id, connector_id)

    manager = MCPClientManager()
    tools = manager.discover_tools(connector)
    permissions = SettingsStore().list_tool_permissions(mailbox_id, connector_id)

    result = []
    for tool in tools:
        permission = permissions.get(tool.name)
        result.append(
            ToolDescriptorOut(
                connector_id=connector_id,
                name=tool.name,
                description=tool.description,
                risk_level=tool.risk_level or default_risk_level(tool.name),
                enabled=bool(permission["enabled"]) if permission else False,
                permission_level=(
                    permission["permission_level"] if permission else "read"
                ),
            )
        )
    return result


@router.get(
    "/{mailbox_id}/connectors/{connector_id}/tools",
    response_model=list[ToolDescriptorOut],
)
def list_tools(mailbox_id: int, connector_id: int) -> list[ToolDescriptorOut]:
    return discover_tools(mailbox_id, connector_id)


@router.put(
    "/{mailbox_id}/connectors/{connector_id}/permissions",
    response_model=dict,
)
def update_permissions(
    mailbox_id: int, connector_id: int, payload: ConnectorPermissionsIn
) -> dict:
    _require_mailbox(mailbox_id)
    _require_mailbox_connector(mailbox_id, connector_id)

    permissions = {
        p.tool_name: {
            "enabled": p.enabled,
            "permission_level": p.permission_level,
        }
        for p in payload.permissions
    }
    SettingsStore().set_tool_permissions(mailbox_id, connector_id, permissions)
    return {"ok": True}


@router.get("/{mailbox_id}/tool-audit", response_model=list[ToolAuditOut])
def list_tool_audit(mailbox_id: int) -> list[ToolAuditOut]:
    _require_mailbox(mailbox_id)
    logs = ObservabilityStore().list_audit_logs(mailbox_id)
    result = []
    for log in logs:
        result.append(
            ToolAuditOut(
                id=log["id"],
                mailbox_id=log["mailbox_id"],
                email_id=log["email_id"],
                case_id=log["case_id"],
                connector_id=log["connector_id"],
                tool_name=log["tool_name"],
                arguments_json_redacted=_parse_json(log.get("arguments_json_redacted")),
                status=log["status"],
                started_at=log["started_at"],
                completed_at=log["completed_at"],
                latency_ms=log["latency_ms"],
                result_summary=log["result_summary"] or "",
                error_type=log["error_type"],
                error_message=log["error_message"],
            )
        )
    return result


def _parse_json(raw: str | None) -> dict:
    if not raw:
        return {}
    import json

    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
