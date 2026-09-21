"""RAG drafting helpers tests (3C)."""

from __future__ import annotations

from email_assistant.core.knowledge_retrieval import RetrievalResult
from email_assistant.core.rag import build_retrieval_query, format_knowledge_context


def test_build_retrieval_query_includes_signals() -> None:
    query = build_retrieval_query(
        subject="Unable to reset password",
        body="I cannot log in to my account.",
        topic="Account Access",
        fields={"product": "Premium"},
    )
    assert "Unable to reset password" in query
    assert "Account Access" in query
    assert "product: Premium" in query
    assert "I cannot log in" in query


def test_build_retrieval_query_skips_empty_fields() -> None:
    query = build_retrieval_query(subject="S", body="B", topic="", fields={"x": None, "y": ""})
    assert "Topic:" not in query
    assert "Fields:" not in query


def test_format_knowledge_context_labelled() -> None:
    results = [
        RetrievalResult(
            chunk_id=7, document_id=2, source_id=1, title="Refund Policy",
            content="Refunds accepted within 30 days.", score=0.9, metadata={},
        ),
        RetrievalResult(
            chunk_id=8, document_id=2, source_id=1, title="Refund Policy",
            content="Contact support for exceptions.", score=0.8, metadata={},
        ),
    ]
    context = format_knowledge_context(results)
    assert "[KB1]" in context
    assert "[KB2]" in context
    assert "Source: Refund Policy" in context
    assert "Refunds accepted within 30 days." in context


def test_format_knowledge_context_empty() -> None:
    assert format_knowledge_context([]) == ""
