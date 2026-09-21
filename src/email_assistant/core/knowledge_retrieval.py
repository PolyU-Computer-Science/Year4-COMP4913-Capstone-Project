"""Knowledge retrieval.

Mailbox-scoped semantic search over indexed chunks. Isolation is enforced by
filtering chunks on ``mailbox_id`` and only considering indexed documents from
enabled sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from email_assistant.core.embeddings import (
    EmbeddingClient,
    EmbeddingConfig,
    cosine_similarity,
    embeddings_compatible,
    get_embedding_client,
)
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


@dataclass
class RetrievalStats:
    """Counters for observability: how many chunks were considered/skipped."""

    chunks_considered: int = 0
    stale_chunks_skipped: int = 0
    returned_count: int = 0


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
        """Search mailbox chunks by cosine similarity (see ``search_detailed``)."""
        results, _ = self.search_detailed(
            mailbox_id, query, top_k, source_ids, min_score
        )
        return results

    def search_detailed(
        self,
        mailbox_id: int,
        query: str,
        top_k: int = 8,
        source_ids: list[int] | None = None,
        min_score: float | None = None,
    ) -> tuple[list[RetrievalResult], RetrievalStats]:
        """Search mailbox chunks, returning (results, stats).

        Only chunks belonging to ``mailbox_id`` and whose document is indexed
        are considered. Chunks from other mailboxes are never returned. Chunks
        whose embedding identity (provider/model/dim) does not match the
        current client are skipped (counted in ``stale_chunks_skipped``).
        """
        stats = RetrievalStats()
        if not query.strip():
            return [], stats

        query_vector = self._embedding.embed_query(query)
        chunks = self._store.list_chunks(mailbox_id, source_ids)
        stats.chunks_considered = len(chunks)

        results: list[RetrievalResult] = []
        for chunk in chunks:
            if chunk.get("doc_status") != "indexed":
                continue
            embedding = chunk.get("embedding") or []
            if not embedding:
                continue
            indexed_config = EmbeddingConfig(
                provider=str(chunk.get("embedding_provider") or ""),
                model=str(chunk.get("embedding_model") or ""),
                dim=int(chunk.get("embedding_dim") or 0),
            )
            if not embeddings_compatible(indexed_config, self._embedding.config):
                # Stale index under a different embedding model — skip.
                stats.stale_chunks_skipped += 1
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
        results = results[:top_k]
        stats.returned_count = len(results)
        return results, stats
