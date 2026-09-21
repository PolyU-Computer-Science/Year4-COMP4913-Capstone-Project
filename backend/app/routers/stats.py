"""Dashboard statistics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.schemas import StatsOut
from backend.app.store import store

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats(
    mailbox_id: int | None = Query(default=None),
) -> StatsOut:
    """Return dashboard statistics, optionally scoped to a single mailbox."""
    return store.stats(mailbox_id)
