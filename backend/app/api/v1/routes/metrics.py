"""metrics.py — Operational metrics endpoint for ARES (Autonomous Research & Evidence System).

Exposes in-process operational metrics (run counts, LLM call counts, export counts, HTTP request counts)
as JSON. Public operational endpoint — no session authentication required.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.metrics import metrics

router = APIRouter()


@router.get("/metrics")
async def get_metrics() -> JSONResponse:
    """Return JSON snapshot of in-process operational metrics."""
    return JSONResponse(content=metrics.get_snapshot())
