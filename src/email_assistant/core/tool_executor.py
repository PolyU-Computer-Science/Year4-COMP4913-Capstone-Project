"""MCP tool execution gateway (6C.5).

This is the *server-side authority* for tool execution. Before any external
call, it re-checks every permission (connector, mailbox assignment, tool,
schema, risk) — independent of what the LLM planner proposed. Executions are
audited, and results are normalised for the drafter.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from email_assistant.core.mcp_runtime import MCPClientManager
from email_assistant.core.observability_store import ObservabilityStore
from email_assistant.core.settings_store import SettingsStore
from email_assistant.core.tool_permissions import (
    DESTRUCTIVE,
    READ,
    WRITE,
    default_risk_level,
)


class ToolPermissionDenied(RuntimeError):
    """A tool call was rejected by the permission gateway."""


class ToolArgumentInvalid(RuntimeError):
    """Arguments failed validation against the tool's input schema."""


@dataclass
class ToolExecutionResult:
    ok: bool = False
    result: Any = None
    error: str | None = None
    denied: bool = False
    requires_approval: bool = False


class ToolExecutionGateway:
    """Authorizes and executes MCP tool calls with audit logging."""

    def __init__(
        self,
        manager: MCPClientManager | None = None,
        settings: SettingsStore | None = None,
        observability: ObservabilityStore | None = None,
    ) -> None:
        self._manager = manager or MCPClientManager()
        self._settings = settings or SettingsStore()
        self._observability = observability or ObservabilityStore()

    def execute(
        self,
        *,
        mailbox_id: int,
        connector_id: int,
        tool_name: str,
        arguments: dict,
        email_id: str | None = None,
        case_id: str | None = None,
        approved: bool = False,
    ) -> ToolExecutionResult:
        """Authorize and execute a tool call. Returns a result + audit log."""
        # 1. Connector exists and belongs to the mailbox.
        connector = self._find_mailbox_connector(mailbox_id, connector_id)
        if connector is None:
            return self._deny(mailbox_id, connector_id, tool_name, arguments,
                              email_id, case_id, "connector not enabled for mailbox")

        # 2. Tool is discovered and enabled for this mailbox.
        tool = self._find_tool(connector_id, tool_name)
        if tool is None:
            return self._deny(mailbox_id, connector_id, tool_name, arguments,
                              email_id, case_id, "tool not discovered")

        permission = self._settings.list_tool_permissions(mailbox_id, connector_id)
        perm = permission.get(tool_name)
        if perm is None or not perm.get("enabled"):
            return self._deny(mailbox_id, connector_id, tool_name, arguments,
                              email_id, case_id, "tool disabled for mailbox")

        # 3. Arguments validate against the tool's input schema.
        ok, error = _validate_arguments(tool.get("input_schema") or {}, arguments)
        if not ok:
            return self._deny(mailbox_id, connector_id, tool_name, arguments,
                              email_id, case_id, f"invalid arguments: {error}")

        # 4. Risk policy: write/destructive require human approval.
        risk = perm.get("permission_level") or tool.get("risk_level") or default_risk_level(tool_name)
        if risk in (WRITE, DESTRUCTIVE) and not approved:
            result = ToolExecutionResult(requires_approval=True)
            self._audit(mailbox_id, connector_id, tool_name, arguments,
                        email_id, case_id, status="needs_approval")
            return result

        # 5. Execute.
        try:
            raw = self._manager.execute_tool(connector, tool_name, arguments)
        except Exception as error:  # noqa: BLE001
            self._audit(mailbox_id, connector_id, tool_name, arguments,
                        email_id, case_id, status="failed",
                        error_type=type(error).__name__, error_message=str(error))
            return ToolExecutionResult(error=str(error))

        summary = _summarize_result(raw)
        self._audit(mailbox_id, connector_id, tool_name, arguments,
                    email_id, case_id, status="success", result_summary=summary)
        return ToolExecutionResult(ok=True, result=raw)

    # ---- helpers ----

    def _find_mailbox_connector(self, mailbox_id: int, connector_id: int) -> dict | None:
        for connector in self._settings.list_mailbox_connectors(mailbox_id):
            if connector["id"] == connector_id and connector.get("enabled"):
                return connector
        return None

    def _find_tool(self, connector_id: int, tool_name: str) -> dict | None:
        for tool in self._settings.list_connector_tools(connector_id):
            if tool["name"] == tool_name:
                return tool
        return None

    def _deny(
        self,
        mailbox_id: int,
        connector_id: int,
        tool_name: str,
        arguments: dict,
        email_id: str | None,
        case_id: str | None,
        reason: str,
    ) -> ToolExecutionResult:
        self._audit(mailbox_id, connector_id, tool_name, arguments,
                    email_id, case_id, status="denied",
                    error_type="ToolPermissionDenied", error_message=reason)
        return ToolExecutionResult(denied=True, error=reason)

    def _audit(
        self,
        mailbox_id: int,
        connector_id: int,
        tool_name: str,
        arguments: dict,
        email_id: str | None,
        case_id: str | None,
        *,
        status: str,
        result_summary: str = "",
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> None:
        try:
            self._observability.audit_tool_call(
                mailbox_id=mailbox_id,
                connector_id=connector_id,
                tool_name=tool_name,
                arguments=arguments,
                email_id=email_id,
                case_id=case_id,
                status=status,
                result_summary=result_summary,
                error_type=error_type,
                error_message=error_message,
            )
        except Exception:  # noqa: BLE001 - audit is best effort
            pass


def _validate_arguments(schema: dict, arguments: dict) -> tuple[bool, str]:
    """Validate arguments against a (subset of) JSON Schema."""
    if not isinstance(arguments, dict):
        return False, "arguments must be an object"

    properties = schema.get("properties") or {}
    required = schema.get("required") or []

    for key in required:
        if key not in arguments:
            return False, f"missing required argument: {key}"

    for key, value in arguments.items():
        prop = properties.get(key)
        if prop is None:
            continue
        type_ok, error = _check_type(prop, value)
        if not type_ok:
            return False, f"{key}: {error}"

    return True, ""


def _check_type(prop: dict, value: Any) -> tuple[bool, str]:
    expected = prop.get("type")
    if expected == "string":
        if not isinstance(value, str):
            return False, "expected string"
        if prop.get("minLength") is not None and len(value) < prop["minLength"]:
            return False, "string too short"
    elif expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, "expected number"
        if prop.get("minimum") is not None and value < prop["minimum"]:
            return False, "below minimum"
        if prop.get("maximum") is not None and value > prop["maximum"]:
            return False, "above maximum"
    elif expected == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return False, "expected integer"
    elif expected == "boolean":
        if not isinstance(value, bool):
            return False, "expected boolean"
    elif expected == "array":
        if not isinstance(value, list):
            return False, "expected array"
    elif expected == "object":
        if not isinstance(value, dict):
            return False, "expected object"
    return True, ""


def _summarize_result(raw: Any) -> str:
    try:
        text = json.dumps(raw, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(raw)
    return text[:500]
