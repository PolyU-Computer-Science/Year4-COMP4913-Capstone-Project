"""Observability endpoints: processing runs and stats."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query

from email_assistant.core.observability_store import ObservabilityStore
from email_assistant.core.settings_store import SettingsStore

from backend.app.schemas import ProcessingRunOut

router = APIRouter(prefix="/api/mailboxes", tags=["observability"])


def _run_out(run: dict) -> ProcessingRunOut:
    return ProcessingRunOut(
        id=run["id"],
        trace_id=run["trace_id"],
        mailbox_id=run["mailbox_id"],
        email_id=run["email_id"],
        case_id=run["case_id"],
        stage=run["stage"],
        status=run["status"],
        provider=run["provider"],
        model=run["model"],
        started_at=run["started_at"],
        completed_at=run["completed_at"],
        latency_ms=run["latency_ms"],
        input_tokens=run["input_tokens"],
        output_tokens=run["output_tokens"],
        total_tokens=run["total_tokens"],
        metadata=_parse_json(run.get("metadata_json")),
        error_type=run["error_type"],
        error_message=run["error_message"],
    )


@router.get("/{mailbox_id}/processing-runs", response_model=list[ProcessingRunOut])
def list_processing_runs(
    mailbox_id: int,
    email_id: str | None = Query(default=None),
    stage: str | None = Query(default=None),
    limit: int = Query(default=100),
) -> list[ProcessingRunOut]:
    if SettingsStore().get_mailbox(mailbox_id) is None:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    runs = ObservabilityStore().list_runs(
        mailbox_id=mailbox_id, email_id=email_id, stage=stage, limit=limit
    )
    return [_run_out(r) for r in runs]


@router.get("/{mailbox_id}/processing-stats", response_model=dict)
def processing_stats(mailbox_id: int) -> dict:
    if SettingsStore().get_mailbox(mailbox_id) is None:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    runs = ObservabilityStore().list_runs(mailbox_id=mailbox_id, limit=10000)

    total = len(runs)
    succeeded = sum(1 for r in runs if r["status"] == "success")
    latencies = [r["latency_ms"] for r in runs if r["latency_ms"] is not None]
    tokens = sum(r["total_tokens"] or 0 for r in runs)

    return {
        "processed": total,
        "success_rate": round(succeeded / total, 4) if total else 0.0,
        "average_latency_ms": round(sum(latencies) / len(latencies), 1)
        if latencies
        else 0.0,
        "total_tokens": tokens,
    }


def _parse_json(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
