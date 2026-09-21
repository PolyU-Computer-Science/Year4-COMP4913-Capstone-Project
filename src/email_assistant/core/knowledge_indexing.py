"""Knowledge indexing service.

Turns a knowledge source's content into mailbox-scoped chunks and embeddings.
Indexing is atomic: new chunks are only swapped in after all embeddings succeed,
so a failed embedding never destroys the previous index.
"""

from __future__ import annotations

import hashlib
from typing import Any

from email_assistant.core.chunking import chunk_text
from email_assistant.core.embeddings import EmbeddingClient, get_embedding_client
from email_assistant.core.knowledge_store import KnowledgeStore


def content_hash(content: str) -> str:
    """SHA-256 of normalized content, used to skip unchanged re-indexing."""
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


class KnowledgeIndexService:
    """Indexes knowledge source content into mailbox-scoped chunks."""

    def __init__(
        self,
        store: KnowledgeStore | None = None,
        embedding_client: EmbeddingClient | None = None,
    ) -> None:
        self._store = store or KnowledgeStore()
        self._embedding = embedding_client or get_embedding_client()

    def index_source(
        self,
        mailbox_id: int,
        source: dict[str, Any],
        *,
        external_id: str = "default",
        title: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Index a source's content. Returns status info.

        ``source`` must already be verified as belonging to ``mailbox_id`` by
        the caller. If the content hash is unchanged, indexing is skipped unless
        ``force`` is True.
        """
        content = str(source.get("content") or "")
        if not content.strip():
            return {
                "status": "failed",
                "error": "Knowledge source has no content to index",
                "document_id": None,
            }

        new_hash = content_hash(content)
        existing = self._store.get_document_by_external_id(
            mailbox_id, int(source["id"]), external_id
        )
        # Skip only when BOTH content and embedding identity are unchanged.
        embedding_unchanged = (
            existing is not None
            and existing.get("embedding_provider") == self._embedding.provider
            and existing.get("embedding_model") == self._embedding.model
            and int(existing.get("embedding_dim") or 0) == self._embedding.dim
        )
        if (
            existing is not None
            and existing.get("content_hash") == new_hash
            and embedding_unchanged
            and not force
        ):
            self._store.mark_document_indexed(existing["id"])
            return {
                "status": "indexed",
                "skipped": True,
                "document_id": existing["id"],
                "chunks": 0,
            }

        # Chunk the content.
        chunks = chunk_text(content)
        if not chunks:
            return {
                "status": "failed",
                "error": "No chunks produced",
                "document_id": None,
            }

        # Embed all chunks. On failure, the previous index is untouched.
        try:
            embeddings = self._embedding.embed_documents(
                [c.content for c in chunks]
            )
        except Exception as error:  # noqa: BLE001
            return {
                "status": "failed",
                "error": f"Embedding failed: {error}",
                "document_id": None,
            }

        # Upsert the document (with embedding identity).
        document_id = self._store.upsert_document(
            {
                "mailbox_id": mailbox_id,
                "source_id": int(source["id"]),
                "external_id": external_id,
                "title": title or str(source.get("name", "")),
                "content_hash": new_hash,
                "embedding_provider": self._embedding.provider,
                "embedding_model": self._embedding.model,
                "embedding_dim": self._embedding.dim,
                "status": "indexed",
            }
        )

        # Atomically replace chunks.
        chunk_rows = [
            {
                "index": c.index,
                "content": c.content,
                "token_count": c.token_count,
                "embedding": embeddings[c.index],
                "embedding_provider": self._embedding.provider,
                "embedding_model": self._embedding.model,
                "embedding_dim": self._embedding.dim,
                "metadata": c.metadata,
            }
            for c in chunks
        ]
        self._store.replace_chunks(mailbox_id, document_id, chunk_rows)
        self._store.mark_document_indexed(document_id)

        return {
            "status": "indexed",
            "document_id": document_id,
            "chunks": len(chunks),
        }

    def reindex_source(
        self, mailbox_id: int, source: dict[str, Any]
    ) -> dict[str, Any]:
        return self.index_source(mailbox_id, source, force=True)

    def delete_document(self, document_id: int) -> None:
        self._store.delete_document(document_id)

    def delete_source_documents(self, mailbox_id: int, source_id: int) -> None:
        self._store.delete_source_documents(mailbox_id, source_id)
