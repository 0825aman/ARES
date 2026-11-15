# 31 — Phase 4 Implementation Roadmap

**Project:** Multi-Agent Autonomous Researcher (MAAR)
**Phase:** 4 — Intelligence, Evidence Extraction, Fact-Checking and Citation Verification
**Date:** November 2026
**Status:** Awaiting Approval
**Revision:** 2 — Updated to reflect finalized architectural decisions

---

## Overview

Phase 4 extends the existing multi-agent research platform with an evidence-centric verification layer. It does not replace or rewrite Phase 2 or Phase 3. It builds on top of both workflows, adding structured evidence extraction, atomic claim identification, fact-checking, a Critic Agent (multi-agent only), and traceable citations.

**The guiding principle: no factual claim in a research report should be presented as verified without traceable supporting evidence.**

### Finalized scope decisions

**Claim verification is a reusable backend service available to both sequential and multi-agent workflows.** It is not LangGraph-specific.

**Sequential workflow (Phase 2):** retains all existing behaviour. Phase 4 adds configurable claim verification (basic depth by default) after report generation. No Critic Agent. No iterative review loop.

**Multi-agent workflow (Phase 3):** integrates the same reusable claim verification service. Adds the Critic Agent with bounded review cycles, Supervisor routing on Critic output, and citation validation.

**Critic cycle termination:** maximum 2 review cycles. If the second review still recommends revision, the run terminates with `needs_attention` or `rejected` — never forced to `approved`. Unresolved issues remain visible in the report.

**arXiv routing:** not restricted to STEM. All research categories are eligible. The Research Planning Agent identifies category and query intent; the source router selects providers accordingly.

**LLM usage tracking:** applies to all runs, both workflows. Tracked as observability only — never gates features or degrades verification quality.

---

## Milestone Dependency Graph

```
M4.1 (Document Processing)    M4.2 (Multi-Provider Source Collection)
          └──────────────────────────────────┘
                              ↓
                    M4.3 (Evidence Schema Extension)
                              ↓
               M4.4 (Claim Identification + Verification)
               [Reusable service — sequential + multi-agent]
                              ↓
                    M4.5 (Critic Agent — multi-agent only)
                              ↓
               M4.6 (Citation Management — both workflows)
                              ↓
               M4.7 (Supervisor + Full Graph Finalization)
                              ↓
                    M4.8 (Frontend Phase 4 Integration)
                              ↓
                   M4.9 (Testing + Documentation)
```

M4.1 and M4.2 are independent and may be developed in parallel. All subsequent milestones are strictly sequential.

---

## Milestone 4.1 — Advanced Document Processing

### Intent

Extend the document processing pipeline to produce richer, structured `DocumentChunk` records that preserve page numbers, section headings, extraction method metadata, and an image-detection flag for OCR-deferred processing. Introduce the `DocumentChunk` ORM as a document-scoped (run-independent) first-class model. Add a `document_processor.py` service that replaces the inline extraction currently embedded in `research_workflow.py` and `agents/tools.py`.

### Key design decisions

- `DocumentChunk` is created on document upload, not during research execution. Chunks are permanent records of what was extracted — they outlive individual research runs.
- OCR detection: if pypdf extracts < 50 chars per page, flag `has_images=True` on `UploadedDocument`. Actual LLM-based OCR extraction is gated by `OCR_ENABLED=true` and a vision-capable LLM provider. IBM watsonx Llama 3.3 70B is text-only — OCR code will be implemented as a conditional branch but will not execute until a vision model is configured.
- Existing Phase 2 and Phase 3 EvidenceRecord rows are backward compatible — `chunk_id` is nullable.

### What changes

**New files:**
- `app/models/chunk.py` — DocumentChunk ORM
- `app/services/chunk_service.py` — chunk CRUD (create_chunks, get_chunks, get_chunk)
- `app/services/document_processor.py` — unified extraction pipeline (PDF, DOCX, TXT, OCR-flag)
- `tests/test_document_processing.py`

**Modified files:**
- `app/models/__init__.py` — import DocumentChunk
- `app/models/document.py` — add `chunk_count` (Integer, default 0), `has_images` (Boolean, default False), `ocr_attempted` (Boolean, default False)
- `alembic/versions/` — new migration
- `app/api/v1/routes/documents.py` — add `GET /{doc_id}/chunks` endpoint
- `app/schemas/document.py` — add `DocumentChunkResponse`
- `app/services/document_service.py` — trigger chunk creation on successful upload

### DocumentChunk model fields

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| id | String(36) PK | No | UUID |
| document_id | String(36) FK | No | FK uploaded_documents (CASCADE DELETE) |
| chunk_index | Integer | No | 0-based sequence |
| text | Text | No | Extracted chunk content |
| page_start | Integer | Yes | First page in this chunk |
| page_end | Integer | Yes | Last page in this chunk |
| section_title | String(500) | Yes | Heading above this chunk (DOCX headings, PDF heuristics) |
| heading_level | Integer | Yes | 1–6 (DOCX heading level) |
| extraction_method | String(50) | Yes | "pypdf" / "python-docx" / "llm-ocr" / "plain-text" |
| char_count | Integer | No | len(text) |
| has_tables | Boolean | No | default False |
| created_at | DateTime | No | UTC |

### Test requirements for M4.1

- PDF chunking produces correct page_start/page_end on each chunk
- DOCX chunking extracts heading paragraphs as section_title
- DOCX heading level preserved in heading_level field
- TXT chunking produces sequential chunk_index values with correct overlap
- Low-quality/image-only PDF sets has_images=True on UploadedDocument
- When OCR_ENABLED=False, image PDF stored with no text chunks and ocr_attempted=False
- chunk_count on UploadedDocument equals number of DocumentChunk rows created
- `GET /documents/{doc_id}/chunks` returns 200 with paginated list
- Duplicate document detection still works (hash-based)
- All existing 166 tests pass

### Acceptance criteria

- All existing tests pass
- DocumentChunk rows created on document upload
- section_title populated for DOCX files with Heading paragraphs
- page_start and page_end populated for PDF chunks
- `GET /documents/{doc_id}/chunks` returns correct data

---

## Milestone 4.2 — Multi-Provider Source Collection

### Intent

Introduce a normalized `Source` ORM model that separates source records from the evidence derived from them. Extend the search provider abstraction to support arXiv and Semantic Scholar. Implement a `MultiProviderSearch` dispatcher that routes queries to appropriate providers based on research category and query relevance. Preserve academic metadata including DOI, authors, publication date, peer-review status, and publication venue.

### Key design decisions

- arXiv: free API via httpx, no API key required. Activated by `ARXIV_ENABLED=true`. **Not restricted to STEM** — available to all research categories when enabled.
- Semantic Scholar: REST API via httpx. Activated by `SEMANTIC_SCHOLAR_API_KEY` being set. Higher rate limits available with key.
- arXiv preprints must never be assumed peer-reviewed. `is_peer_reviewed=False` default for arXiv sources.
- `MultiProviderSearch` runs all enabled providers in parallel via `asyncio.gather` and deduplicates by URL/DOI across providers.
- Provider routing uses `research_category` from `ResearchProject` plus query-level signals from the Planner Agent.
- No new SDK dependencies — both arXiv and Semantic Scholar accessed via existing httpx dependency.

### Routing logic

The `MultiProviderSearch` dispatcher selects providers based on category and query signals:

| Category | Always | If ARXIV_ENABLED | If SEMANTIC_SCHOLAR_API_KEY set |
|----------|--------|------------------|---------------------------------|
| AI / Computer Science | Tavily | arXiv | Semantic Scholar |
| Physics / Mathematics | Tavily | arXiv | Semantic Scholar |
| Biology / Medicine / Health | Tavily | arXiv | Semantic Scholar |
| Economics / Finance | Tavily | arXiv (if query has empirical/theory signal) | Semantic Scholar |
| Policy / Social Science | Tavily | arXiv (if query has research signal) | Semantic Scholar |
| History / Culture | Tavily | — | Semantic Scholar (if key set) |
| General / Unclassified | Tavily | arXiv (if ARXIV_ENABLED) | Semantic Scholar (if key set) |

Category determined from `ResearchProject.category` field (already stored). Query-level signals are keyword heuristics in the search query string (e.g., "study", "research", "trial", "model", "algorithm").

### What changes

**New files:**
- `app/models/source.py` — Source ORM
- `app/providers/arxiv_search.py` — arXiv provider
- `app/providers/semantic_scholar.py` — Semantic Scholar provider
- `app/services/source_service.py` — source CRUD and run-level deduplication
- `app/schemas/source.py` — SourceResponse
- `app/api/v1/routes/sources.py` — GET /runs/{run_id}/sources endpoint
- `tests/test_source_providers.py`

**Modified files:**
- `app/providers/web_search.py` — add `MultiProviderSearch` dispatcher, extend `SearchResult` with `doi`, `authors`, `venue`, `is_peer_reviewed`
- `app/core/config.py` — add ARXIV_ENABLED, SEMANTIC_SCHOLAR_API_KEY
- `app/api/v1/router.py` — register sources route
- `app/models/__init__.py` — import Source
- `alembic/versions/` — combined with M4.1 migration if milestones proceed consecutively
- `backend/.env.example` — document new config vars

### Source model fields

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| id | String(36) PK | No | UUID |
| run_id | String(36) FK | No | FK research_runs (CASCADE) |
| source_type | String(50) | No | "web" / "academic" / "document" / "news" |
| title | String(1000) | Yes | |
| url | String(2000) | Yes | |
| doi | String(200) | Yes | |
| authors | Text | Yes | JSON array of author name strings |
| publisher | String(500) | Yes | Journal, conference, or organization |
| venue | String(500) | Yes | Conference name or journal title |
| publication_date | String(50) | Yes | ISO date string |
| is_peer_reviewed | Boolean | No | default False — never assume arXiv is peer-reviewed |
| retrieval_provider | String(50) | No | "tavily" / "arxiv" / "semantic_scholar" |
| retrieved_at | DateTime | No | UTC |
| content_hash | String(64) | Yes | SHA-256 for dedup |
| is_accessible | Boolean | No | default True |
| credibility_notes | Text | Yes | Factual observations only — no numeric score |
| metadata | Text | Yes | JSON — provider-specific extra fields |
| created_at | DateTime | No | UTC |

### Test requirements for M4.2

- arXiv provider returns correctly shaped SearchResult objects from mock XML response
- Semantic Scholar provider degrades gracefully when API key is absent (falls back to Tavily only)
- MultiProviderSearch deduplicates results across providers by URL and DOI
- Source records persisted for each unique URL/DOI in a run
- is_peer_reviewed=False for all arXiv sources
- Routing produces correct provider list for AI/ML category with ARXIV_ENABLED=true
- Routing produces Tavily-only for history category with ARXIV_ENABLED=false
- `GET /runs/{run_id}/sources` returns paginated list with metadata
- Existing Tavily-only tests continue to pass

### Acceptance criteria

- All existing tests pass
- Source provider tests pass
- Source rows created during research runs
- Run-level deduplication works across providers
- `GET /runs/{run_id}/sources` returns 200

---

## Milestone 4.3 — Evidence Schema Extension

### Intent

Extend the existing `EvidenceRecord` ORM with richer metadata fields that link evidence to `Source` records and `DocumentChunk` records. Replace the ad-hoc evidence creation in `agents/tools.py` with a dedicated `EvidenceExtractor` service that classifies evidence type and relationship, and maps evidence to the new Source and DocumentChunk models.

### What changes

**New files:**
- `app/services/evidence_extractor.py` — structured extraction pipeline
- `app/schemas/evidence.py` — EvidenceResponse
- `tests/test_evidence_extraction.py`

**Modified files:**
- `app/models/evidence.py` — add 7 new columns (see below)
- `app/services/evidence_normalizer.py` — add new fields to NormalizedEvidence dataclass
- `app/api/v1/routes/` — add evidence list endpoint
- `alembic/versions/` — new migration
- `app/agents/researcher.py` — switch inline evidence creation to EvidenceExtractor

### New EvidenceRecord columns (all backward compatible)

| Column | Type | Backward compatible | How |
|--------|------|---------------------|-----|
| source_id | String(36) FK | Yes | Nullable FK to sources |
| chunk_id | String(36) FK | Yes | Nullable FK to document_chunks |
| evidence_type | String(50) | Yes | server_default="other" |
| evidence_relationship | String(50) | Yes | server_default="neutral" |
| section_name | String(500) | Yes | Nullable |
| extraction_method | String(50) | Yes | Nullable |
| extraction_confidence | Float | Yes | Nullable |

### Evidence type enum values

`statistical` / `experimental` / `observational` / `expert_opinion` / `historical` / `official` / `survey` / `interpretative` / `other`

### Evidence relationship enum values

`supports` / `contradicts` / `qualifies` / `contextualizes` / `neutral`

### EvidenceExtractor pipeline

```
Input: list[NormalizedEvidence], run_id, task_id, source_map {url → source_id}, chunk_map {(doc_id, chunk_idx) → chunk_id}

For each item:
  1. Map to source_id if URL matches known Source
  2. Map to chunk_id if (document_id, chunk_index) matches DocumentChunk
  3. Classify evidence_type via batched LLM call (up to 10 items per call)
  4. Classify evidence_relationship from content vs research question context
  5. Persist EvidenceRecord with all new fields

Returns: list[str] (evidence IDs persisted)
```

### Test requirements for M4.3

- EvidenceExtractor maps web evidence to source_id when URL matches Source
- EvidenceExtractor maps document evidence to chunk_id
- evidence_type set to valid enum value
- evidence_relationship defaults to "neutral" when unclear
- extraction_confidence between 0.0 and 1.0
- Existing Phase 2 runs produce evidence records with backward-compatible defaults
- `GET /runs/{run_id}/evidence` returns paginated list filterable by evidence_type and evidence_relationship

### Acceptance criteria

- All existing tests pass
- EvidenceRecord has new fields with correct values
- Evidence API returns 200

---

## Milestone 4.4 — Claim Identification and Verification

### Intent

Implement the claim identification and verification pipeline as a **workflow-independent reusable backend service** (`claim_verifier.py`). This service is callable from both the sequential workflow (after report generation) and the multi-agent workflow (in a dedicated graph node). It extracts atomic claims at the configured depth and verifies each against collected evidence.

### Reusability requirement

`claim_verifier.py` must have no imports from `app.graph.*`. It must accept a `db` session, a `run_id`, a `report_id`, and a `verification_depth` and return a structured result. Both workflows call it with the same interface.

### What changes

**New files:**
- `app/models/claim.py` — Claim ORM
- `app/models/claim_verification.py` — ClaimVerification ORM
- `app/services/claim_service.py` — claim CRUD
- `app/services/claim_extractor.py` — LLM-based claim extraction (workflow-independent)
- `app/services/claim_verifier.py` — LLM-based verification, callable from both workflows
- `app/schemas/claim.py` — ClaimResponse, ClaimVerificationResponse, VerificationSummary
- `app/api/v1/routes/claims.py`
- `tests/test_claim_extraction.py`
- `tests/test_claim_verification.py`
- `tests/test_sequential_claim_verification.py` — verifies sequential workflow integration

**Modified files:**
- `app/graph/nodes.py` — add claim_extraction_node calling claim_verifier service
- `app/graph/state.py` — add `claim_ids`, `verification_summary`, `verification_depth` fields
- `app/graph/workflow.py` — add claim_extraction_node to topology
- `app/services/research_workflow.py` — call claim_verifier after report generation (sequential path)
- `app/core/config.py` — add VERIFICATION_DEPTH, MAX_CLAIMS_PER_RUN
- `app/schemas/run.py` — add `verification_depth` to StartRunRequest and RunResponse
- `app/models/run.py` — add `verification_depth` column (server_default="basic")
- `app/api/v1/router.py` — register claims route
- `app/models/__init__.py` — import new models
- `alembic/versions/` — new migration

### Claim model fields

| Field | Type | Notes |
|-------|------|-------|
| id | String(36) PK | UUID |
| run_id | String(36) FK | FK research_runs (CASCADE) |
| report_id | String(36) FK | FK research_reports — nullable |
| claim_text | Text | The atomic claim statement |
| claim_type | String(50) | factual / statistical / causal / correlational / interpretative / prediction / opinion |
| originating_section | String(200) | "executive_summary" / "key_findings" / "observations" / etc. |
| is_high_impact | Boolean | True for statistical, causal, medical, controversial claims |
| created_at | DateTime | UTC |

### ClaimVerification model fields

| Field | Type | Notes |
|-------|------|-------|
| id | String(36) PK | UUID |
| claim_id | String(36) FK | FK claims (CASCADE) |
| run_id | String(36) FK | FK research_runs |
| verification_status | String(50) | supported / partially_supported / contradicted / insufficient_evidence / unverified / not_applicable |
| supporting_evidence_ids | Text | JSON array of EvidenceRecord IDs |
| contradicting_evidence_ids | Text | JSON array of EvidenceRecord IDs |
| reasoning_summary | Text | LLM-generated explanation |
| evidence_limitations | Text | Nullable |
| confidence | Float | 0.0–1.0 |
| verified_at | DateTime | UTC |

### Verification depth semantics

**Basic depth:**
- Source: `report.key_findings` list (3–8 items typically)
- Additional: any claim in `executive_summary` or `observations` flagged as `is_high_impact=True` (statistical, causal, medical, controversial)
- Cap: `MAX_CLAIMS_PER_RUN` (default 20)

**Thorough depth:**
- Source: LLM extraction from full report text (executive_summary + key_findings + observations)
- All claim types extracted and verified
- Cap: `MAX_CLAIMS_PER_RUN` (default 20)

**Claim prioritization in basic mode:** The claim extractor classifies `claim_type` and sets `is_high_impact=True` for: `statistical`, `causal`, any claim containing medical/scientific terminology. High-impact claims are verified even in basic mode if under the cap.

### Verification status semantics (precise definitions)

| Status | Meaning |
|--------|---------|
| `supported` | At least one evidence item directly and specifically supports the claim as stated |
| `partially_supported` | Evidence supports the general direction but not the specific claim text or scope |
| `contradicted` | At least one credible evidence item directly contradicts the claim |
| `insufficient_evidence` | No relevant evidence found — claim cannot be evaluated; does NOT mean the claim is false |
| `unverified` | Claim not yet processed (initial state) |
| `not_applicable` | Value judgment or subjective opinion — not a factual claim |

### Sequential workflow integration

After `generate_report()` completes in `run_research_workflow()`:
```python
# New Phase 4 addition
from app.services.claim_verifier import verify_claims_for_run
await verify_claims_for_run(db, run_id=run.id, report_id=report.id,
                            depth=run.verification_depth)
```
The run continues to `completed` status regardless of verification outcome — verification failure does not fail the run. Unverified claims are marked `unverified` in the database.

### Test requirements for M4.4

- Basic depth extracts 3–8 claims from key_findings
- Basic depth also captures high-impact claims from other sections
- Thorough depth extracts more claims than basic from the same report
- Claim type classification produces valid enum values only
- MAX_CLAIMS_PER_RUN cap is respected in both depths
- Claim verifier produces ClaimVerification with valid status
- `insufficient_evidence` is correctly used when no relevant evidence exists
- `not_applicable` applied to opinion claims, not forced into factual verification
- Sequential workflow completes with claim verification records in DB
- Multi-agent workflow also produces claim verification records
- `GET /runs/{run_id}/claims` returns claims with verification status
- All 166 existing tests pass

### Acceptance criteria

- All existing tests pass
- Claim extraction and verification tests pass
- Both sequential and multi-agent runs produce Claim + ClaimVerification records
- API returns 200 for `GET /runs/{run_id}/claims`

---

## Milestone 4.5 — Critic / Reviewer Agent

### Intent

Introduce a `critic_node` into the LangGraph graph. The Critic Agent evaluates research quality holistically after claims are verified. It produces a structured `CriticReview` with a clear recommendation that the Supervisor uses to decide the next step. The Critic applies **only to multi-agent runs**. The maximum number of Critic review cycles is 2 — but the system never forces approval.

### Termination behaviour

- If the **first review** recommends revision: Supervisor routes to the appropriate correction step (additional research, re-verification, or report revision).
- If the **second review** also recommends revision: the Supervisor sets the run's report status to `needs_attention` or `rejected` based on severity, terminates the review loop, and surfaces unresolved issues in the final report. **No forced approval.**
- The distinction between `needs_attention` (issues present but report usable) and `rejected` (report fails critical quality threshold) must be determined by the Critic's `overall_assessment` field.

### What changes

**New files:**
- `app/agents/critic.py` — Critic Agent implementation
- `app/models/critic_review.py` — CriticReview ORM
- `app/schemas/critic.py` — CriticReviewResponse, CriticDecision Pydantic schemas
- `app/api/v1/routes/reviews.py` — GET /runs/{run_id}/review endpoint
- `tests/test_critic_agent.py`

**Modified files:**
- `app/graph/workflow.py` — add critic_node to graph topology
- `app/graph/state.py` — add `critic_review_id`, `critic_decision`, `critic_cycles` fields
- `app/graph/nodes.py` — finalize_report_node routes to claim_extraction_node then critic_node
- `app/agents/supervisor.py` — add routing for Phase 4 Critic decisions
- `app/schemas/agent.py` — add Phase 4 decisions to SupervisorDecision allowed values
- `app/core/config.py` — add CRITIC_MAX_REVIEW_CYCLES (default 2)
- `app/api/v1/router.py` — register reviews route
- `app/models/__init__.py` — import CriticReview
- `alembic/versions/` — new migration

### Updated graph topology (after M4.5)

```
START → initialize_run → supervisor
supervisor → planning_node → supervisor
supervisor → research_node → supervisor
supervisor → finalize_report (draft)
finalize_report → claim_extraction_node
claim_extraction_node → critic_node
critic_node → supervisor (with critic context)
supervisor → planning_node          [request_additional_research]
supervisor → claim_extraction_node  [request_reverification]
supervisor → finalize_report        [revise_report]
supervisor → citation_validation    [approve_report]
supervisor → fail_workflow          [fail_workflow]
citation_validation → final_report → END
fail_workflow → END
```

### CriticReview model fields

| Field | Type | Notes |
|-------|------|-------|
| id | String(36) PK | UUID |
| run_id | String(36) FK | FK research_runs (CASCADE) |
| review_version | Integer | 1-based, increments per review cycle |
| overall_assessment | String(50) | "strong" / "adequate" / "weak" / "inadequate" |
| review_status | String(50) | "approved" / "needs_attention" / "rejected" / "failed" |
| recommended_action | String(50) | "approve_report" / "request_additional_research" / "request_reverification" / "revise_report" / "reject" |
| unsupported_claims | Text | JSON array of claim IDs or text |
| citation_issues | Text | JSON array |
| contradictory_findings | Text | JSON array |
| missing_evidence | Text | JSON array |
| source_quality_issues | Text | JSON array |
| reasoning_issues | Text | JSON array |
| review_summary | Text | Narrative summary |
| created_at | DateTime | UTC |

### Phase 4 Supervisor routing decisions (additions)

| Decision | Trigger | Routes to |
|----------|---------|-----------|
| `approve_report` | Critic approved | citation_validation |
| `request_additional_research` | Critic found missing evidence | planning_node |
| `request_reverification` | Critic found unsupported claims | claim_extraction_node |
| `revise_report` | Critic found reasoning/quality issues | finalize_report (regenerate) |
| `reject` | Second review: inadequate, cycle limit reached | mark report rejected → END |
| `mark_needs_attention` | Second review: weak issues unresolved | mark report needs_attention → citation_validation |

### ResearchReport status values (extended for Phase 4)

`draft` / `verified` / `needs_attention` / `rejected` — stored in new `review_status` column on `research_reports`.

### Test requirements for M4.5

- Critic produces valid CriticReview with correct field types and valid enum values
- Critic identifies at least one issue in a deliberately weak research output
- Critic returns "approved" for a strong research output
- Supervisor correctly routes "approve_report" → citation_validation
- Supervisor correctly routes "request_additional_research" → planning_node
- At cycle limit: second review recommends revision → report marked needs_attention (not approved)
- At cycle limit: second review marks inadequate → report marked rejected
- CriticReview persisted with correct review_version
- `GET /runs/{run_id}/review` returns latest review
- All 166 existing tests pass

### Acceptance criteria

- All existing tests pass
- Critic agent tests pass
- Graph compiles with updated topology
- Bounded cycle enforcement: no forced approvals
- Review API returns 200

---

## Milestone 4.6 — Citation Management and Validation

### Intent

Implement citation management as a **shared backend service** available to both sequential and multi-agent workflows. Structured Citation records link every report source reference to a traceable evidence-source chain. The citation validator runs before the final report is marked complete. Bibliography and formatted citations are generated deterministically from structured Source data — never from LLM memory.

### What changes

**New files:**
- `app/models/citation.py` — Citation ORM
- `app/services/citation_service.py` — citation creation and formatting
- `app/services/citation_validator.py` — pre-report validation checks (no LangGraph dependency)
- `app/schemas/citation.py` — CitationResponse, BibliographyResponse
- `app/api/v1/routes/citations.py`
- `tests/test_citation_management.py`

**Modified files:**
- `app/graph/nodes.py` — citation_validation_node calls citation_validator service
- `app/graph/state.py` — add `citation_validation_passed` field
- `app/services/research_workflow.py` — call citation_validator after claim verification (sequential path)
- `app/models/report.py` — add `has_validated_citations` (Boolean, default False), `review_status` (String, nullable)
- `app/api/v1/router.py` — register citations route
- `app/models/__init__.py` — import Citation
- `alembic/versions/` — new migration

### Citation model fields

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| id | String(36) PK | No | UUID |
| run_id | String(36) FK | No | FK research_runs (CASCADE) |
| report_id | String(36) FK | No | FK research_reports (CASCADE) |
| claim_id | String(36) FK | Yes | FK claims — linked when claim_verifier ran |
| evidence_id | String(36) FK | No | FK evidence_records |
| source_id | String(36) FK | Yes | FK sources — if Source exists |
| citation_key | String(50) | No | "[SOURCE 1]" — matches report label |
| page_reference | String(100) | Yes | "p. 42" / "pp. 15–17" |
| section_reference | String(200) | Yes | |
| url | String(2000) | Yes | |
| doi | String(200) | Yes | |
| apa_formatted | Text | Yes | Deterministic APA string |
| ieee_formatted | Text | Yes | Deterministic IEEE string |
| is_verified | Boolean | No | default False |
| validation_notes | Text | Yes | |
| created_at | DateTime | No | UTC |

### Citation validator checks

1. Every `[SOURCE N]` label in report's `sources_used` maps to an EvidenceRecord
2. Every referenced EvidenceRecord exists in the DB and has non-empty content
3. No fabricated citation keys (citation_key not in report's sources list)
4. If source_id is set, the Source record exists
5. URL passes `is_safe_url()` — no SSRF-unsafe internal URLs in bibliography
6. At least 1 citation per key_finding (warning if finding has no traceable source)
7. Claims with `verification_status = "contradicted"` are flagged in citation notes

### Traceability chain

```
Report [SOURCE N]
  → Citation (citation_key, page_reference, section_reference)
    → EvidenceRecord (content excerpt, section_name)
      → Source (url, publisher, doi, publication_date, is_peer_reviewed)
```

All links queryable via API. Exposed in frontend `CitationDetail` panel.

### Test requirements for M4.6

- Citation records created for each source reference in report
- Validator catches a fabricated citation key
- Validator catches a missing evidence_id reference
- is_verified=True for all citations passing validation
- Sequential workflow produces citation records
- Multi-agent workflow produces citation records
- `GET /runs/{run_id}/citations` returns full list with evidence context
- APA formatting correct for source with all fields present
- APA formatting degrades gracefully for source with missing author/date

### Acceptance criteria

- All existing tests pass
- Citation management tests pass
- Both workflows produce citation records
- Citation API returns 200 with is_verified status

---

## Milestone 4.7 — LLM Usage Tracking, Supervisor Integration and Graph Finalization

### Intent

Wire all Phase 4 components into the complete LangGraph workflow. Add LLM usage tracking to all workflows. Finalize `ResearchWorkflowState` with all Phase 4 fields. Confirm the Supervisor handles all 10 routing decisions. Run complete Phase 4 integration tests.

### LLM usage tracking

Introduce a lightweight `TrackedLLMProvider` wrapper around the existing `LLMProvider` that intercepts `complete()` calls and records:

- Call count increment
- Approximate token usage (input chars / 4, output chars / 4)
- Estimated cost based on `LLM_COST_PER_1K_TOKENS` config
- Call latency

Usage is accumulated per-run and written to `ResearchRun` columns at run completion. It is observability only — never gates features or modifies verification behaviour.

### New ResearchRun columns

| Column | Type | Notes |
|--------|------|-------|
| verification_depth | String(50) | server_default="basic" |
| llm_call_count | Integer | server_default=0 |
| total_tokens_used | Integer | server_default=0 |
| estimated_cost_usd | Float | server_default=0.0 |

### What changes

**New files:**
- `app/providers/tracked_llm.py` — TrackedLLMProvider wrapper
- `tests/test_phase4_workflow.py`

**Modified files:**
- `app/graph/state.py` — finalize all Phase 4 state fields
- `app/graph/workflow.py` — compile final Phase 4 graph
- `app/graph/nodes.py` — finalize claim_extraction_node, citation_validation_node
- `app/graph/executor.py` — update initial state, inject TrackedLLMProvider
- `app/services/research_workflow.py` — inject TrackedLLMProvider, write usage at completion
- `app/agents/supervisor.py` — add all Phase 4 routing decisions
- `app/schemas/run.py` — add Phase 4 fields to RunResponse
- `app/models/run.py` — add 4 new columns
- `alembic/versions/` — new migration (combined if possible)

### Complete Phase 4 state fields added to ResearchWorkflowState

| Field | Type | Notes |
|-------|------|-------|
| verification_depth | str | "basic" / "thorough" |
| claim_ids | Annotated[list[str], append_unique] | |
| verification_summary | dict / None | Summary of verification results |
| critic_review_id | str / None | Latest CriticReview ID |
| critic_decision | str / None | Latest Critic recommended_action |
| critic_cycles | int | Number of Critic reviews completed |
| citation_validation_passed | bool | |

### Complete routing decisions (all 10)

| Decision | Trigger | Routes to |
|----------|---------|-----------|
| `request_plan` | No plan exists | planning_node |
| `revise_plan` | Plan gaps | planning_node |
| `execute_next_task` | Tasks pending | research_node |
| `continue_research` | Same as execute_next_task | research_node |
| `complete_research` | Tasks done, request draft | finalize_report |
| `approve_report` | Critic approved | citation_validation |
| `request_additional_research` | Missing evidence | planning_node |
| `request_reverification` | Unsupported claims | claim_extraction_node |
| `revise_report` | Quality issues | finalize_report |
| `reject` | Critic cycle limit + inadequate | fail_workflow or final_report with rejected status |
| `mark_needs_attention` | Cycle limit + weak issues | citation_validation with needs_attention |
| `fail_workflow` | Unrecoverable error | fail_workflow_node |

### Acceptance criteria

- All existing tests pass
- Full Phase 4 integration test passes (GR4-001 through GR4-005)
- All 10+ routing decisions exercised in tests
- No forced approval at cycle limit
- LLM usage columns populated on completed runs

---

## Milestone 4.8 — Frontend Phase 4 Integration

### Intent

Extend the existing research workspace with five new panels. All panels are available to both sequential and multi-agent runs where the data exists. The Critic review panel is multi-agent only. All components follow the existing MAAR design system (Tailwind CSS, shadcn/ui, Lucide icons, slate/violet colour tokens).

### What changes

**New files:**
- `src/components/workspace/SourcePanel.tsx`
- `src/components/workspace/EvidenceExplorer.tsx`
- `src/components/workspace/ClaimVerificationPanel.tsx`
- `src/components/workspace/CriticReviewPanel.tsx` (multi-agent only — rendered conditionally)
- `src/components/workspace/CitationDetail.tsx`

**Modified files:**
- `src/lib/types/run.ts` — add Source, Evidence (extended), Claim, ClaimVerification, CriticReview, Citation, VerificationStatus types; add `verification_depth`, `llm_call_count`, `total_tokens_used`, `estimated_cost_usd` to ResearchRun
- `src/lib/api/runs.ts` — add getSources, getEvidence, getClaims, getCriticReview, getCitations
- `src/components/workspace/ResearchPanel.tsx` — add Phase 4 tabs when data available; show verification depth selector in ResearchForm
- `src/components/workspace/ResearchForm.tsx` — add verification depth radio/toggle (basic/thorough)
- `src/components/workspace/ResearchReportView.tsx` — render [SOURCE N] as clickable citation chips

### New frontend types

```typescript
type VerificationStatus =
  | 'supported' | 'partially_supported' | 'contradicted'
  | 'insufficient_evidence' | 'unverified' | 'not_applicable';

interface Source {
  id: string;
  title: string | null;
  url: string | null;
  doi: string | null;
  source_type: string;
  publisher: string | null;
  venue: string | null;
  publication_date: string | null;
  is_peer_reviewed: boolean;
  retrieval_provider: string;
  is_accessible: boolean;
  credibility_notes: string | null;
}

interface EvidenceItem {
  id: string;
  source_type: string;
  source_label: string;
  content: string | null;
  evidence_type: string;
  evidence_relationship: string;
  section_name: string | null;
  url: string | null;
  page_title: string | null;
  source: Source | null;
}

interface Claim {
  id: string;
  claim_text: string;
  claim_type: string;
  originating_section: string;
  is_high_impact: boolean;
  verification: ClaimVerification | null;
}

interface ClaimVerification {
  verification_status: VerificationStatus;
  reasoning_summary: string;
  confidence: number;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  evidence_limitations: string | null;
}

interface CriticReview {
  id: string;
  review_version: number;
  overall_assessment: string;
  review_status: string;
  recommended_action: string;
  review_summary: string;
  unsupported_claims: string[];
  citation_issues: string[];
  contradictory_findings: string[];
  missing_evidence: string[];
  source_quality_issues: string[];
}

interface Citation {
  id: string;
  citation_key: string;
  url: string | null;
  doi: string | null;
  page_reference: string | null;
  section_reference: string | null;
  apa_formatted: string | null;
  is_verified: boolean;
  evidence_excerpt: string | null;
  source: Source | null;
}
```

### UI component specifications

**SourcePanel:** Card list. Each card shows source_type badge, title, publisher/venue, publication_date, is_peer_reviewed badge, URL link. Accessible for both workflows.

**EvidenceExplorer:** Filter bar (relationship: all / supports / contradicts / qualifies). Card per evidence item: source_label, evidence_type badge, relationship badge, content excerpt (expandable), section_name, link to source. Accessible for both workflows.

**ClaimVerificationPanel:** One row per claim. Status badge (colour-coded: green=supported, amber=partial, red=contradicted, slate=insufficient/unverified). Click row to expand: claim_text, claim_type, reasoning_summary, confidence meter, supporting/contradicting evidence references. Accessible for both workflows.

**CriticReviewPanel:** Shown only for multi-agent runs. Overall assessment badge. Expandable sections: Unsupported Claims, Citation Issues, Contradictions, Missing Evidence, Source Quality Issues. Recommended action highlighted.

**CitationDetail:** Slide-out panel triggered by clicking [SOURCE N] in report. Shows: citation_key, apa_formatted, page_reference, section_reference, evidence excerpt (from EvidenceRecord), Source metadata including is_peer_reviewed. Traceability chain visualised: Report → Citation → Evidence → Source.

**ResearchForm:** Verification depth toggle (Basic / Thorough) shown below workflow mode selector. Available for both sequential and multi-agent.

### Acceptance criteria

- `npm run build` passes with no TypeScript errors
- All five components render in development mode
- Source panel visible after completed run (both workflows)
- Claim panel shows correct status badges
- Critic panel visible only for multi-agent runs
- [SOURCE N] citation chips clickable in report
- Verification depth selector visible in ResearchForm

---

## Milestone 4.9 — Testing, Integration Validation and Documentation

### Intent

Complete the test suite. Run full Phase 4 end-to-end validation. Measure evidence coverage and citation correctness. Update all documentation.

### What changes

**New files:**
- `tests/test_phase4_workflow.py` — full E2E with all Phase 4 components
- `tests/test_evaluation_metrics.py` — 5-fixture measurable evaluation corpus
- `tests/evaluation_fixtures/` — pre-written evidence, reports, and expected claim outcomes
- `docs/33_PHASE_4_AGENT_SPECIFICATIONS.md` — Critic Agent documentation
- `docs/34_PHASE_4_API_REFERENCE.md` — all new Phase 4 endpoints
- `maar-phase4-plan.md` — master plan with all milestones marked complete

**Modified files:**
- All Phase 4 planning docs updated to reflect actual implementation
- `backend/.env.example` — all new Phase 4 vars documented
- `README.md` — Phase 4 capabilities section added

### Evaluation metrics

| Metric | Definition | Measurement approach |
|--------|-----------|---------------------|
| Evidence coverage | % of claims with ≥1 supporting evidence | Computed on 5-fixture corpus |
| Citation correctness | % of citations validated as is_verified=True | 100% required |
| Unsupported claim rate | % claims with insufficient_evidence | Measured; no hard target |
| Contradiction detection | % of pre-labeled contradictions correctly flagged | Measured on fixture 2 and 4 |
| Workflow completion rate | % of runs reaching completed/needs_attention/rejected | Target > 90% |
| Forced approval absence | Runs where cycle limit forced approval | Must be 0% |

**Evaluation limitations documented:**
- All evaluation is mock-data based; real-world LLM output varies
- 5 fixtures are not statistically representative
- Human-labeled ground truth is narrow

### Phase 4 acceptance criteria

1. All existing 166 tests pass
2. All new Phase 4 tests pass (target ≥ 80 new tests)
3. `npm run build` passes with no TypeScript errors
4. E2E test: document upload → claim verification → critic review → final report with citations
5. Sequential workflow produces claim verification records
6. Multi-agent workflow produces claim verification + critic review records
7. Evidence coverage metric ≥ 80% on evaluation fixtures
8. Citation validator reports 100% verified citations on evaluation fixtures
9. Cycle limit never forces approval (0 occurrences in all test runs)
10. Phase 2 sequential workflow unaffected
11. Phase 3 multi-agent workflow unaffected
12. LLM usage tracked on all completed runs
13. Documentation updated

---

## Files Expected to Change by Milestone

| Milestone | New Files | Modified Files |
|-----------|-----------|----------------|
| M4.1 | chunk.py, chunk_service.py, document_processor.py, test_document_processing.py | models/__init__.py, document.py model, migration, evidence_normalizer.py, documents.py route, schemas/document.py, document_service.py |
| M4.2 | source.py, arxiv_search.py, semantic_scholar.py, source_service.py, schemas/source.py, routes/sources.py, test_source_providers.py | web_search.py, config.py, router.py, models/__init__.py, migration, .env.example |
| M4.3 | evidence_extractor.py, schemas/evidence.py, test_evidence_extraction.py | evidence.py model, evidence_normalizer.py, migration, researcher.py, routes/evidence.py (new) |
| M4.4 | claim.py, claim_verification.py, claim_service.py, claim_extractor.py, claim_verifier.py, schemas/claim.py, routes/claims.py, test_claim_extraction.py, test_claim_verification.py, test_sequential_claim_verification.py | nodes.py, state.py, workflow.py, config.py, schemas/run.py, models/run.py, research_workflow.py, router.py, models/__init__.py, migration |
| M4.5 | critic.py, critic_review.py, schemas/critic.py, routes/reviews.py, test_critic_agent.py | workflow.py, state.py, nodes.py, supervisor.py, schemas/agent.py, router.py, models/__init__.py, config.py, migration |
| M4.6 | citation.py model, citation_service.py, citation_validator.py, schemas/citation.py, routes/citations.py, test_citation_management.py | nodes.py, state.py, models/report.py, research_workflow.py, router.py, models/__init__.py, migration |
| M4.7 | tracked_llm.py, test_phase4_workflow.py | state.py, workflow.py, nodes.py, executor.py, supervisor.py, schemas/run.py, models/run.py, research_workflow.py, migration |
| M4.8 | 5 React components | types/run.ts, api/runs.ts, ResearchPanel.tsx, ResearchForm.tsx, ResearchReportView.tsx |
| M4.9 | test_evaluation_metrics.py, evaluation_fixtures/, docs/33, docs/34, maar-phase4-plan.md | All Phase 4 docs, .env.example, README.md |

---

## Database Migration Strategy

Phase 4 introduces 5 new tables and modifies 4 existing tables. Migrations will be consolidated where milestones proceed without interruption:

| Migration group | Milestone | Changes |
|----------------|-----------|---------|
| Migration A | M4.1 + M4.2 | Add document_chunks table, sources table; add 3 columns to uploaded_documents |
| Migration B | M4.3 | Add 7 columns to evidence_records |
| Migration C | M4.4 | Add claims table, claim_verifications table; add verification_depth to research_runs |
| Migration D | M4.5 | Add critic_reviews table |
| Migration E | M4.6 | Add citations table; add 2 columns to research_reports |
| Migration F | M4.7 | Add llm_call_count, total_tokens_used, estimated_cost_usd to research_runs |

Each migration: named FK constraints, server_default on all new non-nullable columns, working downgrade(), tested with `alembic downgrade -1` before milestone sign-off.

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Claim extraction produces empty list | High | Always fall back to extracting claims from key_findings list directly; never return zero claims for a non-empty report |
| LLM-based claim type classification inconsistent | Medium | Constrain output to enum values; default to "factual" on parse failure |
| arXiv/Semantic Scholar APIs unavailable | Low | MultiProviderSearch degrades gracefully — falls back to Tavily only |
| Critic Agent produces invalid structured output | Medium | One retry with stricter prompt; fall back to needs_attention status |
| Forced approval introduced through code bug | High | Explicit test for zero forced-approval occurrences across all cycle-limit test cases |
| LLM usage tracking adds latency | Low | Tracking is in-memory accumulation; DB write only at run completion |
| Phase 2 sequential workflow broken by claim verification | Medium | claim_verifier.py must have no LangGraph imports; integration tested separately |
| Graph topology too complex (12 nodes) | Medium | Linear topology — no parallelism; routing is deterministic |
| Frontend becomes cluttered with 5 new panels | Medium | All panels collapsed by default; progressive disclosure |
