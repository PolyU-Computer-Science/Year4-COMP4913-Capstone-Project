#!/usr/bin/env python
"""Probe an MCP Streamable HTTP endpoint (6C.0).

Connects, initializes, and lists tools WITHOUT hardcoding tool names. Prints
server info, protocol version, capabilities, and the discovered tools with
their input schemas. Saves nothing and prints no secrets.

Usage:
    uv run python scripts/probe_mcp.py [url]

Default url: https://demo.solutionforest.net/mcp/mtr/
"""

from __future__ import annotations

import json
import sys


def main() -> None:
    from email_assistant.core.mcp_transport import StreamableHttpTransport

    url = sys.argv[1] if len(sys.argv) > 1 else "https://demo.solutionforest.net/mcp/mtr/"
    print(f"Probing MCP endpoint: {url}")

    transport = StreamableHttpTransport()
    try:
        tools = transport.list_tools(url)
    except Exception as error:  # noqa: BLE001
        print(f"\nPROBE FAILED: {type(error).__name__}: {error}")
        sys.exit(1)

    print(f"\nDiscovered {len(tools)} tool(s):")
    for tool in tools:
        print(f"\n- name        : {tool['name']}")
        print(f"  description : {tool['description']}")
        print(f"  inputSchema : {json.dumps(tool['input_schema'])}")
        if tool.get("annotations"):
            print(f"  annotations : {json.dumps(tool['annotations'])}")


if __name__ == "__main__":
    main()
