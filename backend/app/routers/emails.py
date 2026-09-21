"""Email fetching and processing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

from backend.app.schemas import (
    CaseOut,
    ClassificationOut,
    EmailsResponse,
    ProcessResponse,
    SyncResponse,
)
from backend.app.store import store

router = APIRouter(prefix="/api/emails", tags=["emails"])


class SyncIn(BaseModel):
    """Optional payload for sync — target a single mailbox, or all."""

    mailbox_id: int | None = None


@router.get("", response_model=EmailsResponse)
def list_emails(
    mailbox_id: int | None = Query(default=None),
) -> EmailsResponse:
    """Return stored emails, optionally scoped to a single mailbox."""
    emails = store.list_emails(mailbox_id)
    return EmailsResponse(emails=emails, count=len(emails))


@router.post("/sync", response_model=SyncResponse)
def sync_emails(payload: SyncIn | None = None) -> SyncResponse:
    """Fetch unread emails (IMAP) and persist them (deduped)."""
    from email_assistant.core import fetch_emails

    mailbox_id = payload.mailbox_id if payload else None
    try:
        if mailbox_id is None:
            raw_emails = fetch_emails()
        else:
            raw_emails = fetch_emails(mailbox_id)
    except Exception as error:  # noqa: BLE001 - surface IMAP failures to the UI
        print(f"IMAP fetch failed: {error}")
        raise HTTPException(
            status_code=502, detail=f"IMAP fetch failed: {error}"
        ) from error

    added, emails = store.sync_emails(raw_emails, mailbox_id)
    return SyncResponse(synced=added, emails=emails, count=len(emails))


@router.get("/{email_id}/attachments/{cid}")
def get_attachment(email_id: str, cid: str) -> Response:
    """Serve an inline email attachment (e.g. a ``cid:`` image)."""
    attachment = store.get_attachment(email_id, cid)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    content_type, data = attachment
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": "inline"},
    )


@router.post("/{email_id}/process", response_model=ProcessResponse)
def process_email(email_id: str) -> ProcessResponse:
    """Run the AI crew (classify + draft) on a stored email by id.

    The pipeline is mailbox-scoped: the mailbox's topics constrain the
    classifier, and its indexed knowledge grounds the drafter (RAG). Each
    stage is traced via the observer for latency/usage.
    """
    import uuid

    from email_assistant.agents import EmailAssistant
    from email_assistant.core import format_email
    from email_assistant.core.knowledge_retrieval import KnowledgeRetriever
    from email_assistant.core.mailbox_context import load_mailbox_context
    from email_assistant.core.observability import Observer
    from email_assistant.core.rag import build_retrieval_query, format_knowledge_context
    from email_assistant.core.topics import (
        format_topics_prompt,
        resolve_topic,
    )

    email = store.get_email(email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Email not found")

    store.mark_processing(email_id)

    content = format_email(
        {
            "sender": email.sender,
            "subject": email.subject,
            "timestamp": email.timestamp,
            "body": email.body,
        }
    )

    # Load the mailbox's business context (topics, fields, knowledge, tools).
    context = load_mailbox_context(email.mailbox_id) if email.mailbox_id else None
    available_topics = (
        format_topics_prompt(context.topics) if context else ""
    )

    trace_id = uuid.uuid4().hex
    observer = Observer()

    # 1. Knowledge retrieval (mailbox-scoped RAG). Best-effort: a retrieval
    #    failure or zero results never blocks drafting.
    knowledge_context = ""
    knowledge_refs: list[dict] = []
    if context and context.knowledge_sources and context.mailbox.get("use_knowledge"):
        try:
            with observer.run(
                stage="knowledge_retrieval",
                mailbox_id=email.mailbox_id,
                email_id=email_id,
                trace_id=trace_id,
            ):
                query = build_retrieval_query(
                    subject=email.subject,
                    body=email.body,
                )
                results = KnowledgeRetriever().search(
                    email.mailbox_id, query, top_k=5
                )
                knowledge_context = format_knowledge_context(results)
                knowledge_refs = [
                    {
                        "chunk_id": r.chunk_id,
                        "source_id": r.source_id,
                        "score": r.score,
                    }
                    for r in results
                ]
        except Exception:  # noqa: BLE001 - RAG must not block processing
            knowledge_context = ""

    # 2. Classifier + Drafter (single CrewAI sequential crew).
    try:
        with observer.run(
            stage="email_processing",
            mailbox_id=email.mailbox_id,
            email_id=email_id,
            trace_id=trace_id,
        ):
            result = EmailAssistant().crew().kickoff(
                inputs={
                    "email_content": content,
                    "available_topics": available_topics,
                    "knowledge_context": knowledge_context or "(no knowledge available)",
                }
            )
    except Exception:
        store.mark_failed(email_id)
        raise

    classification = None
    if result.pydantic is not None:
        classification = ClassificationOut(**result.pydantic.model_dump())
    else:
        from email_assistant.core.classification_parser import (
            parse_classification,
        )

        tasks_output = getattr(result, "tasks_output", None) or []
        if tasks_output:
            parsed = parse_classification(tasks_output[0].raw or "")
            if parsed is not None:
                classification = ClassificationOut(**parsed.model_dump())

    if classification is None:
        store.mark_failed(email_id)
        raise HTTPException(
            status_code=422,
            detail=(
                "Classification failed: the model did not return a valid "
                "structured result. Check your LLM configuration (max_tokens) "
                "and retry."
            ),
        )

    # Resolve the free-form topic against the mailbox's configured topics.
    topic_id, canonical = resolve_topic(
        context.topics if context else [], classification.topic
    )
    classification.topic_id = topic_id
    classification.topic_raw = classification.topic
    if canonical:
        classification.topic = canonical

    case = store.save_case(email_id, classification, result.raw)
    if case is None:
        store.mark_failed(email_id)
        raise HTTPException(status_code=404, detail="Email not found")

    # 3. AI field extraction (structured, mailbox-scoped, partial success).
    if context and context.active_fields:
        from email_assistant.core.extraction import ClassificationExtractionClient
        from email_assistant.core.extraction_service import (
            ExtractionService,
            outcome_to_values_json,
        )

        client = ClassificationExtractionClient(
            classification.topic, classification.custom
        )
        extraction_service = ExtractionService(client)
        try:
            with observer.run(
                stage="field_extraction",
                mailbox_id=email.mailbox_id,
                email_id=email_id,
                trace_id=trace_id,
            ):
                outcome = extraction_service.extract(
                    content, context.topics, context.active_fields
                )
            values = outcome_to_values_json(outcome)
            if values:
                store.fill_ai_case_field_values(email_id, values)
        except Exception:  # noqa: BLE001 - extraction failure must not block
            pass

    # Record retrieval provenance on the run for observability/debugging.
    if knowledge_refs:
        try:
            runs = observer._store.list_runs(
                mailbox_id=email.mailbox_id, email_id=email_id, limit=1
            )
            if runs:
                observer._store.finish_run(
                    runs[0]["id"],
                    metadata={"knowledge_chunk_ids": [r["chunk_id"] for r in knowledge_refs]},
                )
        except Exception:  # noqa: BLE001 - best effort
            pass

    return ProcessResponse(case=case)


@router.post("/process-all", response_model=dict)
def process_all_emails(
    mailbox_id: int | None = Query(default=None),
) -> dict:
    """Queue-process all pending emails sequentially (one at a time).

    Synchronous so FastAPI runs it in a worker thread; each email's status
    transitions new -> processing -> processed (or back to new on failure).
    """
    pending = store.list_pending_ids(mailbox_id)
    processed = 0
    failed: list[str] = []

    for email_id in pending:
        try:
            process_email(email_id)
            processed += 1
        except Exception:  # noqa: BLE001 - keep the queue running on failures
            failed.append(email_id)

    return {"queued": len(pending), "processed": processed, "failed": failed}
