#!/usr/bin/env python
"""Manual smoke test for the MTR MCP connector (NOT run in CI).

Discovers tools from the live MTR MCP server and executes a couple of read-only
queries (station lookup + next trains) to verify the runtime path end-to-end.

Usage:
    uv run python scripts/smoke_mcp_mtr.py
"""

from __future__ import annotations

import json

MTR_URL = "https://demo.solutionforest.net/mcp/mtr/"


def _banner(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> None:
    from email_assistant.core.mcp_transport import StreamableHttpTransport

    transport = StreamableHttpTransport()

    _banner("Discovery")
    try:
        tools = transport.list_tools(MTR_URL)
    except Exception as error:  # noqa: BLE001
        print(f"FAILED to discover: {error}")
        return
    names = [t["name"] for t in tools]
    print(f"discovered {len(tools)} tools: {names}")

    _banner("Station lookup (mtr_get_station)")
    try:
        result = transport.call_tool(MTR_URL, "mtr_get_station", {"station": "ADM"})
        text = _extract_text(result)
        print(text[:400])
    except Exception as error:  # noqa: BLE001
        print(f"FAILED: {error}")

    _banner("Next trains (mtr_next_trains)")
    try:
        result = transport.call_tool(MTR_URL, "mtr_next_trains", {"station": "ADM"})
        text = _extract_text(result)
        print(text[:400])
    except Exception as error:  # noqa: BLE001
        print(f"FAILED: {error}")

    _banner("Journey planning (mtr_plan_route)")
    try:
        result = transport.call_tool(
            MTR_URL, "mtr_plan_route", {"from": "Kowloon Tong", "to": "Admiralty"}
        )
        text = _extract_text(result)
        print(text[:400])
    except Exception as error:  # noqa: BLE001
        print(f"FAILED: {error}")

    _banner("Done")
    print("MTR MCP smoke test complete.")


def _extract_text(result) -> str:
    if isinstance(result, dict) and result.get("content"):
        parts = []
        for block in result["content"]:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(parts)
    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    main()
