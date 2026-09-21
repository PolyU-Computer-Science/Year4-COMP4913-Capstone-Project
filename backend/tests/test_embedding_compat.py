"""Embedding compatibility safety tests (6A)."""

from __future__ import annotations

import pytest

from email_assistant.core.embeddings import (
    EmbeddingClient,
    EmbeddingConfig,
    EmbeddingDimensionMismatch,
    cosine_similarity,
    embeddings_compatible,
)
from email_assistant.core.knowledge_indexing import KnowledgeIndexService
from email_assistant.core.knowledge_retrieval import KnowledgeRetriever
from email_assistant.core.knowledge_store import KnowledgeStore


@pytest.fixture(autouse=True)
def _tmp_knowledge_db(tmp_path, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_DB", str(tmp_path / "knowledge.db"))
    yield tmp_path


class _FakeEmbedding(EmbeddingClient):
    def __init__(self, provider: str, model: str, dim: int) -> None:
        self.provider = provider
        self.model = model
        self.dim = dim

    def embed_documents(self, texts):
        return [self._embed(t) for t in texts]

    def embed_query(self, text):
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for i, ch in enumerate(text):
            vector[i % self.dim] += ord(ch)
        return vector


def test_embeddings_compatible_same_identity() -> None:
    a = EmbeddingConfig("hashing", "hashing", 256)
    b = EmbeddingConfig("hashing", "hashing", 256)
    assert embeddings_compatible(a, b) is True


def test_embeddings_incompatible_on_model_change() -> None:
    a = EmbeddingConfig("hashing", "hashing", 256)
    b = EmbeddingConfig("hashing", "nomic-embed", 256)
    assert embeddings_compatible(a, b) is False


def test_embeddings_incompatible_on_provider_change() -> None:
    a = EmbeddingConfig("hashing", "hashing", 256)
    b = EmbeddingConfig("openai", "hashing", 256)
    assert embeddings_compatible(a, b) is False


def test_embeddings_incompatible_on_dimension_change() -> None:
    a = EmbeddingConfig("hashing", "hashing", 256)
    b = EmbeddingConfig("hashing", "hashing", 512)
    assert embeddings_compatible(a, b) is False


def test_cosine_similarity_rejects_dimension_mismatch() -> None:
    with pytest.raises(EmbeddingDimensionMismatch):
        cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])


def test_model_change_triggers_reindex() -> None:
    store = KnowledgeStore()
    service = KnowledgeIndexService(
        store, embedding_client=_FakeEmbedding("hashing", "hashing", 64)
    )
    source = {"id": 1, "name": "KB", "content": "Refund policy 30 days."}
    first = service.index_source(3, source)
    assert first.get("skipped") is not True

    # Change the embedding model — reindex must happen, not skip.
    service2 = KnowledgeIndexService(
        store, embedding_client=_FakeEmbedding("ollama", "nomic-embed", 128)
    )
    second = service2.index_source(3, source)
    assert second.get("skipped") is not True
    assert second["status"] == "indexed"

    # Document now carries the new embedding identity.
    docs = store.list_documents(3)
    assert docs[0]["embedding_model"] == "nomic-embed"
    assert docs[0]["embedding_dim"] == 128


def test_same_model_and_content_skips() -> None:
    store = KnowledgeStore()
    client = _FakeEmbedding("hashing", "hashing", 64)
    service = KnowledgeIndexService(store, embedding_client=client)
    source = {"id": 1, "name": "KB", "content": "Refund policy 30 days."}

    service.index_source(3, source)
    second = service.index_source(3, source)
    assert second.get("skipped") is True


def test_retrieval_skips_stale_embedding_chunks() -> None:
    store = KnowledgeStore()
    # Index with model A.
    service = KnowledgeIndexService(
        store, embedding_client=_FakeEmbedding("hashing", "hashing", 64)
    )
    service.index_source(3, {"id": 1, "name": "KB", "content": "Refund policy 30 days."})

    # Retrieval with a different model B returns nothing (stale index skipped).
    retriever = KnowledgeRetriever(
        store, embedding_client=_FakeEmbedding("ollama", "nomic-embed", 128)
    )
    results = retriever.search(3, "refund policy")
    assert results == []

    # Retrieval with the same model A works.
    retriever = KnowledgeRetriever(
        store, embedding_client=_FakeEmbedding("hashing", "hashing", 64)
    )
    assert len(retriever.search(3, "refund policy")) >= 1


def test_failed_reindex_keeps_previous_index() -> None:
    store = KnowledgeStore()
    service = KnowledgeIndexService(
        store, embedding_client=_FakeEmbedding("hashing", "hashing", 64)
    )
    service.index_source(3, {"id": 1, "name": "KB", "content": "Refund policy 30 days."})

    def boom(texts):
        raise RuntimeError("embedding down")

    service._embedding.embed_documents = boom  # type: ignore[method-assign]
    result = service.index_source(3, {"id": 1, "name": "KB", "content": "changed"})
    assert result["status"] == "failed"

    # Previous chunks remain intact.
    assert len(store.list_chunks(3)) >= 1
