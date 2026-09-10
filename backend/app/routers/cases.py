"""Processed cases endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.schemas import CaseOut, CasesResponse, DraftIn
from backend.app.store import store

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("", response_model=CasesResponse)
def list_cases() -> CasesResponse:
    """Return all processed cases (newest first)."""
    cases = store.get_cases()
    return CasesResponse(cases=cases, count=len(cases))


@router.patch("/{case_id}", response_model=CaseOut)
def update_case_draft(case_id: str, payload: DraftIn) -> CaseOut:
    """Update the draft reply of a processed case."""
    case = store.save_draft(case_id, payload.draft)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.post("/{case_id}/send", response_model=CaseOut)
def send_case(case_id: str) -> CaseOut:
    """Send the approved draft via SMTP and mark the case as sent."""
    from email_assistant.core.email_sender import send_reply
    from email_assistant.core.settings_store import SettingsStore

    case = store.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    if not case.draft.strip():
        raise HTTPException(status_code=422, detail="Draft is empty")

    account = SettingsStore().get_enabled_mail_account()
    if account is None:
        raise HTTPException(
            status_code=400, detail="No enabled mail account configured"
        )

    try:
        send_reply(
            account,
            to=case.email.sender,
            subject=case.email.subject,
            body=case.draft,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001 - report SMTP failures to the UI
        raise HTTPException(status_code=502, detail=f"SMTP error: {error}") from error

    sent = store.mark_sent(case_id)
    if sent is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return sent
