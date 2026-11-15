# 40 — Phase 5 Requirements

**Project:** Multi-Agent Autonomous Researcher (MAAR)
**Phase:** 5 — Complete Research Experience
**Status:** Planning

---

## 1. Overview

Phase 5 transforms MAAR from a functional research engine with a data-display UI into a complete, interactive research product. The user gains real-time visibility into agent execution, structured evidence exploration, human-in-the-loop control, and professional report export.

Phase 4 delivered a complete backend pipeline — source collection, evidence extraction, claim verification, Critic review, and citation management — all accessible via REST APIs. Phase 5 builds the experience layer on top of that foundation.

---

## 2. Phase 4 Baseline (What Exists)

The following capabilities are confirmed complete and tested as of Phase 4:

| Area | Status |
|------|--------|
| Sequential research workflow (Phase 2) | ✅ Complete |
| Multi-agent workflow with LangGraph (Phase 3) | ✅ Complete |
| LangGraph async SQLite checkpointer | ✅ Active (`maar_checkpoints.db`) |
| Document chunking (M4.1) | ✅ Complete |
| Source collection — Tavily, arXiv, Semantic Scholar (M4.2) | ✅ Complete |
| Evidence schema extension and type classification (M4.3) | ✅ Complete |
| Claim extraction and LLM-based verification (M4.4) | ✅ Complete |
| Critic Agent with bounded review cycles (M4.5) | ✅ Complete |
| Citation management — APA/IEEE formatting (M4.6) | ✅ Complete |
| LLM usage tracking (M4.7) | ✅ Complete |
| Phase 4 frontend panels (Sources, Evidence, Claims, Critic, Citations) (M4.8) | ✅ Complete |
| Evaluation metrics and documentation (M4.9) | ✅ Complete |

**What Phase 5 adds:** Live activity streaming, structured progress tracking, human approval workflow, Source Explorer, Evidence Viewer improvements, and PDF/DOCX/Markdown export.

---

## 3. Objectives

By the end of Phase 5, a user should be able to:

1. Start a research run and observe live agent activities as they happen.
2. Track research progress through well-defined workflow stages.
3. Inspect all collected sources with search, filter, and sort.
4. Drill into any claim, view its verification evidence, and navigate to the original source.
5. Approve or reject key workflow checkpoints before the workflow proceeds.
6. View the final research report in a structured, professional layout.
7. Export the report as PDF, DOCX, or Markdown.
8. Return to any previous run and see its complete activity history.

---

## 4. Functional Requirements

### 4.1 Live Agent Activity (M5.1 + M5.2)

**FR-ACT-01**: Display a real-time activity timeline during a research run showing actual backend execution events, not fabricated frontend messages.

**FR-ACT-02**: Each activity entry must include: agent name, event type, summary description, timestamp, iteration/cycle count, and status (pending, running, completed, failed).

**FR-ACT-03**: The activity timeline must survive browser refresh — events are persisted and replayed on reconnect.

**FR-ACT-04**: The system must use Server-Sent Events (SSE) for live event delivery. Polling must not be the primary mechanism for live updates (polling can remain as a fallback).

**FR-ACT-05**: The frontend must handle reconnection after SSE connection drops, resuming from the last received event ID.

**FR-ACT-06**: The frontend must not expose internal LLM chain-of-thought, model reasoning, or raw API payloads. Only concise execution summaries and tool/action events are displayed.

**FR-ACT-07**: Out-of-order or duplicate events must be handled gracefully (deduplicated by event ID).

### 4.2 Research Progress Tracking (M5.2)

**FR-PRG-01**: Display overall research progress across clearly defined workflow stages.

**FR-PRG-02**: Progress stages for multi-agent workflow:
1. Planning
2. Source Collection (one stage per task, n tasks)
3. Report Generation
4. Claim Verification
5. Critic Review
6. Citation Validation
7. Complete

**FR-PRG-03**: Progress must be derived from actual task completion counts, not arbitrary frontend percentages.

**FR-PRG-04**: Each stage must have a clear visual state: pending (grey), running (animated), completed (green), failed (red), skipped (grey strikethrough), waiting for approval (amber).

**FR-PRG-05**: Elapsed time and estimated stage duration must be displayed.

**FR-PRG-06**: When the run is in `needs_attention` or `rejected` state, the progress display must clearly communicate the reason.

**FR-PRG-07**: Sequential workflow progress uses a different (simpler) stage model than multi-agent.

### 4.3 Source Explorer (M5.3)

**FR-SRC-01**: Display all sources collected during a research run with full metadata: title, authors, publication date, publisher, source type, DOI, arXiv ID, Semantic Scholar ID, URL, retrieval provider, peer-reviewed status, retrieval timestamp.

**FR-SRC-02**: Support text search across source title, authors, and URL.

**FR-SRC-03**: Support filter by: source type (web, academic, news, document), retrieval provider (Tavily, arXiv, Semantic Scholar), peer-reviewed status (yes/no/unknown).

**FR-SRC-04**: Support sort by: relevance, publication date, retrieval time.

**FR-SRC-05**: Each source must link to the evidence records associated with it.

**FR-SRC-06**: Duplicate sources (same URL or DOI) must be visually marked.

**FR-SRC-07**: External source URLs must open in a new tab with `rel="noopener noreferrer"`.

**FR-SRC-08**: Source credibility must NOT be displayed as a numeric score. Only transparent metadata-based indicators are acceptable (e.g., "Peer-reviewed", "arXiv preprint", "Web source — no peer review").

**FR-SRC-09**: Source Explorer must reuse Phase 4 `GET /sources` API and `Source` model. No new tables.

### 4.4 Evidence Viewer (M5.4)

**FR-EVI-01**: Users can view all extracted claims for a research run, grouped by originating section.

**FR-EVI-02**: For each claim, display: claim text, type, verification status, is_high_impact flag, and full verification details (supporting evidence IDs, contradicting evidence IDs, reasoning summary, confidence).

**FR-EVI-03**: Users can expand a claim to see its associated evidence records (content, source label, evidence type, relationship, source URL).

**FR-EVI-04**: Users can navigate from a claim → evidence record → original source.

**FR-EVI-05**: Document provenance must be preserved: page numbers, section names, chunk index.

**FR-EVI-06**: Evidence relationships must be clearly labeled: `supports`, `contradicts`, `qualifies`, `contextualizes`, `neutral`.

**FR-EVI-07**: Claims with `insufficient_evidence` or `contradicted` status must be visually prominent — these are critical findings.

**FR-EVI-08**: AI-generated reasoning summaries must be clearly labeled as AI-generated, distinct from the actual extracted evidence text.

**FR-EVI-09**: Evidence Viewer must never present a claim as verified without a traceable evidence record.

**FR-EVI-10**: Evidence Viewer must reuse Phase 4 `GET /claims` and `GET /evidence` APIs. No new tables.

### 4.5 Human Approval Workflow (M5.5)

**FR-APR-01**: The system must support human approval checkpoints at configurable workflow stages.

**FR-APR-02**: Initial approval checkpoints: (a) Research Plan Approval, (b) Critic Review Approval (when Critic returns `needs_attention`).

**FR-APR-03**: Additional checkpoints (configurable per run): pre-research approval, final report approval.

**FR-APR-04**: Each approval request must be persisted with: run_id, checkpoint_type, workflow state reference, status (pending/approved/rejected/expired), user decision, optional comments, created_at, decided_at.

**FR-APR-05**: Pending approval requests must survive browser refresh and application restart.

**FR-APR-06**: The user must be able to: Approve, Reject, Request Changes (with comment), or Continue with Limitations.

**FR-APR-07**: The LangGraph workflow must pause at approval checkpoints using `interrupt_before` and resume when the user responds.

**FR-APR-08**: Duplicate approval actions on the same checkpoint must be prevented.

**FR-APR-09**: Approval does not automatically verify unverified claims. Workflow decisions are made by the Supervisor post-approval.

**FR-APR-10**: The approval UI must clearly communicate: what is being approved, what happens if approved vs rejected, and what the current Critic findings are (if relevant).

**FR-APR-11**: Expired approval requests (run has been in pending state for >24 hours) must be handled gracefully.

### 4.6 Report Generation and Export (M5.6)

**FR-RPT-01**: Display the research report in a structured, professional layout:
1. Title and Research Metadata
2. Executive Summary
3. Research Question and Objectives
4. Key Findings (with clickable `[SOURCE N]` citations)
5. Detailed Analysis
6. Evidence and Claim Verification Summary
7. Contradictions and Conflicting Findings
8. Limitations and Uncertainties
9. Conclusion
10. References and Citations (APA formatted)

**FR-RPT-02**: Export to PDF using a local Python library (no external service).

**FR-RPT-03**: Export to DOCX using `python-docx` (already installed).

**FR-RPT-04**: Export to Markdown (no additional library required).

**FR-RPT-05**: Exported files must be downloadable via an API endpoint. Files are stored in a local exports directory.

**FR-RPT-06**: Report versioning must be supported. When the Critic requests `revise_report`, the previous version must be preserved (not overwritten). Each version must be accessible.

**FR-RPT-07**: Exports must use existing verified research data only. No new LLM generation during export.

**FR-RPT-08**: Path traversal and unsafe file names must be prevented in export file paths.

**FR-RPT-09**: Export file names must be deterministic and human-readable: `{project_slug}_{run_id[:8]}_{format}.{ext}`.

**FR-RPT-10**: Large reports must not crash the export service. Report size limits must be defined and enforced.

---

## 5. Non-Functional Requirements

### 5.1 Performance

**NFR-PERF-01**: SSE connections must not degrade backend performance for other requests.

**NFR-PERF-02**: Source Explorer must paginate results (default 20 per page, max 100).

**NFR-PERF-03**: Evidence Viewer must paginate claims (default 20 per page).

**NFR-PERF-04**: PDF/DOCX export must complete within 30 seconds for a typical report (≤ 50 pages).

**NFR-PERF-05**: SSE event delivery latency must be ≤ 2 seconds from backend event creation.

### 5.2 Reliability

**NFR-REL-01**: The application must recover correctly after backend restart with pending approvals.

**NFR-REL-02**: SSE must reconnect automatically after connection drop (client-side EventSource auto-reconnect + Last-Event-ID header).

**NFR-REL-03**: Export failures must be captured and reported to the user without crashing the backend.

**NFR-REL-04**: SQLite write concurrency must be managed — no concurrent writes to the same run's tables during SSE streaming.

### 5.3 Security

**NFR-SEC-01**: Exported files must be stored outside the web root and served only via authenticated (or run-ownership-validated) download endpoints.

**NFR-SEC-02**: File paths in export responses must not expose absolute server paths.

**NFR-SEC-03**: SSE event payloads must not include API keys, raw LLM responses, internal model reasoning, or provider credentials.

**NFR-SEC-04**: Approval endpoints must validate that the approval request belongs to the correct project/run.

**NFR-SEC-05**: External source URLs rendered in the UI must not execute scripts (safe rendering, not dangerouslySetInnerHTML).

**NFR-SEC-06**: User-provided approval comments must be sanitized before persistence.

### 5.4 Usability

**NFR-UX-01**: All Phase 5 UI must follow the existing Tailwind/shadcn/ui design system.

**NFR-UX-02**: All tabs and panels must have loading skeletons, empty states, and error states.

**NFR-UX-03**: The workspace layout must remain usable on viewports ≥ 1024px. Responsive layout is required but mobile-first is not a priority.

**NFR-UX-04**: Approval panels must be clearly visible and not hidden in a tab — they must interrupt the normal workflow with a visible prompt.

---

## 6. Explicit Exclusions

The following are explicitly OUT OF SCOPE for Phase 5:

- Multi-user authentication, accounts, or sessions.
- Cloud hosting, managed databases, or paid monitoring.
- Redis, Celery, or external message queues.
- Real-time collaborative research (multi-user simultaneous editing).
- Mobile-first or native app layouts.
- OCR capabilities beyond what Phase 4 architecture described (text-only, no vision LLM in Phase 5).
- New LLM provider integrations beyond the existing fallback chain.
- Automated retesting of previously verified claims.
- Version control integration (Git) for report exports.
- User-defined custom export templates.

---

## 7. Assumptions

- Phase 4 is fully deployed and tested. All 14 API endpoints, 14 ORM models, and 271 tests remain passing.
- The LangGraph checkpointer (`maar_checkpoints.db`) is functional and can support `interrupt_before`.
- `python-docx` is already installed (confirmed in requirements.txt) and can be used for DOCX export.
- A PDF generation library (`reportlab` or `weasyprint`) will be added to requirements.txt as part of M5.6.
- The frontend polling architecture (setInterval) will be retained as a fallback alongside SSE.
- All approval data will be persisted in the main SQLite DB (`maar_dev.db`) — not the checkpoint DB.
- Research runs are single-user (no concurrent access to the same run from multiple browser tabs is a supported scenario, but correctness must not be compromised by it).
- Export files are stored on local filesystem in a configurable `exports/` directory.
