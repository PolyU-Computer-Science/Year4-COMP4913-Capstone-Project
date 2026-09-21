"""SQLite store for knowledge documents and chunks.

Documents and chunks are mailbox-scoped: every chunk carries ``mailbox_id`` so
retrieval can filter by mailbox without relying on joins. Embeddings are stored
as JSON arrays and compared with Python cosine similarity (see
``knowledge_retrieval``).
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(override=False)


def _db_path() -> str:
    return os.environ.get("KNOWLEDGE_DB", "data/knowledge.db")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id INTEGER PRIMARY KEY,
    mailbox_id INTEGER NOT NULL,
    source_id INTEGER NOT NULL,
    external_id TEXT DEFAULT '',
    title TEXT DEFAULT '',
    mime_type TEXT DEFAULT 'text/plain',
    content_hash TEXT DEFAULT '',
    embedding_provider TEXT DEFAULT '',
    embedding_model TEXT DEFAULT '',
    embedding_dim INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT,
    indexed_at TEXT,
    UNIQUE(mailbox_id, source_id, external_id)
)
"""

_CHUNKS_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id INTEGER PRIMARY KEY,
    mailbox_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER DEFAULT 0,
    embedding_json TEXT DEFAULT '[]',
    embedding_provider TEXT DEFAULT '',
    embedding_model TEXT DEFAULT '',
    embedding_dim INTEGER DEFAULT 0,
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT,
    UNIQUE(document_id, chunk_index)
)
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class KnowledgeStore:
    """Persistent store for knowledge documents and chunks."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or _db_path()
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute(_SCHEMA)
        conn.execute(_CHUNKS_SCHEMA)
        conn.commit()
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        # Migration: add embedding identity columns for existing DBs.
        for column, col_type in (
            ("embedding_provider", "TEXT DEFAULT ''"),
            ("embedding_model", "TEXT DEFAULT ''"),
            ("embedding_dim", "INTEGER DEFAULT 0"),
        ):
            try:
                conn.execute(
                    f"ALTER TABLE knowledge_documents ADD COLUMN {column} {col_type}"
                )
            except sqlite3.OperationalError:
                pass
        conn.commit()
        conn.close()

    # ---- documents ----

    def get_document(self, document_id: int) -> dict[str, Any] | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM knowledge_documents WHERE id = ?",
                    (document_id,),
                ).fetchone()
            finally:
                conn.close()
        return dict(row) if row is not None else None

    def get_document_by_external_id(
        self, mailbox_id: int, source_id: int, external_id: str
    ) -> dict[str, Any] | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM knowledge_documents "
                    "WHERE mailbox_id = ? AND source_id = ? AND external_id = ?",
                    (mailbox_id, source_id, external_id),
                ).fetchone()
            finally:
                conn.close()
        return dict(row) if row is not None else None

    def list_documents(self, mailbox_id: int) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT * FROM knowledge_documents WHERE mailbox_id = ? ORDER BY id",
                    (mailbox_id,),
                ).fetchall()
            finally:
                conn.close()
        return [dict(row) for row in rows]

    def upsert_document(self, data: dict[str, Any]) -> int:
        """Insert or update a document. Returns the document id."""
        now = _now()
        mailbox_id = int(data["mailbox_id"])
        source_id = int(data["source_id"])
        external_id = str(data.get("external_id", ""))
        title = str(data.get("title", ""))
        mime_type = str(data.get("mime_type", "text/plain"))
        content_hash = str(data.get("content_hash", ""))
        status = str(data.get("status", "pending"))
        metadata_json = json.dumps(data.get("metadata") or {})

        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO knowledge_documents
                        (mailbox_id, source_id, external_id, title, mime_type,
                         content_hash, embedding_provider, embedding_model,
                         embedding_dim, status, metadata_json, created_at,
                         updated_at, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(mailbox_id, source_id, external_id) DO UPDATE SET
                        title = excluded.title,
                        mime_type = excluded.mime_type,
                        content_hash = excluded.content_hash,
                        embedding_provider = excluded.embedding_provider,
                        embedding_model = excluded.embedding_model,
                        embedding_dim = excluded.embedding_dim,
                        status = excluded.status,
                        metadata_json = excluded.metadata_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        mailbox_id,
                        source_id,
                        external_id,
                        title,
                        mime_type,
                        content_hash,
                        str(data.get("embedding_provider", "")),
                        str(data.get("embedding_model", "")),
                        int(data.get("embedding_dim", 0)),
                        status,
                        metadata_json,
                        now,
                        now,
                        None,
                    ),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT id FROM knowledge_documents "
                    "WHERE mailbox_id = ? AND source_id = ? AND external_id = ?",
                    (mailbox_id, source_id, external_id),
                ).fetchone()
            finally:
                conn.close()
        return int(row["id"])

    def mark_document_indexed(
        self, document_id: int, status: str = "indexed"
    ) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "UPDATE knowledge_documents SET status = ?, indexed_at = ? "
                    "WHERE id = ?",
                    (status, _now(), document_id),
                )
                conn.commit()
            finally:
                conn.close()

    def mark_document_failed(self, document_id: int, error: str) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "UPDATE knowledge_documents SET status = 'failed', "
                    "metadata_json = json_set(COALESCE(metadata_json, '{}'), "
                    "'$.error', ?) WHERE id = ?",
                    (error, document_id),
                )
                conn.commit()
            finally:
                conn.close()

    def delete_document(self, document_id: int) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "DELETE FROM knowledge_chunks WHERE document_id = ?",
                    (document_id,),
                )
                conn.execute(
                    "DELETE FROM knowledge_documents WHERE id = ?", (document_id,)
                )
                conn.commit()
            finally:
                conn.close()

    # ---- chunks ----

    def replace_chunks(
        self,
        mailbox_id: int,
        document_id: int,
        chunks: list[dict[str, Any]],
    ) -> None:
        """Atomically replace all chunks for a document."""
        now = _now()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "DELETE FROM knowledge_chunks WHERE document_id = ?",
                    (document_id,),
                )
                for chunk in chunks:
                    conn.execute(
                        """
                        INSERT INTO knowledge_chunks
                            (mailbox_id, document_id, chunk_index, content,
                             token_count, embedding_json, embedding_provider,
                             embedding_model, embedding_dim, metadata_json,
                             created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            mailbox_id,
                            document_id,
                            int(chunk["index"]),
                            str(chunk["content"]),
                            int(chunk.get("token_count", 0)),
                            json.dumps(chunk.get("embedding") or []),
                            str(chunk.get("embedding_provider", "")),
                            str(chunk.get("embedding_model", "")),
                            int(chunk.get("embedding_dim", 0)),
                            json.dumps(chunk.get("metadata") or {}),
                            now,
                        ),
                    )
                conn.commit()
            finally:
                conn.close()

    def list_chunks(
        self,
        mailbox_id: int,
        source_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                query = (
                    "SELECT c.*, d.source_id AS source_id, d.title AS title, "
                    "d.status AS doc_status "
                    "FROM knowledge_chunks c "
                    "JOIN knowledge_documents d ON d.id = c.document_id "
                    "WHERE c.mailbox_id = ?"
                )
                params: list[Any] = [mailbox_id]
                if source_ids:
                    placeholders = ",".join("?" for _ in source_ids)
                    query += f" AND d.source_id IN ({placeholders})"
                    params.extend(source_ids)
                rows = conn.execute(query, params).fetchall()
            finally:
                conn.close()

        result = []
        for row in rows:
            chunk = dict(row)
            chunk["embedding"] = json.loads(chunk.get("embedding_json") or "[]")
            chunk["metadata"] = json.loads(chunk.get("metadata_json") or "{}")
            result.append(chunk)
        return result

    def delete_source_documents(self, mailbox_id: int, source_id: int) -> None:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT id FROM knowledge_documents "
                    "WHERE mailbox_id = ? AND source_id = ?",
                    (mailbox_id, source_id),
                ).fetchall()
                for row in rows:
                    conn.execute(
                        "DELETE FROM knowledge_chunks WHERE document_id = ?",
                        (row["id"],),
                    )
                conn.execute(
                    "DELETE FROM knowledge_documents "
                    "WHERE mailbox_id = ? AND source_id = ?",
                    (mailbox_id, source_id),
                )
                conn.commit()
            finally:
                conn.close()

    def clear(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM knowledge_chunks")
                conn.execute("DELETE FROM knowledge_documents")
                conn.commit()
            finally:
                conn.close()
