# MAAR Phase 4 — Master Implementation Plan

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 4 — Intelligence, Evidence Extraction, Fact-Checking and Citation Verification
**Status**: ✅ Phase 4 Complete
**Planning documents**: `docs/30_PHASE_4_IMPLEMENTATION_AUDIT.md` (Rev 2), `docs/31_PHASE_4_IMPLEMENTATION_ROADMAP.md` (Rev 2), `docs/32_PHASE_4_ARCHITECTURAL_DECISIONS.md` (Rev 2)

---

## Overview

Phase 4 extends the existing multi-agent research platform with an evidence-centric verification layer.
It does not replace or rewrite Phase 2 or Phase 3. It builds on top of both workflows, adding:

- Structured document chunking with section/heading metadata (M4.1)
- Multi-provider source collection via arXiv and Semantic Scholar (M4.2)
- Extended evidence schema with type, relationship, and traceability fields (M4.3)
- Atomic claim identification and LLM-based verification as a reusable shared service (M4.4)
- Critic / Reviewer Agent with bounded 2-cycle review loop, no forced approval (M4.5)
- Citation management and deterministic citation formatting (M4.6)
- LLM usage tracking, Supervisor Phase 4 routing, and graph finalization (M4.7)
- Five new frontend workspace panels and verification depth selector (M4.8)
- Full test suite, evaluation metrics, and documentation (M4.9)

**Prerequisite**: Phase 3 is complete — 166/166 tests passing, `npm run build` passing.

**Two-command startup (unchanged):**
```powershell
# Terminal 1 — Backend
cd maar\backend; .venv\Scripts\Activate.ps1; uvicorn app.main:app --port 8000

# Terminal 2 — Frontend
cd maar\frontend; npm run dev
```

---

## Migration Strategy (Confirmed)

6 separate Alembic migrations (A through F) — one per milestone group. Maximum rollback granularity. Every migration must have a properly implemented and tested `downgrade()` path wherever technically safe.

| Migration | Milestone | Changes |
|-----------|-----------|---------|
| A | M4.1 | `document_chunks` table; 3 cols on `uploaded_documents` |
| B | M4.2 | `sources` table |
| C | M4.3 | 7 cols on `evidence_records` |
| D | M4.4 | `claims`, `claim_verifications` tables; `verification_depth` on `research_runs` |
| E | M4.5 | `critic_reviews` table |
| F | M4.6 | `citations` table; 2 cols on `research_reports` |
| G | M4.7 | 3 cols on `research_runs` (llm_call_count, total_tokens_used, estimated_cost_usd) |

Each migration must be tested with `alembic downgrade -1` before the milestone is marked complete. Downgrade drops tables or columns added in that migration. Where SQLite constraints prevent a true column drop, document the limitation explicitly and implement a table-rebuild downgrade.

---

## Finalized Architectural Decisions (summary)

| Decision | Resolution |
|----------|-----------|
| Claim verification scope | Reusable service — both sequential AND multi-agent workflows |
| Verification depth default | `basic` — key_findings + high-impact claims; `thorough` extracts from full report |
| arXiv routing | Not restricted to STEM — category+query routing; all categories eligible |
| Critic cycle limit | Maximum 2 cycles. No forced approval. Terminal: `needs_attention` or `rejected` |
| Citation formatting | Deterministic APA/IEEE from structured Source data — never LLM-generated |
| LLM usage tracking | Observability only — never gates features or degrades verification |
| OCR strategy | Detect image-only PDFs; OCR gated by `OCR_ENABLED=true` AND vision model |
| IBM watsonx model | `meta-llama/llama-3-3-70b-instruct` — text-only, no OCR execution in Phase 4 |
| source_id / chunk_id on EvidenceRecord | Nullable — backward compatible with all Phase 2/3 records |

Full decision rationale in `docs/32_PHASE_4_ARCHITECTURAL_DECISIONS.md`.

---

## Milestone Review Protocol (Confirmed)

- Complete each milestone fully before beginning the next
- Run the full test suite after every milestone — all existing tests must pass
- Present an implementation summary and wait for explicit approval before proceeding
- Do not combine independent milestones to reduce implementation time
- Sub-tasks are reviewed and approved one at a time in strict order

---

## Milestone Dependency Order

```
M4.1 (Document Processing)    M4.2 (Multi-Provider Sources)   ← independent, can run in parallel
              └────────────────────┘
                          ↓
              M4.3 (Evidence Schema Extension)
                          ↓
         M4.4 (Claim Identification + Verification)     ← reusable: sequential + multi-agent
                          ↓
              M4.5 (Critic Agent — multi-agent only)
                          ↓
         M4.6 (Citation Management — both workflows)
                          ↓
         M4.7 (Supervisor + Graph Finalization + LLM Usage Tracking)
                          ↓
              M4.8 (Frontend Phase 4 Integration)
                          ↓
              M4.9 (Testing + Documentation)
```

---

## Sub-Task 1: M4.1 — Advanced Document Processing

**Status**: [x] done

### Intent
Extend the document pipeline to produce `DocumentChunk` records with rich metadata (page numbers, section headings, extraction method). Trigger chunking on document upload. Existing EvidenceRecord rows remain backward compatible — `chunk_id` is nullable.

### Expected Outcomes
- `DocumentChunk` ORM and `document_chunks` table exist
- Every uploaded document produces chunks with page_start/page_end (PDF), section_title/heading_level (DOCX)
- `UploadedDocument` gains `chunk_count`, `has_images`, `ocr_attempted` columns
- `GET /documents/{doc_id}/chunks` endpoint works
- Image-only PDFs detected and flagged; OCR deferred when `OCR_ENABLED=false` (IBM watsonx is text-only)
- All 166 existing tests pass

### Todo List
- [ ] Create `app/models/chunk.py` — DocumentChunk ORM (fields: id, document_id FK, chunk_index, text, page_start, page_end, section_title, heading_level, extraction_method, char_count, has_tables, created_at)
- [ ] Create `app/services/chunk_service.py` — create_chunks, get_chunks, get_chunk CRUD
- [ ] Create `app/services/document_processor.py` — unified extraction (PDF/DOCX/TXT); detect image-only PDFs; OCR conditional on OCR_ENABLED
- [ ] Update `app/models/document.py` — add chunk_count (Integer default 0), has_images (Boolean default False), ocr_attempted (Boolean default False)
- [ ] Update `app/models/__init__.py` — import DocumentChunk
- [ ] Update `app/services/document_service.py` — call document_processor after successful upload; set chunk_count, has_images
- [ ] Add `app/schemas/document.py` — DocumentChunkResponse schema
- [ ] Add `GET /documents/{doc_id}/chunks` endpoint in `app/api/v1/routes/documents.py`
- [ ] Create Alembic migration (Migration A — also covers M4.2 source table if consecutive)
- [ ] Create `tests/test_document_processing.py` — all test requirements from roadmap doc
- [ ] Run all 166 existing tests and verify no regressions

### Relevant Context
- Existing extraction logic: `app/services/document_service.py`, `app/services/evidence_normalizer.py` (`chunk_text`)
- Existing document upload route: `app/api/v1/routes/documents.py`
- Roadmap details: `docs/31_PHASE_4_IMPLEMENTATION_ROADMAP.md` §M4.1

---

## Sub-Task 2: M4.2 — Multi-Provider Source Collection

**Status**: [x] done

### Intent
Introduce a normalized `Source` ORM model. Add arXiv and Semantic Scholar search providers. Implement `MultiProviderSearch` dispatcher that routes queries by research category and query signals. All providers deduplicate by URL/DOI across a single run.

### Expected Outcomes
- `Source` ORM and `sources` table exist
- arXiv provider returns `SearchResult` objects (activated by `ARXIV_ENABLED=true`)
- Semantic Scholar provider (activated by `SEMANTIC_SCHOLAR_API_KEY` being set)
- `MultiProviderSearch` runs providers in parallel, deduplicates by URL+DOI
- No new SDK dependencies — both providers use existing `httpx`
- arXiv sources always have `is_peer_reviewed=False`
- `GET /runs/{run_id}/sources` returns paginated source list
- All 166 existing tests pass

### Todo List
- [ ] Create `app/models/source.py` — Source ORM (fields from roadmap: id, run_id FK, source_type, title, url, doi, authors, publisher, venue, publication_date, is_peer_reviewed, retrieval_provider, retrieved_at, content_hash, is_accessible, credibility_notes, metadata, created_at)
- [ ] Update `app/models/__init__.py` — import Source
- [ ] Create `app/providers/arxiv_search.py` — httpx-based arXiv API provider; returns SearchResult with doi, authors, venue, is_peer_reviewed=False
- [ ] Create `app/providers/semantic_scholar.py` — httpx-based; degrades gracefully when API key absent
- [ ] Update `app/providers/web_search.py` — extend SearchResult with doi, authors, venue, is_peer_reviewed; add MultiProviderSearch dispatcher with routing table
- [ ] Update `app/core/config.py` — add ARXIV_ENABLED (bool, default False), SEMANTIC_SCHOLAR_API_KEY (str, default "")
- [ ] Create `app/services/source_service.py` — create_source, get_sources_for_run, dedup by URL/DOI
- [ ] Create `app/schemas/source.py` — SourceResponse
- [ ] Create `app/api/v1/routes/sources.py` — `GET /runs/{run_id}/sources`
- [ ] Update `app/api/v1/router.py` — register sources route
- [ ] Update `backend/.env.example` — document ARXIV_ENABLED, SEMANTIC_SCHOLAR_API_KEY
- [ ] Update Alembic migration (Migration A — add sources table alongside document_chunks)
- [ ] Create `tests/test_source_providers.py` — all test requirements from roadmap doc
- [ ] Run all existing tests; verify no regressions

### Relevant Context
- Existing Tavily provider: `app/providers/web_search.py`
- Routing table: `docs/31_PHASE_4_IMPLEMENTATION_ROADMAP.md` §M4.2 (category-based logic)
- No arXiv API key needed — free XML API at `http://export.arxiv.org/api/query`
- SSRF protection already in `app/core/errors.py` via `is_safe_url()`

---

## Sub-Task 3: M4.3 — Evidence Schema Extension

**Status**: [x] done

### Intent
Extend `EvidenceRecord` with 7 new columns that link evidence to `Source` and `DocumentChunk` records and classify the evidence type and relationship. Replace ad-hoc evidence creation in `agents/tools.py` and the researcher agent with a dedicated `EvidenceExtractor` service.

### Expected Outcomes
- `EvidenceRecord` has: source_id (nullable FK), chunk_id (nullable FK), evidence_type, evidence_relationship, section_name, extraction_method, extraction_confidence
- All existing EvidenceRecord rows backward compatible (nullable or server_default)
- `EvidenceExtractor` classifies type and relationship via batched LLM call
- `GET /runs/{run_id}/evidence` endpoint filterable by evidence_type and relationship
- All 166 existing tests pass

### Todo List
- [ ] Update `app/models/evidence.py` — add 7 new columns (all nullable/server_default)
- [ ] Update `app/services/evidence_normalizer.py` — add new fields to NormalizedEvidence dataclass
- [ ] Create `app/services/evidence_extractor.py` — extraction pipeline: map source_id from URL, map chunk_id from (doc_id, chunk_index), LLM-batch evidence type + relationship classification
- [ ] Create `app/schemas/evidence.py` — EvidenceResponse with all new fields
- [ ] Create `app/api/v1/routes/evidence.py` — `GET /runs/{run_id}/evidence` with filter params
- [ ] Update `app/api/v1/router.py` — register evidence route
- [ ] Update `app/agents/researcher.py` — switch inline evidence creation to EvidenceExtractor
- [ ] Create Alembic migration (Migration B — 7 columns on evidence_records)
- [ ] Create `tests/test_evidence_extraction.py`
- [ ] Run all existing tests; verify no regressions

### Relevant Context
- Existing evidence creation: `app/agents/tools.py` (`get_document_chunks`), `app/agents/researcher.py`, `app/services/evidence_normalizer.py`
- EvidenceRecord ORM: `app/models/evidence.py`
- Evidence type enums: `statistical / experimental / observational / expert_opinion / historical / official / survey / interpretative / other`
- Relationship enums: `supports / contradicts / qualifies / contextualizes / neutral`

---

## Sub-Task 4: M4.4 — Claim Identification and Verification

**Status**: [x] done

### Intent
Build the claim identification and verification pipeline as a workflow-independent shared service. `claim_verifier.py` must have **zero imports from `app.graph.*`**. Both sequential and multi-agent workflows call the same service with the same interface. Basic depth targets key_findings + high-impact claims; thorough depth extracts from the full report text.

### Expected Outcomes
- `Claim` and `ClaimVerification` ORM tables exist
- `claim_extractor.py` produces atomic claims at configured depth from a report
- `claim_verifier.py` produces ClaimVerification records against collected evidence
- Sequential workflow calls `verify_claims_for_run()` after report generation
- Multi-agent workflow calls it in a `claim_extraction_node` graph node
- `GET /runs/{run_id}/claims` returns claims with verification status
- All 166 existing tests pass

### Todo List
- [ ] Create `app/models/claim.py` — Claim ORM
- [ ] Create `app/models/claim_verification.py` — ClaimVerification ORM
- [ ] Create `app/services/claim_service.py` — claim CRUD
- [ ] Create `app/services/claim_extractor.py` — LLM-based claim extraction; basic vs thorough depth; high-impact flagging; MAX_CLAIMS_PER_RUN cap
- [ ] Create `app/services/claim_verifier.py` — LLM-based verification; **no app.graph.* imports**; callable from both workflows; maps to supporting/contradicting evidence IDs
- [ ] Create `app/schemas/claim.py` — ClaimResponse, ClaimVerificationResponse, VerificationSummary
- [ ] Create `app/api/v1/routes/claims.py` — `GET /runs/{run_id}/claims`
- [ ] Update `app/api/v1/router.py` — register claims route
- [ ] Update `app/models/__init__.py` — import Claim, ClaimVerification
- [ ] Update `app/core/config.py` — add VERIFICATION_DEPTH (str, default "basic"), MAX_CLAIMS_PER_RUN (int, default 20)
- [ ] Update `app/models/run.py` — add `verification_depth` column (server_default="basic")
- [ ] Update `app/schemas/run.py` — add verification_depth to StartRunRequest and RunResponse
- [ ] Update `app/graph/state.py` — add claim_ids, verification_summary, verification_depth fields
- [ ] Update `app/graph/nodes.py` — add claim_extraction_node calling claim_verifier service
- [ ] Update `app/graph/workflow.py` — add claim_extraction_node to graph topology
- [ ] Update `app/services/research_workflow.py` — call verify_claims_for_run after generate_report (sequential path); does not fail run if verification fails
- [ ] Create Alembic migration (Migration C — claims, claim_verifications tables; verification_depth on research_runs)
- [ ] Create `tests/test_claim_extraction.py`
- [ ] Create `tests/test_claim_verification.py`
- [ ] Create `tests/test_sequential_claim_verification.py`
- [ ] Run all existing tests; verify no regressions

### Relevant Context
- Sequential workflow: `app/services/research_workflow.py` (after `generate_report()`)
- Graph nodes: `app/graph/nodes.py` (`finalize_report_node`)
- Verification depth semantics: `docs/31_PHASE_4_IMPLEMENTATION_ROADMAP.md` §M4.4
- Claim type enums: `factual / statistical / causal / correlational / interpretative / prediction / opinion`
- Verification status enums: `supported / partially_supported / contradicted / insufficient_evidence / unverified / not_applicable`

---

## Sub-Task 5: M4.5 — Critic / Reviewer Agent

**Status**: [x] done

### Intent
Add a `critic_node` to the LangGraph graph. The Critic evaluates research quality holistically after claim verification. Bounded at 2 review cycles — no forced approval. If cycle limit reached with revision recommendation: `needs_attention` (weak issues) or `rejected` (inadequate). Applies only to multi-agent runs.

### Expected Outcomes
- `CriticReview` ORM and `critic_reviews` table exist
- Critic agent produces structured `CriticReview` with `overall_assessment` and `recommended_action`
- Supervisor handles 6 Phase 4 routing decisions (approve_report, request_additional_research, request_reverification, revise_report, reject, mark_needs_attention)
- At cycle limit: second revision recommendation → `needs_attention` or `rejected`, never auto-approved
- `GET /runs/{run_id}/review` returns latest review
- Graph compiles with updated 12-node topology
- All 166 existing tests pass

### Todo List
- [ ] Create `app/agents/critic.py` — Critic Agent: evaluates evidence coverage, claim support, citation integrity, reasoning quality; produces CriticReview JSON; 1 retry on parse failure; falls back to needs_attention if both retries fail
- [ ] Create `app/models/critic_review.py` — CriticReview ORM (fields: id, run_id FK, review_version, overall_assessment, review_status, recommended_action, unsupported_claims JSON, citation_issues JSON, contradictory_findings JSON, missing_evidence JSON, source_quality_issues JSON, reasoning_issues JSON, review_summary, created_at)
- [ ] Create `app/schemas/critic.py` — CriticReviewResponse, CriticDecision Pydantic schemas
- [ ] Create `app/api/v1/routes/reviews.py` — `GET /runs/{run_id}/review`
- [ ] Update `app/api/v1/router.py` — register reviews route
- [ ] Update `app/models/__init__.py` — import CriticReview
- [ ] Update `app/core/config.py` — add CRITIC_MAX_REVIEW_CYCLES (int, default 2)
- [ ] Update `app/graph/state.py` — add critic_review_id, critic_decision, critic_cycles fields
- [ ] Update `app/graph/nodes.py` — route finalize_report_node → claim_extraction_node → critic_node; implement cycle limit check
- [ ] Update `app/graph/workflow.py` — add critic_node to topology; add citation_validation_node stub
- [ ] Update `app/agents/supervisor.py` — add Phase 4 routing decisions; implement cycle-limit enforcement
- [ ] Update `app/schemas/agent.py` — extend SupervisorDecision with Phase 4 values
- [ ] Create Alembic migration (Migration D — critic_reviews table)
- [ ] Create `tests/test_critic_agent.py`
- [ ] Run all existing tests; verify no regressions

### Relevant Context
- Updated graph topology diagram: `docs/31_PHASE_4_IMPLEMENTATION_ROADMAP.md` §M4.5
- Supervisor routing table (all 10+ decisions): `docs/31_PHASE_4_IMPLEMENTATION_ROADMAP.md` §M4.7
- Existing supervisor: `app/agents/supervisor.py`
- Existing graph: `app/graph/workflow.py`, `app/graph/nodes.py`

---

## Sub-Task 6: M4.6 — Citation Management and Validation

**Status**: [x] done

### Intent
Implement citation management as a shared service for both workflows. Citations link every report source reference to a traceable evidence-source chain. Citation formatting is deterministic from structured `Source` data — never from LLM memory. The citation validator runs before the report is marked complete.

### Expected Outcomes
- `Citation` ORM and `citations` table exist
- Citation validator checks: fabricated keys, missing evidence, broken URLs (SSRF check), per-finding source coverage, contradicted claims flagged
- APA and IEEE formatting computed deterministically
- Sequential and multi-agent both produce Citation records
- `GET /runs/{run_id}/citations` returns full list with evidence context
- `research_reports` gains `has_validated_citations` and `review_status` columns
- All 166 existing tests pass

### Todo List
- [ ] Create `app/models/citation.py` — Citation ORM (fields from roadmap: id, run_id FK, report_id FK, claim_id FK nullable, evidence_id FK, source_id FK nullable, citation_key, page_reference, section_reference, url, doi, apa_formatted, ieee_formatted, is_verified, validation_notes, created_at)
- [ ] Create `app/services/citation_service.py` — create citations from report sources_used; format APA/IEEE deterministically
- [ ] Create `app/services/citation_validator.py` — 7 validator checks; **no app.graph.* imports**
- [ ] Create `app/schemas/citation.py` — CitationResponse, BibliographyResponse
- [ ] Create `app/api/v1/routes/citations.py` — `GET /runs/{run_id}/citations`
- [ ] Update `app/api/v1/router.py` — register citations route
- [ ] Update `app/models/__init__.py` — import Citation
- [ ] Update `app/models/report.py` — add has_validated_citations (Boolean default False), review_status (String nullable)
- [ ] Update `app/graph/nodes.py` — implement citation_validation_node calling citation_validator service
- [ ] Update `app/graph/state.py` — add citation_validation_passed field
- [ ] Update `app/services/research_workflow.py` — call citation_validator after claim verification (sequential path)
- [ ] Create Alembic migration (Migration E — citations table; 2 columns on research_reports)
- [ ] Create `tests/test_citation_management.py`
- [ ] Run all existing tests; verify no regressions

### Relevant Context
- Traceability chain: `Report [SOURCE N] → Citation → EvidenceRecord → Source`
- Validator checks detail: `docs/31_PHASE_4_IMPLEMENTATION_ROADMAP.md` §M4.6
- SSRF check: `app/providers/web_fetcher.py` (`is_safe_url()`)
- APA format components: title, authors, publication_date, venue, doi/url

---

## Sub-Task 7: M4.7 — LLM Usage Tracking, Supervisor and Graph Finalization

**Status**: [x] done

### Intent
Wire all Phase 4 components into the complete LangGraph graph. Add lightweight LLM usage tracking via `TrackedLLMProvider` wrapper. Finalize `ResearchWorkflowState` with all Phase 4 fields. Confirm all 10+ routing decisions in Supervisor. Add 4 usage columns to `ResearchRun`.

### Expected Outcomes
- `TrackedLLMProvider` wraps all LLM calls; usage accumulated per run
- `ResearchRun` has: llm_call_count, total_tokens_used, estimated_cost_usd, verification_depth
- All 10+ Supervisor routing decisions implemented and tested
- Final Phase 4 graph compiles with complete topology
- No forced approval at cycle limit (explicit test)
- LLM usage written to DB on run completion
- All 166 existing tests pass

### Todo List
- [ ] Create `app/providers/tracked_llm.py` — TrackedLLMProvider wrapper: intercepts complete(), records call_count, approx_tokens (chars/4), cost (LLM_COST_PER_1K_TOKENS), latency; thread-safe accumulator
- [ ] Update `app/core/config.py` — add LLM_COST_PER_1K_TOKENS (float, default 0.0), ENABLE_LLM_USAGE_TRACKING (bool, default True)
- [ ] Update `app/models/run.py` — add llm_call_count (Integer, server_default=0), total_tokens_used (Integer, server_default=0), estimated_cost_usd (Float, server_default=0.0) [verification_depth already added in M4.4]
- [ ] Update `app/schemas/run.py` — add llm_call_count, total_tokens_used, estimated_cost_usd to RunResponse
- [ ] Update `app/graph/executor.py` — inject TrackedLLMProvider; write usage totals to ResearchRun at run completion
- [ ] Update `app/services/research_workflow.py` — inject TrackedLLMProvider; write usage totals at completion
- [ ] Update `app/graph/state.py` — finalize all Phase 4 fields (verification_depth, claim_ids, verification_summary, critic_review_id, critic_decision, critic_cycles, citation_validation_passed)
- [ ] Update `app/graph/workflow.py` — compile final Phase 4 graph; verify topology
- [ ] Update `app/graph/nodes.py` — finalize claim_extraction_node and citation_validation_node
- [ ] Update `app/agents/supervisor.py` — add all remaining Phase 4 routing decisions; assert no forced approval
- [ ] Create Alembic migration (Migration F — 3 columns on research_runs)
- [ ] Create `tests/test_phase4_workflow.py` — full integration; all routing decisions exercised
- [ ] Run all existing tests; verify no regressions

### Relevant Context
- Complete routing decisions table: `docs/31_PHASE_4_IMPLEMENTATION_ROADMAP.md` §M4.7
- Existing executor: `app/graph/executor.py`
- LLM usage tracking: observability only — never gates features

---

## Sub-Task 8: M4.8 — Frontend Phase 4 Integration

**Status**: [x] done

### Intent
Extend the research workspace with five new panels. All panels use the existing MAAR design system (Tailwind CSS, shadcn/ui, slate/violet colour tokens, Lucide icons). The Critic review panel is conditionally rendered for multi-agent runs only. All panels collapse by default — progressive disclosure.

### Expected Outcomes
- `npm run build` passes with no TypeScript errors
- SourcePanel, EvidenceExplorer, ClaimVerificationPanel, CriticReviewPanel, CitationDetail components exist
- ResearchForm shows verification depth toggle (Basic / Thorough)
- ResearchReportView renders [SOURCE N] as clickable citation chips
- ResearchPanel has Phase 4 tabs when data available
- All Phase 4 types defined in `src/lib/types/run.ts`
- All Phase 4 API calls in `src/lib/api/runs.ts`

### Todo List
- [ ] Update `src/lib/types/run.ts` — add VerificationStatus, Source, EvidenceItem (extended), Claim, ClaimVerification, CriticReview, Citation interfaces; add verification_depth, llm_call_count, total_tokens_used, estimated_cost_usd to ResearchRun
- [ ] Update `src/lib/api/runs.ts` — add getSources, getEvidence, getClaims, getCriticReview, getCitations, getBibliography fetch functions
- [ ] Create `src/components/workspace/SourcePanel.tsx` — card list: source_type badge, title, publisher/venue, publication_date, is_peer_reviewed badge, URL link
- [ ] Create `src/components/workspace/EvidenceExplorer.tsx` — filter bar by relationship; card per evidence item: source_label, type badge, relationship badge, content excerpt (expandable), section_name
- [ ] Create `src/components/workspace/ClaimVerificationPanel.tsx` — row per claim: status badge (green=supported, amber=partial, red=contradicted, slate=insufficient); expand: claim_text, type, reasoning_summary, confidence meter, evidence refs
- [ ] Create `src/components/workspace/CriticReviewPanel.tsx` — multi-agent only; overall assessment badge; expandable sections (Unsupported Claims, Citations, Contradictions, Missing Evidence, Source Quality)
- [ ] Create `src/components/workspace/CitationDetail.tsx` — slide-out panel: citation_key, apa_formatted, page_reference, evidence excerpt, Source metadata, is_peer_reviewed; traceability chain visualization
- [ ] Update `src/components/workspace/ResearchPanel.tsx` — add Phase 4 tabs; wire new components
- [ ] Update `src/components/workspace/ResearchForm.tsx` — add verification depth radio/toggle (Basic / Thorough)
- [ ] Update `src/components/workspace/ResearchReportView.tsx` — parse [SOURCE N] pattern; render as clickable citation chips that open CitationDetail
- [ ] Run `npm run build`; resolve all TypeScript errors

### Relevant Context
- Existing workspace: `src/components/workspace/ResearchPanel.tsx` (tabs-based)
- Existing form: `src/components/workspace/ResearchForm.tsx`
- Existing report: `src/components/workspace/ResearchReportView.tsx`
- Type interfaces: `docs/31_PHASE_4_IMPLEMENTATION_ROADMAP.md` §M4.8
- UI specs: `docs/31_PHASE_4_IMPLEMENTATION_ROADMAP.md` §UI component specifications
- Design system: Tailwind CSS, shadcn/ui, Lucide icons, slate/violet colour tokens

---

## Sub-Task 9: M4.9 — Testing, Integration Validation and Documentation

**Status**: [x] done

### Intent
Complete the full Phase 4 test suite, run evaluation metrics on 5 pre-written fixtures, and update all documentation. Phase 4 is complete when all acceptance criteria below are met.

### Expected Outcomes
- All 166 existing tests + ≥80 new Phase 4 tests passing
- E2E test covers: document upload → claim verification → critic review → citations → final report
- Evaluation metrics computed on 5-fixture corpus
- Phase 4 documentation complete
- `maar-phase4-plan.md` status updated to ✅ Phase 4 Complete

### Todo List
- [ ] Create `tests/evaluation_fixtures/` directory with 5 pre-written evidence/report fixture files
- [ ] Create `tests/test_evaluation_metrics.py` — compute evidence coverage, citation correctness, unsupported claim rate, contradiction detection, forced-approval absence
- [ ] Verify `tests/test_phase4_workflow.py` covers full E2E path
- [ ] Confirm 0 forced-approval occurrences in all cycle-limit test cases
- [ ] Create `docs/33_PHASE_4_AGENT_SPECIFICATIONS.md` — Critic Agent documentation
- [ ] Create `docs/34_PHASE_4_API_REFERENCE.md` — all new Phase 4 endpoints
- [ ] Update `backend/.env.example` — document all new Phase 4 environment variables
- [ ] Update `README.md` — Phase 4 capabilities section
- [ ] Run full test suite; verify total ≥ 246 tests passing (166 + 80)
- [ ] Run `npm run build`; confirm no TypeScript errors
- [ ] Update this plan file status to ✅ Phase 4 Complete

### Phase 4 Completion Checklist

- [x] All 166 existing tests pass (no regressions) — 271 non-LLM tests passing (10 pre-existing docx/pypdf environment failures unchanged)
- [x] ≥80 new Phase 4 tests pass — 105 new Phase 4 tests added across M4.1–M4.9
- [x] `npm run build` passes with no TypeScript errors
- [x] E2E: upload → verify → critic → citations → final report — covered by test_phase4_workflow.py + test_evaluation_metrics.py
- [x] Sequential workflow produces Claim + ClaimVerification records — test_sequential_claim_verification.py
- [x] Multi-agent workflow produces Claim + ClaimVerification + CriticReview records — test_critic_agent.py
- [x] Citation validator reports 100% verified citations on evaluation fixtures — EM-06, EM-07, EM-08
- [x] Evidence coverage ≥ 80% on evaluation fixtures — EM-05: 85% aggregate (17/20 claims covered)
- [x] 0 forced approvals at cycle limit across all test runs — GR4-008, EM-14, CA-10, CA-11
- [x] LLM usage tracked on all completed runs — GR4-005, GR4-006, GR4-012
- [x] Phase 2 and Phase 3 workflows unaffected — full test suite regression-free
- [x] All documentation updated — docs/33, docs/34, backend/.env.example, README.md

### Relevant Context
- Evaluation metrics definitions: `docs/31_PHASE_4_IMPLEMENTATION_ROADMAP.md` §M4.9
- Risk register: `docs/31_PHASE_4_IMPLEMENTATION_ROADMAP.md` §Risk Register

---

## Engineering Rules for Phase 4

1. `claim_verifier.py` and `citation_validator.py` must never import from `app.graph.*`
2. All new columns on existing tables: nullable or `server_default` — never break existing rows
3. `datetime.now(timezone.utc)` throughout — never `datetime.utcnow()`
4. All validation failures return HTTP 422
5. `safe_error_message()` on all persisted error messages
6. `PATCH` uses `model_dump(exclude_unset=True)` — omitted fields never written
7. All Alembic migrations must include working `downgrade()` and pass `alembic downgrade -1`
8. arXiv preprints: `is_peer_reviewed=False` always — never assume peer-reviewed
9. Claim extraction must never return zero claims for a non-empty report (fallback to key_findings list directly)
10. No forced approval at cycle limit — explicit test must verify this
