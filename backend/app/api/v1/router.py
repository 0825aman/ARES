from fastapi import APIRouter
from app.api.v1.routes import health, projects, documents, runs, sources, evidence, claims, reviews, citations
from app.api.v1.routes import sse, approvals, exports, auth, tokens, guardrails, evaluations

# Protected routers — business logic requiring active authentication in production
protected_router = APIRouter()
protected_router.include_router(projects.router, prefix="/projects", tags=["projects"])
protected_router.include_router(documents.router, prefix="/projects", tags=["documents"])
protected_router.include_router(runs.router, prefix="/projects", tags=["runs"])
protected_router.include_router(sources.router, prefix="/projects", tags=["sources"])
protected_router.include_router(evidence.router, prefix="/projects", tags=["evidence"])
protected_router.include_router(claims.router, prefix="/projects", tags=["claims"])
protected_router.include_router(reviews.router, prefix="/projects", tags=["reviews"])
protected_router.include_router(citations.router, prefix="/projects", tags=["citations"])
# Phase 5 M5.1 — SSE stream endpoint: GET /projects/{project_id}/runs/{run_id}/stream
protected_router.include_router(sse.router, prefix="/projects", tags=["sse"])
# Phase 5 M5.5 — Approval workflow endpoints
protected_router.include_router(approvals.router, prefix="/projects", tags=["approvals"])
# Phase 5 M5.6 — Export and report versioning endpoints
protected_router.include_router(exports.router, prefix="/projects", tags=["exports"])
# Token tracking and telemetry endpoints
protected_router.include_router(tokens.router, prefix="/tokens", tags=["tokens"])
# ARES Guardrails System endpoints
protected_router.include_router(guardrails.router, prefix="/guardrails", tags=["guardrails"])
# ARES LLM & Multi-Agent Evaluation Dashboard endpoints
protected_router.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])

# Auth router — public / self-authenticating (/auth/login, /auth/logout, /auth/me)
auth_router = auth.router

# Composite api_router (used when bypass mode is active)
api_router = APIRouter()
api_router.include_router(protected_router)
api_router.include_router(auth_router, tags=["auth"])

# health_router is mounted separately at the app root (no /api/v1 prefix)
health_router = health.router
