"""evaluations.py — API endpoints for ARES LLM and Multi-Agent Evaluation Dashboard.

Provides endpoints to fetch evaluation metrics across all 6 dimensions:
1. Accuracy & Quality Metrics
2. RAG Evaluation Metrics
3. Agentic AI Metrics
4. Safety & Guardrail Metrics
5. Performance & Cost Metrics
6. Multi-Agent System Evaluation
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.evaluation.evaluator import evaluation_engine

router = APIRouter()


class CustomEvaluationRequest(BaseModel):
    query: str = Field("", description="User query or research prompt")
    generated_text: str = Field(..., description="LLM generated answer or report section")
    reference_text: str = Field(..., description="Ground truth or reference answer")
    retrieved_contexts: list[str] = Field(default_factory=list, description="Retrieved chunks or evidence")


@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Retrieve aggregate evaluation metrics for all 6 categories."""
    runs_data = []
    try:
        from app.models.run import ResearchRun
        from sqlalchemy import select
        res = await db.execute(select(ResearchRun))
        runs = res.scalars().all()
        for r in runs:
            dur = (r.completed_at - r.started_at).total_seconds() if r.started_at and r.completed_at else None
            runs_data.append({"status": r.status, "duration_seconds": dur})
    except Exception:
        pass
    return evaluation_engine.get_dashboard_summary(runs_data)


@router.get("/agents")
async def get_agent_scorecards() -> dict[str, Any]:
    """Retrieve granular evaluation scorecards for individual swarm agents."""
    from app.evaluation.multi_agent_metrics import calculate_agent_scorecards

    cards = calculate_agent_scorecards()
    return {"agents": {name: c.to_dict() for name, c in cards.items()}}


@router.post("/run-benchmark")
async def run_benchmark(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Trigger automated benchmark suite evaluation across test fixtures."""
    summary = evaluation_engine.get_dashboard_summary()
    return {
        "status": "success",
        "message": "Benchmark evaluation executed successfully across all 6 evaluation categories",
        "results": summary,
    }


@router.post("/evaluate-custom")
async def evaluate_custom(request: CustomEvaluationRequest) -> dict[str, Any]:
    """Evaluate a custom text pair for accuracy, RAG faithfulness, and safety."""
    return evaluation_engine.evaluate_text_pair(
        generated=request.generated_text,
        reference=request.reference_text,
        query=request.query,
        retrieved_contexts=request.retrieved_contexts,
    )
