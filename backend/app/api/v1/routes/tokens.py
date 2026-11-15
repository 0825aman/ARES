"""tokens.py — Token Tracking & Telemetry endpoints.

Exposes comprehensive token utilization statistics, multi-agent breakdowns,
timeline series, real-world research equivalents, and pictograph data.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services import token_service

router = APIRouter()


@router.get("/summary")
async def get_token_summary(db: AsyncSession = Depends(get_db)):
    """Return aggregated token metrics, agent distributions, timelines, and pictograph data."""
    return await token_service.get_token_summary(db)


@router.post("/backfill")
async def backfill_tokens(db: AsyncSession = Depends(get_db)):
    """Backfill zero-token historical runs with event-based estimates."""
    count = await token_service.backfill_zero_token_runs(db)
    return {"status": "ok", "runs_backfilled": count}
