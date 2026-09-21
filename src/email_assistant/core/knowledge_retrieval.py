"""Knowledge retrieval.

Mailbox-scoped semantic search over indexed chunks. Isolation is enforced by
filtering chunks on ``mailbox_id`` and only considering indexed documents from
enabled sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from email_assistant.core.embeddings import EmbeddingClient, cosine_similarity, get_embedding_client
from email_assistant.core.knowledge_store import KnowledgeStore


@dataclass
class RetrievalResult:
    chunk_id: int
    document_id: int
    source_id: int
    title: str
    content: str
    score: float
    metadata: dict[str, Any]


class KnowledgeRetriever:
    """Retrieves top-k mailbox-scoped chunks for a query."""

    def __init__(
        self,
        store: KnowledgeStore | None = None,
        embedding_client: EmbeddingClient | None = None,
    ) -> None:
        self._store = store or KnowledgeStore()
        self._embedding = embedding_client or get_embedding_client()

    def search(
        self,
        mailbox_id: int,
        query: str,
        top_k: int = 8,
        source_ids: list[int] | None = None,
        min_score: float | None = None,
    ) -> list[RetrievalResult]:
        """Search mailbox chunks by cosine similarity.

        Only chunks belonging to ``mailbox_id`` and whose document is indexed
        are considered. Chunks from other mailboxes are never returned.
        """
        if not query.strip():
            return []

        query_vector = self._embedding.embed_query(query)
        chunks = self._store.list_chunks(mailbox_id, source_ids)

        results: list[RetrievalResult] = []
        for chunk in chunks:
            if chunk.get("doc_status") != "indexed":
                continue
            embedding = chunk.get("embedding") or []
            if not embedding:
                continue
            score = cosine_similarity(query_vector, embedding)
            if min_score is not None and score < min_score:
                continue
            results.append(
                RetrievalResult(
                    chunk_id=int(chunk["id"]),
                    document_id=int(chunk["document_id"]),
                    source_id=int(chunk["source_id"]),
                    title=str(chunk.get("title") or ""),
                    content=str(chunk["content"]),
                    score=round(float(score), 4),
                    metadata=chunk.get("metadata") or {},
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
