"""Email fetching and processing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from backend.app.schemas import (
    CaseOut,
    ClassificationOut,
    EmailsResponse,
    ProcessResponse,
    SyncResponse,
)
from backend.app.store import store

router = APIRouter(prefix="/api/emails", tags=["emails"])


@router.get("", response_model=EmailsResponse)
def list_emails() -> EmailsResponse:
    """Return all stored emails (no side effects)."""
    emails = store.list_emails()
    return EmailsResponse(emails=emails, count=len(emails))


@router.post("/sync", response_model=SyncResponse)
def sync_emails() -> SyncResponse:
    """Fetch unread emails (IMAP) and persist them (deduped)."""
    from email_assistant.core import fetch_emails

    try:
        raw_emails = fetch_emails()
    except Exception as error:  # noqa: BLE001 - surface IMAP failures to the UI
        print(f"IMAP fetch failed: {error}")
        raise HTTPException(
            status_code=502, detail=f"IMAP fetch failed: {error}"
        ) from error

    added, emails = store.sync_emails(raw_emails)
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

    This endpoint is synchronous so FastAPI executes it in a worker thread,
    keeping the event loop free during the blocking CrewAI kickoff. The email
    status transitions new -> processing -> processed (reverted to new on
    failure so it can be retried).
    """
    from email_assistant.agents import EmailAssistant
    from email_assistant.core import format_email

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

    try:
        result = EmailAssistant().crew().kickoff(inputs={"email_content": content})
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

    case = store.save_case(email_id, classification, result.raw)
    if case is None:
        store.mark_failed(email_id)
        raise HTTPException(status_code=404, detail="Email not found")

    return ProcessResponse(case=case)


@router.post("/process-all", response_model=dict)
def process_all_emails() -> dict:
    """Queue-process all pending emails sequentially (one at a time).

    Synchronous so FastAPI runs it in a worker thread; each email's status
    transitions new -> processing -> processed (or back to new on failure).
    """
    pending = store.list_pending_ids()
    processed = 0
    failed: list[str] = []

    for email_id in pending:
        try:
            process_email(email_id)
            processed += 1
        except Exception:  # noqa: BLE001 - keep the queue running on failures
            failed.append(email_id)

    return {"queued": len(pending), "processed": processed, "failed": failed}
