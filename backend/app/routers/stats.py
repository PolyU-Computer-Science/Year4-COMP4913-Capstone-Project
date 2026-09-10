"""Dashboard statistics endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas import StatsOut
from backend.app.store import store

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats() -> StatsOut:
    """Return dashboard statistics computed from the case store."""
    return store.stats()
