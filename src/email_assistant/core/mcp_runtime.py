"""MCP connector tool model and client manager abstraction.

Connectors are discovered and invoked through a small abstraction so the
runtime never depends on a specific MCP transport. Permissions are enforced by
``tool_permissions`` — this module only handles discovery and execution; it
delegates authorization to the permission layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolDescriptor:
    connector_id: int
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    risk_level: str = "read"

    @property
    def canonical_name(self) -> str:
        # Namespaced to avoid collisions between connectors.
        return self.name


class MCPTransport(Protocol):
    """Transport for discovering and invoking tools on an MCP server."""

    def list_tools(self, server: str) -> list[dict[str, Any]]: ...

    def call_tool(self, server: str, tool_name: str, arguments: dict) -> Any: ...


class NoopTransport:
    """Default transport: returns no tools (connectors are not connected)."""

    def list_tools(self, server: str) -> list[dict[str, Any]]:
        return []

    def call_tool(self, server: str, tool_name: str, arguments: dict) -> Any:
        raise RuntimeError(f"Connector not connected: {server}")


class MCPClientManager:
    """Discovers and invokes MCP tools via a pluggable transport."""

    def __init__(self, transport: MCPTransport | None = None) -> None:
        self._transport = transport or NoopTransport()

    def discover_tools(self, connector: dict[str, Any]) -> list[ToolDescriptor]:
        server = str(connector.get("server") or "")
        raw_tools = self._transport.list_tools(server)
        return [
            ToolDescriptor(
                connector_id=int(connector["id"]),
                name=str(tool.get("name", "")),
                description=str(tool.get("description", "")),
                input_schema=tool.get("input_schema") or {},
                risk_level=str(tool.get("risk_level", "read")),
            )
            for tool in raw_tools
        ]

    def execute_tool(
        self, connector: dict[str, Any], tool_name: str, arguments: dict
    ) -> Any:
        server = str(connector.get("server") or "")
        return self._transport.call_tool(server, tool_name, arguments)
