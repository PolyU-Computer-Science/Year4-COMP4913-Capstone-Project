#!/usr/bin/env python
"""Manual smoke test for OpenRouter structured output (NOT run in CI).

Reads OPENROUTER_API_KEY from ``.env`` and runs one classification through the
structured client to verify the MiMo runtime contract works. Never prints the
API key and never writes results to a committed file.

Usage:
    uv run python scripts/smoke_structured_llm.py
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv(override=False)


def _banner(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> None:
    from email_assistant.core.structured_classification import StructuredClassifier
    from email_assistant.core.structured_llm import build_openrouter_structured_client

    _banner("Config")
    try:
        client = build_openrouter_structured_client()
    except Exception as error:  # noqa: BLE001
        print(f"FAILED to build client: {error}")
        return
    print(f"model   : {client.model}")
    print(f"base_url: {client._base_url}")
    print("api_key : <set>" if client._api_key else "api_key : <missing>")

    topics = [
        {"id": 1, "name": "Refund", "status": "active"},
        {"id": 2, "name": "Password Reset", "status": "active"},
    ]

    _banner("Structured classification")
    try:
        outcome = StructuredClassifier(client).classify(
            "I bought the product last week and want to request a refund.",
            topics,
        )
        print(f"category          : {outcome.category}")
        print(f"topic             : {outcome.topic}")
        print(f"topic_resolved    : {outcome.topic_resolved}")
        print(f"priority          : {outcome.priority}")
        print(f"urgency_score     : {outcome.urgency_score}")
        print(f"summary           : {outcome.summary}")
        print(f"structured_valid  : {outcome.structured_valid}")
        print(f"repair_attempted  : {outcome.repair_attempted}")
        print(f"returned_model    : {outcome.returned_model}")
        print(f"tokens (in/out)   : {outcome.prompt_tokens}/{outcome.completion_tokens}")
        print(f"latency_ms        : {outcome.latency_ms}")
        print("PASS" if outcome.structured_valid else "FAIL")
    except Exception as error:  # noqa: BLE001
        print(f"FAILED: {error}")
        return

    _banner("Done")
    print("Structured LLM smoke test complete.")


if __name__ == "__main__":
    main()
