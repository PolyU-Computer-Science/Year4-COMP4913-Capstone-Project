"""Tool permission enforcement.

Permissions are mailbox-scoped and default-deny. This is the *server-side*
authority: even if a tool is hidden from the LLM, execution is still checked
again here before any external call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

READ = "read"
WRITE = "write"
DESTRUCTIVE = "destructive"

PERMISSION_LEVELS = {READ, WRITE, DESTRUCTIVE}


@dataclass
class ToolPermission:
    tool_name: str
    enabled: bool = False
    permission_level: str = READ


class ToolPermissionService:
    """Filters tools visible to the LLM and authorizes execution."""

    def __init__(self, permissions: dict[str, ToolPermission] | None = None) -> None:
        # keyed by tool_name
        self._permissions = permissions or {}

    def set_permissions(self, permissions: dict[str, ToolPermission]) -> None:
        self._permissions = permissions

    def visible_tools(self, descriptors: list[Any]) -> list[Any]:
        """Return only the tools the LLM is allowed to see."""
        return [d for d in descriptors if self.is_allowed(d.name)]

    def is_allowed(self, tool_name: str) -> bool:
        permission = self._permissions.get(tool_name)
        if permission is None:
            # Default deny for unknown tools.
            return False
        return permission.enabled

    def authorize(self, tool_name: str) -> tuple[bool, str]:
        """Authorize an execution attempt. Returns (ok, reason)."""
        permission = self._permissions.get(tool_name)
        if permission is None:
            return False, f"Tool '{tool_name}' is not permitted"
        if not permission.enabled:
            return False, f"Tool '{tool_name}' is disabled"
        return True, ""


def default_risk_level(tool_name: str, description: str = "") -> str:
    """Heuristic risk level for a discovered tool name."""
    lowered = tool_name.lower()
    for keyword in ("delete", "remove", "destroy", "drop"):
        if keyword in lowered:
            return DESTRUCTIVE
    for keyword in ("create", "write", "update", "send", "modify", "set", "post"):
        if keyword in lowered:
            return WRITE
    return READ
