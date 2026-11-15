# 32 — Phase 4 Architectural Decisions

**Project:** Multi-Agent Autonomous Researcher (MAAR)
**Phase:** 4 — Intelligence, Evidence Extraction, Fact-Checking and Citation Verification
**Date:** November 2026
**Revision:** 2 — Updated to reflect finalized architectural decisions

---

## ADR-401 — DocumentChunk as a First-Class ORM Model

### Decision

Introduce a `DocumentChunk` ORM model rather than continuing to use `EvidenceRecord` as the implicit chunk store.

### Context

In Phases 2 and 3, document text is extracted, chunked, and immediately converted to `EvidenceRecord` rows with `source_type="document"`. This works but conflates two different concepts: a structural chunk of a document (a permanent record of what was extracted) and an evidence item that was collected and used in a specific research run.

Phase 4 requires:
1. Reusing document chunks across multiple research runs without re-extraction.
2. Preserving structural metadata (page number, section title, heading level) that belongs to the chunk, not to the evidence.
3. Enabling evidence extraction to reference a specific chunk for full traceability.

### Chosen approach

Create `DocumentChunk` with its own lifecycle:
- Created when a document is uploaded and processed (once per document).
- Referenced by `EvidenceRecord` via `chunk_id` FK when a chunk is used as evidence in a run.
- Not deleted when a run is deleted (belongs to the document, not the run).

### Alternatives considered

| Alternative | Rejected because |
|-------------|-----------------|
| Add chunk metadata fields directly to EvidenceRecord | EvidenceRecord is run-scoped; chunk data should persist across runs |
| Store chunks as JSON blob in UploadedDocument | Not queryable; cannot filter by page number or section |
| Use a vector store (Qdrant, pgvector) for chunk storage | Introduces major infrastructure dependency; not needed for Phase 4 scope |

### Consequences

- UploadedDocument model gains `chunk_count`, `has_images`, `ocr_attempted` columns.
- `EvidenceRecord` gains a nullable `chunk_id` FK.
- Document processing runs `DocumentChunk` creation on upload, not deferred to research execution.
- Existing Phase 2 and Phase 3 runs do not have DocumentChunk records — backward compatible (chunk_id nullable).

---

## ADR-402 — Source as a First-Class ORM Model

### Decision

Introduce a `Source` ORM model as a normalized catalog of sources associated with a research run, separate from the `EvidenceRecord` model.

### Context

Currently, source information (URL, title, page title) is stored inline on each `EvidenceRecord`. This means:
- The same web page accessed twice in different tasks creates two EvidenceRecord rows with the same URL but potentially different titles.
- There is no place to store source-level metadata (publisher, author, publication date, DOI) that belongs to the source as a whole.
- Source credibility evaluation and deduplication across tasks are not possible.

### Chosen approach

Create a `Source` model scoped to a research run:
- One Source record per unique URL/DOI per run (run-level deduplication).
- Multiple `EvidenceRecord` rows can reference the same `Source`.
- Source credibility notes stored on the Source record, not duplicated across Evidence.
- `is_peer_reviewed` field explicitly tracked — never assumed for arXiv sources.

### Credibility approach

A numeric credibility score is explicitly rejected because:
1. It would require a defined and testable methodology.
2. Domain authority does not reliably predict source quality.
3. A single score hides important qualitative distinctions.

Instead, `credibility_notes` is a free-text field populated by factual observations (e.g., "Published by peer-reviewed journal", "arXiv preprint — not peer-reviewed", "Publication date: 2018 — may be outdated", "No author attribution"). The Critic Agent evaluates source quality as part of its holistic review.

### Alternatives considered

| Alternative | Rejected because |
|-------------|-----------------|
| Keep source info on EvidenceRecord | Cannot deduplicate across tasks; cannot store source-level metadata |
| Numeric credibility score | Methodology undefined; domain authority ≠ reliability |
| Source quality as a separate LLM call | Adds LLM cost per source; credibility_notes approach is cheaper and more transparent |

---

## ADR-403 — LLM-Based OCR for Scanned PDFs

### Decision

Use LLM vision capabilities to extract text from scanned/image-only PDFs, rather than installing local Tesseract. Implement detection and flagging in Phase 4; defer actual OCR extraction until a vision-capable model is configured.

### Context

The user explicitly chose the LLM-based approach to avoid a local Tesseract dependency.

### Implementation approach

1. Detect image-only PDFs: if pypdf extracts < 50 characters per page, flag it as a potential image page.
2. Set `has_images=True` on `UploadedDocument` for any document with low-text pages.
3. If `OCR_ENABLED=true` AND the LLM provider supports vision, render the PDF page as an image and pass it to the LLM.
4. If vision is not supported (current case with IBM watsonx Llama 3.3 70B), set `ocr_attempted=False` and flag the content gap in research findings.

### Current limitation

IBM watsonx.ai with `meta-llama/llama-3-3-70b-instruct` does not support image inputs. Therefore OCR via LLM will be implemented as a conditional branch that is active but does not execute until a vision model is configured. The flag infrastructure and detection logic will be complete in Phase 4.

### Alternatives considered

| Alternative | Rejected because |
|-------------|-----------------|
| Tesseract (local) | Requires local binary installation; user explicitly rejected |
| Skip OCR entirely | Would silently fail on scanned documents; detection and flagging are still needed |
| PyMuPDF | Adds dependency but doesn't provide OCR for image PDFs |

---

## ADR-404 — Configurable Verification Depth

### Decision

Implement claim verification depth as a per-run configurable parameter with two levels:
- **Basic** (default): verifies `key_findings` plus any high-impact claims (statistical, causal, medical, controversial) found elsewhere in the report.
- **Thorough**: extracts and verifies all identifiable factual claims from the full report.

### Context

Claim verification requires one LLM call per claim, plus evidence retrieval. For a 6-task research run with thorough verification, this could mean 15–30 LLM calls for verification alone.

The user confirmed: basic should remain the default to control API costs and latency. Thorough should be available when deeper academic verification is needed. Basic must still prioritize high-impact claims — it is not simply "fewer claims" but "most important claims".

### Verification depth semantics

| Depth | Source of claims | High-impact prioritization |
|-------|-----------------|---------------------------|
| basic | `key_findings` list + high-impact claims from other sections | Yes — statistical, causal, medical, controversial claims always included |
| thorough | LLM extraction from full report text (all sections) | All claims — cap applied |

**High-impact criteria for basic depth:**
- `claim_type` is `statistical` or `causal`
- Claim text contains medical/health/clinical terminology
- Claim text contains numerical assertions (percentages, quantities, rates)
- Claim text makes a causation assertion ("causes", "leads to", "results in")

### Workflow applicability

Verification depth applies to **both sequential and multi-agent workflows**. The `verification_depth` field is stored on `ResearchRun` and exposed in the API. Users can select depth per run from the frontend.

### Cost constraint

Cost optimization must never cause unsupported claims to be marked as verified. The cap (`MAX_CLAIMS_PER_RUN`) limits the number of claims verified, but claims that exceed the cap are marked `unverified`, not `supported`. This distinction is preserved in the database and API.

### Alternatives considered

| Alternative | Rejected because |
|-------------|-----------------|
| Always thorough | Too expensive for iterative development |
| Always basic | Insufficient for Phase 4 accuracy requirement |
| No verification | Violates core Phase 4 principle |
| Configurable per-claim threshold | Too complex for Phase 4; future Phase 5 consideration |

---

## ADR-405 — Multi-Provider Academic Search Architecture

### Decision

Implement a `MultiProviderSearch` dispatcher class that routes search queries to different providers (Tavily, arXiv, Semantic Scholar) based on research category and query-level signals. arXiv is not restricted to STEM categories — it is available to any category when enabled.

### Context

Phase 4 requires academic source retrieval to improve evidence quality. The original routing table restricted arXiv to science/technology/health. The user corrected this: arXiv should be available across categories, with routing determined by category AND query signals.

### Routing approach

Category determines the base provider set. Query signals (keyword heuristics in the search query) can elevate arXiv for any category where the query has an empirical or theoretical research character.

**Provider activation:**
- Tavily: always active (default for all categories)
- arXiv: activated by `ARXIV_ENABLED=true`, eligible for all categories; query signals determine priority
- Semantic Scholar: activated by `SEMANTIC_SCHOLAR_API_KEY` being set; eligible for all categories

**Category routing table:**

| Category | Tavily | arXiv (if enabled) | Semantic Scholar (if key set) |
|----------|--------|--------------------|-------------------------------|
| AI / CS / ML | ✅ | ✅ | ✅ |
| Physics / Math | ✅ | ✅ | ✅ |
| Biology / Medicine | ✅ | ✅ | ✅ |
| Economics / Finance | ✅ | Query-signal gated | ✅ |
| Policy / Social Science | ✅ | Query-signal gated | ✅ |
| History / Culture | ✅ | — | ✅ |
| General / Unclassified | ✅ | ✅ (fallback) | ✅ |

Query-signal gating: the query is scanned for keywords like "study", "research", "analysis", "model", "algorithm", "empirical", "experiment", "trial". If ≥2 signals found, arXiv is activated for that query.

### Source provenance transparency

arXiv sources must be stored with `is_peer_reviewed=False`. The system must never assume a preprint has passed peer review. This is surfaced in the frontend SourcePanel as a badge and in `credibility_notes`.

### Provider interface unchanged

All new providers implement the existing `WebSearchProvider` abstract class. The `SearchResult` dataclass gains `doi`, `authors`, `venue`, and `is_peer_reviewed` fields, but these are optional (`None` for Tavily results that don't have them).

### Alternatives considered

| Alternative | Rejected because |
|-------------|-----------------|
| Restrict arXiv to STEM only | User explicitly corrected this — economics, UBI, policy research may cite arXiv |
| Single hardcoded provider | Not configurable; cannot adapt to research category |
| PubMed for medical | Complex authentication; Semantic Scholar covers similar domain |
| CrossRef / OpenAlex | More complex pagination; defer to Phase 5 |

---

## ADR-406 — Critic Agent as a Sequential Graph Node with Explicit Termination Statuses

### Decision

Implement the Critic Agent as a single sequential node in the LangGraph graph. Maximum 2 review cycles. At the cycle limit, the Supervisor must **never force approval** — it must apply an explicit termination status (`needs_attention` or `rejected`) based on the Critic's assessment.

### Context

The original ADR stated: "If the second review also recommends revision: Supervisor forces approval to prevent infinite loops." The user corrected this: forcing approval converts an unresolved quality issue into an implicit endorsement, which violates the core Phase 4 principle.

### Revised termination behaviour

**After first review:**
- Approved: proceed to citation validation
- Revision recommended: route to appropriate correction (additional research / re-verify / revise report)

**After second review (cycle limit reached):**
- Approved: proceed to citation validation
- `overall_assessment = "weak"` (issues present but report is useful): mark report `needs_attention` → proceed to citation validation with unresolved issues visible
- `overall_assessment = "inadequate"` (critical quality failure): mark report `rejected` → terminate workflow
- In both cases, unresolved issues from the CriticReview record remain visible in the final report and API

### Why this matters

A system that auto-approves poor research at the cycle limit is indistinguishable from a system that never reviews at all. `needs_attention` and `rejected` are explicit, visible outcomes that communicate honest uncertainty to users.

### Bounded execution guarantee

The maximum number of supervisor routing cycles is `MAX_SUPERVISOR_CYCLES` (existing config, default 3). The additional Phase 4 routing decisions (approve, revise, request_research, etc.) all count toward this limit. Phase 4 also adds `CRITIC_MAX_REVIEW_CYCLES=2` as a separate counter tracked in state as `critic_cycles`.

### Alternatives considered

| Alternative | Rejected because |
|-------------|-----------------|
| Force approval at cycle limit | Converts unresolved quality issue into implicit endorsement — violates Phase 4 principle |
| No cycle limit | Potential infinite loop; unbounded LLM costs |
| Three review cycles | Marginally better quality but tripled latency and cost for the review phase |
| Critic as external service | Adds infrastructure; graph executor is the right boundary |

---

## ADR-407 — Claim Verification as a Reusable Workflow-Independent Service

### Decision

Implement claim verification as a standalone backend service (`claim_verifier.py`) with no imports from `app.graph.*`. Both the sequential workflow and the multi-agent workflow call this service with the same interface.

### Context

The original design restricted claim verification to multi-agent runs only. The user corrected this: claim verification should be available to sequential runs as well, and the service must not be coupled to LangGraph internals.

### Service interface

```python
async def verify_claims_for_run(
    db: AsyncSession,
    run_id: str,
    report_id: str,
    depth: str = "basic",
) -> VerificationSummary:
    """Extract and verify claims for a completed run.

    Works identically whether called from:
    - run_research_workflow() (sequential, Phase 2 path)
    - claim_extraction_node() (multi-agent, LangGraph node)

    Returns VerificationSummary — not stored in graph state, only used
    for logging and summary reporting.
    """
```

### Sequential workflow integration

After `generate_report()` in `run_research_workflow()`, the service is called directly:
```python
await verify_claims_for_run(db, run_id=run.id, report_id=report.id, depth=run.verification_depth)
```
The run continues to `completed` status regardless of verification outcome. Unverified claims are marked `unverified` — verification failure does not fail the run.

### Multi-agent workflow integration

A `claim_extraction_node` in the LangGraph graph calls `verify_claims_for_run()` and writes the returned `claim_ids` to state. The Supervisor then routes based on the summary.

### Shared schema

`ClaimResponse`, `ClaimVerificationResponse`, and `VerificationStatus` types are shared between both workflows and exposed identically through the API regardless of which workflow generated them.

### Alternatives considered

| Alternative | Rejected because |
|-------------|-----------------|
| Claim verification as LangGraph-only | Excludes sequential workflow users |
| Separate claim_verifier implementations | Code duplication; inconsistent schemas |
| Claim verification in report_generator | Conflates report writing with verification |

---

## ADR-408 — Citation Management as a Shared Service, Not Multi-Agent Only

### Decision

Implement citation management as a shared backend service callable from both sequential and multi-agent workflows. Bibliography and citation formatting are generated deterministically from structured Source data — never from LLM memory.

### Context

The original design introduced citation validation only in the multi-agent graph. The user's finalized decisions specify that citation management should be available to both workflows.

### Traceability chain

```
Report [SOURCE N]
  → Citation record (citation_key, page_reference, section_reference)
    → EvidenceRecord (content excerpt, section_name)
      → Source record (url, publisher, doi, publication_date, is_peer_reviewed)
```

This chain is queryable via API for both sequential and multi-agent runs. The frontend `CitationDetail` panel navigates this chain regardless of workflow mode.

### Deterministic APA formatting

```python
def format_apa(source: Source, evidence: EvidenceRecord) -> str:
    author = source.authors[0] if source.authors else "Unknown Author"
    year = source.publication_date[:4] if source.publication_date else "n.d."
    title = source.title or evidence.page_title or "Untitled"
    publisher = source.publisher or ""
    url = source.url or ""
    return f"{author}. ({year}). {title}. {publisher}. {url}"
```

Formatting degrades gracefully for sources with missing metadata (uses "Unknown Author", "n.d.", etc.) rather than failing.

### Alternatives considered

| Alternative | Rejected because |
|-------------|-----------------|
| Citations multi-agent only | Sequential run users cannot trace report sources |
| LLM-generated bibliography | May fabricate metadata; explicit violation of Phase 4 principle |
| No structured citations | Cannot provide user-navigable traceability |

---

## ADR-409 — Backward Compatibility Strategy for Phase 4 Schema Changes

### Decision

All Phase 4 database schema changes must be backward compatible with Phase 2 and Phase 3 research runs stored in the existing database.

### Implementation rules

1. **New tables**: DocumentChunk, Source, Claim, ClaimVerification, CriticReview, Citation — no backward compatibility concerns; they simply have no rows for pre-Phase 4 runs.

2. **New columns on existing tables**: All nullable, or with `server_default` values.

3. **No column renames or type changes**.

4. **Migration reversibility**: Every migration must include a working `downgrade()` function.

5. **Sequential workflow backward compatibility**: `run_research_workflow()` continues to work without Phase 4 models. Phase 4 components are called optionally after Phase 2 logic completes.

6. **Phase 3 runs**: Existing Phase 3 runs do not have claim or citation records — those fields are nullable.

### Column additions table

| Table | New Column | Default | Notes |
|-------|-----------|---------|-------|
| research_runs | verification_depth | "basic" | server_default |
| research_runs | llm_call_count | 0 | server_default |
| research_runs | total_tokens_used | 0 | server_default |
| research_runs | estimated_cost_usd | 0.0 | server_default |
| uploaded_documents | chunk_count | 0 | server_default |
| uploaded_documents | has_images | false | server_default |
| uploaded_documents | ocr_attempted | false | server_default |
| evidence_records | source_id | null | Nullable FK |
| evidence_records | chunk_id | null | Nullable FK |
| evidence_records | evidence_type | "other" | server_default |
| evidence_records | evidence_relationship | "neutral" | server_default |
| evidence_records | section_name | null | Nullable |
| evidence_records | extraction_method | null | Nullable |
| evidence_records | extraction_confidence | null | Nullable |
| research_reports | verification_summary | null | Nullable TEXT |
| research_reports | critic_review_id | null | Nullable FK |
| research_reports | review_status | null | Nullable |
| research_reports | has_validated_citations | false | server_default |

---

## ADR-410 — LLM Usage Tracking as Observability Only

### Decision

Implement LLM usage tracking (call count, token usage, estimated cost, latency) for all research runs as observability infrastructure. Usage tracking never gates features, modifies routing decisions, or degrades verification quality.

### Context

The user requires: "Track LLM provider, model, token usage, API calls, latency, errors and estimated cost per research run." Simultaneously: "Ensure that cost optimization never compromises evidence traceability or causes unsupported claims to be marked as verified."

### Implementation approach

Introduce a `TrackedLLMProvider` wrapper that decorates any `LLMProvider` implementation:
- Intercepts each `complete()` call
- Records: call timestamp, input length (chars), output length (chars), latency (ms), error (if any)
- Accumulates totals in memory per-run
- Writes to `ResearchRun` columns at run completion (single DB write, not per-call)

Token approximation: `chars / 4` (industry standard approximation). This is an estimate, not an exact count. Logged as such.

Cost approximation: `(total_tokens / 1000) * LLM_COST_PER_1K_TOKENS`. Set to 0.0 by default (free/internal models). Configurable per-deployment.

### Invariants

- A claim marked `insufficient_evidence` must stay `insufficient_evidence` regardless of cost pressure.
- The `MAX_CLAIMS_PER_RUN` cap prevents unbounded LLM spend, but claims that exceed the cap are marked `unverified`, not `supported`.
- Tracking is always enabled (`ENABLE_LLM_USAGE_TRACKING=true` default) but can be disabled for testing environments.

### Alternatives considered

| Alternative | Rejected because |
|-------------|-----------------|
| No usage tracking | Violates Phase 4 observability requirement |
| Per-call DB writes | Too much write amplification; accumulate in memory instead |
| External metrics service (Prometheus, Datadog) | Introduces infrastructure dependency; local-first requirement |
| LangSmith-only tracking | LangSmith is optional; tracking must work without it |

---

## ADR-411 — Evaluation Metrics Approach

### Decision

Implement a small hand-labeled evaluation corpus (5 research fixtures) with expected claim outcomes. Measure Phase 4 accuracy against this corpus. Never claim high accuracy based solely on unit test pass rates.

### Evaluation fixtures

1. Well-supported claims: question with strong, consistent evidence. Expected: ≥80% `supported`.
2. Mixed evidence: question with both supporting and contradicting sources. Expected: mix of `supported` and `contradicted`.
3. Limited evidence: question where evidence is sparse. Expected: several `insufficient_evidence`.
4. Medical conflicting studies: health claim with conflicting research. Expected: `partially_supported` or `contradicted`.
5. Causation vs correlation: a causal claim where evidence shows only correlation. Expected: `partially_supported` with limitation noted; causation assertion not verified.

### Metrics computed

| Metric | Definition |
|--------|-----------|
| Evidence coverage | Claims with ≥1 supporting evidence / total claims |
| Citation correctness | Verified citations / total citations |
| Unsupported claim rate | Claims with `insufficient_evidence` / total claims |
| Contradiction detection | Pre-labeled contradictions correctly flagged / total |
| Workflow completion rate | Runs reaching a terminal status / attempts |
| Forced approval absence | Runs where cycle limit forced approval (must = 0) |

### Documented limitations

- All evaluation is mock-data based; real LLM output will vary.
- 5 fixtures are not statistically representative.
- Human-labeled ground truth is narrow and does not cover all claim types.
- Real-world evidence quality depends on Tavily results and external APIs.
