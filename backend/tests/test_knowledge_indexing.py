"""Knowledge indexing / chunking / embedding tests (3A)."""

from __future__ import annotations

import pytest

from email_assistant.core.chunking import chunk_text
from email_assistant.core.embeddings import HashingEmbeddingClient, cosine_similarity
from email_assistant.core.knowledge_indexing import KnowledgeIndexService, content_hash
from email_assistant.core.knowledge_store import KnowledgeStore


@pytest.fixture(autouse=True)
def _tmp_knowledge_db(tmp_path, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_DB", str(tmp_path / "knowledge.db"))
    yield tmp_path


def test_chunk_generation_splits_long_text() -> None:
    text = " ".join(f"This is sentence number {i} about refunds." for i in range(100))
    chunks = chunk_text(text, target_tokens=50)
    assert len(chunks) > 1
    # Chunks are indexed sequentially.
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_chunk_short_text_single_chunk() -> None:
    chunks = chunk_text("A short refund policy.")
    assert len(chunks) == 1
    assert chunks[0].content == "A short refund policy."


def test_chunk_empty_returns_empty() -> None:
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_content_hash_stable() -> None:
    assert content_hash("  refund policy ") == content_hash("refund policy")


def test_embedding_is_deterministic_and_normalized() -> None:
    client = HashingEmbeddingClient()
    a = client.embed_query("refund policy")
    b = client.embed_query("refund policy")
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6


def test_cosine_similarity_same_text_high() -> None:
    client = HashingEmbeddingClient()
    a = client.embed_query("refund policy for 30 days")
    b = client.embed_query("refund policy for 30 days")
    assert cosine_similarity(a, b) > 0.9


def test_index_source_creates_chunks_with_mailbox_id() -> None:
    service = KnowledgeIndexService()
    source = {"id": 1, "name": "Refund Policy", "content": "Refund policy: 30 days."}
    result = service.index_source(3, source)
    assert result["status"] == "indexed"
    assert result["chunks"] >= 1

    store = KnowledgeStore()
    docs = store.list_documents(3)
    assert len(docs) == 1
    assert docs[0]["mailbox_id"] == 3
    assert docs[0]["status"] == "indexed"

    chunks = store.list_chunks(3)
    assert len(chunks) >= 1
    assert all(c["mailbox_id"] == 3 for c in chunks)
    assert all(len(c["embedding"]) > 0 for c in chunks)


def test_index_unchanged_content_skips(monkeypatch) -> None:
    service = KnowledgeIndexService()
    source = {"id": 1, "name": "Refund Policy", "content": "Refund policy: 30 days."}

    first = service.index_source(3, source)
    second = service.index_source(3, source)
    assert first["status"] == "indexed"
    assert second.get("skipped") is True
    assert second["chunks"] == 0

    # Only one document exists (no duplicates).
    assert len(KnowledgeStore().list_documents(3)) == 1


def test_index_changed_content_reindexes() -> None:
    service = KnowledgeIndexService()
    source = {"id": 1, "name": "Refund Policy", "content": "Refund policy: 30 days."}
    service.index_source(3, source)

    source["content"] = "Refund policy: 60 days now."
    result = service.index_source(3, source)
    assert result.get("skipped") is not True

    chunks = KnowledgeStore().list_chunks(3)
    joined = " ".join(c["content"] for c in chunks)
    assert "60 days" in joined


def test_failed_embedding_keeps_previous_index(monkeypatch) -> None:
    service = KnowledgeIndexService()
    source = {"id": 1, "name": "Refund Policy", "content": "Refund policy: 30 days."}
    service.index_source(3, source)
    before = KnowledgeStore().list_chunks(3)

    def boom(texts):
        raise RuntimeError("embedding down")

    service._embedding.embed_documents = boom  # type: ignore[method-assign]

    result = service.index_source(3, {"id": 1, "name": "Refund Policy", "content": "changed"})
    assert result["status"] == "failed"

    after = KnowledgeStore().list_chunks(3)
    assert [c["content"] for c in after] == [c["content"] for c in before]


def test_index_no_content_fails() -> None:
    service = KnowledgeIndexService()
    result = service.index_source(3, {"id": 1, "name": "Empty", "content": ""})
    assert result["status"] == "failed"


def test_delete_document_removes_chunks() -> None:
    service = KnowledgeIndexService()
    result = service.index_source(3, {"id": 1, "name": "X", "content": "some content"})
    doc_id = result["document_id"]

    store = KnowledgeStore()
    assert len(store.list_chunks(3)) >= 1
    store.delete_document(doc_id)
    assert store.list_chunks(3) == []
