"""Knowledge indexing and retrieval endpoints (mailbox-scoped)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from email_assistant.core.knowledge_indexing import KnowledgeIndexService
from email_assistant.core.knowledge_retrieval import KnowledgeRetriever
from email_assistant.core.knowledge_store import KnowledgeStore
from email_assistant.core.settings_store import SettingsStore

from backend.app.schemas import (
    KnowledgeDocumentOut,
    KnowledgeIndexResult,
    RetrievalEmbeddingOut,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResultOut,
    RetrievalStatsOut,
)

router = APIRouter(prefix="/api/mailboxes", tags=["knowledge"])


def _require_mailbox(mailbox_id: int) -> None:
    if SettingsStore().get_mailbox(mailbox_id) is None:
        raise HTTPException(status_code=404, detail="Mailbox not found")


def _require_assigned_source(mailbox_id: int, source_id: int) -> dict:
    store = SettingsStore()
    source = store.get_knowledge_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    assigned = {s["id"] for s in store.list_mailbox_knowledge(mailbox_id)}
    if source_id not in assigned:
        raise HTTPException(
            status_code=400, detail="Knowledge source does not belong to this mailbox"
        )
    return source


@router.post(
    "/{mailbox_id}/knowledge/sources/{source_id}/index",
    response_model=KnowledgeIndexResult,
)
def index_source(mailbox_id: int, source_id: int) -> KnowledgeIndexResult:
    _require_mailbox(mailbox_id)
    source = _require_assigned_source(mailbox_id, source_id)

    if source.get("status") == "disabled":
        return KnowledgeIndexResult(
            status="failed", error="Source is disabled"
        )

    result = KnowledgeIndexService().index_source(mailbox_id, source)
    return KnowledgeIndexResult(**result)


@router.get(
    "/{mailbox_id}/knowledge/sources/{source_id}/documents",
    response_model=list[KnowledgeDocumentOut],
)
def list_documents(mailbox_id: int, source_id: int) -> list[KnowledgeDocumentOut]:
    _require_mailbox(mailbox_id)
    _require_assigned_source(mailbox_id, source_id)
    documents = [
        d for d in KnowledgeStore().list_documents(mailbox_id) if d["source_id"] == source_id
    ]
    return [KnowledgeDocumentOut(**d) for d in documents]


@router.post(
    "/{mailbox_id}/knowledge/search",
    response_model=RetrievalResponse,
)
def search_knowledge(mailbox_id: int, payload: RetrievalRequest) -> RetrievalResponse:
    _require_mailbox(mailbox_id)
    retriever = KnowledgeRetriever()
    results, stats = retriever.search_detailed(
        mailbox_id,
        payload.query,
        top_k=payload.top_k,
        source_ids=payload.source_ids,
    )
    return RetrievalResponse(
        query=payload.query,
        embedding=RetrievalEmbeddingOut(
            provider=retriever._embedding.provider,
            model=retriever._embedding.model,
            dim=retriever._embedding.dim,
        ),
        stats=RetrievalStatsOut(
            top_k=payload.top_k,
            chunks_considered=stats.chunks_considered,
            stale_chunks_skipped=stats.stale_chunks_skipped,
            returned_count=stats.returned_count,
            source_count=stats.source_count,
            latency_ms=stats.latency_ms,
            max_score=stats.max_score,
            min_returned_score=stats.min_returned_score,
        ),
        results=[
            RetrievalResultOut(
                source_id=r.source_id,
                source_name=r.title,
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                chunk_index=r.chunk_index,
                score=r.score,
                content=r.content,
                metadata=r.metadata,
            )
            for r in results
        ],
    )
