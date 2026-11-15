# 34 — Phase 4 API Reference

**Project:** Multi-Agent Autonomous Researcher (MAAR)
**Phase:** 4 — Intelligence, Evidence Extraction, Fact-Checking and Citation Verification
**Status:** Complete
**Base URL:** `http://localhost:8000/api/v1`

---

## Overview

Phase 4 introduces 6 new API endpoint groups. All endpoints follow the same conventions as the existing MAAR API:

- Authentication: none (local development)
- Content-Type: `application/json`
- Error format: `{"detail": "..."}`
- Pagination: `offset` + `limit` query parameters

---

## New Phase 4 Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/projects/{project_id}/documents/{doc_id}/chunks` | GET | List document chunks for an uploaded document |
| `/projects/{project_id}/runs/{run_id}/sources` | GET | List sources collected for a run |
| `/projects/{project_id}/runs/{run_id}/evidence` | GET | List evidence records for a run |
| `/projects/{project_id}/runs/{run_id}/claims` | GET | List claims with verification status |
| `/projects/{project_id}/runs/{run_id}/review` | GET | Get the latest Critic review for a run |
| `/projects/{project_id}/runs/{run_id}/citations` | GET | Get citations/bibliography for a run |

---

## Document Chunks

### `GET /projects/{project_id}/documents/{doc_id}/chunks`

Returns all document chunks for an uploaded document.

**Path parameters:**
- `project_id` — UUID of the research project
- `doc_id` — UUID of the uploaded document

**Response `200 OK`:**
```json
{
  "document_id": "string",
  "items": [
    {
      "id": "string",
      "document_id": "string",
      "chunk_index": 0,
      "text": "string",
      "page_start": 1,
      "page_end": 1,
      "section_title": "Introduction",
      "heading_level": 1,
      "extraction_method": "pymupdf",
      "char_count": 847,
      "has_tables": false,
      "created_at": "2026-11-10T10:00:00Z"
    }
  ],
  "total": 12
}
```

**Error responses:**
- `404` — document not found
- `403` — document does not belong to the specified project

---

## Sources

### `GET /projects/{project_id}/runs/{run_id}/sources`

Returns structured source records collected during a research run. Sources are normalized representations of search results from all providers (Tavily, arXiv, Semantic Scholar).

**Query parameters:**
- `offset` (int, default 0)
- `limit` (int, default 50, max 100)

**Response `200 OK`:**
```json
{
  "run_id": "string",
  "items": [
    {
      "id": "string",
      "run_id": "string",
      "source_type": "web",
      "title": "string | null",
      "url": "string | null",
      "doi": "string | null",
      "authors": "string | null",
      "publisher": "string | null",
      "venue": "string | null",
      "publication_date": "string | null",
      "is_peer_reviewed": false,
      "retrieval_provider": "tavily",
      "is_accessible": true,
      "credibility_notes": "string | null",
      "retrieved_at": "2026-11-10T10:00:00Z",
      "created_at": "2026-11-10T10:00:00Z"
    }
  ],
  "total": 8
}
```

**Source type values:** `web`, `academic`, `news`, `document`

**Retrieval provider values:** `tavily`, `arxiv`, `semantic_scholar`

**Error responses:**
- `404` — run not found

---

## Evidence

### `GET /projects/{project_id}/runs/{run_id}/evidence`

Returns evidence records collected during a research run. Supports filtering by evidence type and relationship.

**Query parameters:**
- `offset` (int, default 0)
- `limit` (int, default 50, max 100)
- `evidence_type` (str, optional) — filter by type: `statistical`, `experimental`, `observational`, `expert_opinion`, `historical`, `official`, `survey`, `interpretative`, `other`
- `relationship` (str, optional) — filter by relationship: `supports`, `contradicts`, `qualifies`, `contextualizes`, `neutral`

**Response `200 OK`:**
```json
{
  "run_id": "string",
  "items": [
    {
      "id": "string",
      "run_id": "string",
      "source_type": "web",
      "source_label": "[SOURCE 1]",
      "content": "string | null",
      "relevance_score": 0.92,
      "fetch_status": "success",
      "url": "string | null",
      "page_title": "string | null",
      "retrieved_at": "2026-11-10T10:00:00Z | null",
      "document_id": "string | null",
      "chunk_index": null,
      "page_number": null,
      "evidence_type": "statistical",
      "evidence_relationship": "supports",
      "section_name": "Key Findings | null",
      "extraction_method": "llm | null",
      "extraction_confidence": 0.88,
      "source_id": "string | null"
    }
  ],
  "total": 24
}
```

**Error responses:**
- `404` — run not found

---

## Claims

### `GET /projects/{project_id}/runs/{run_id}/claims`

Returns all extracted claims for a run, including verification results when available.

**Query parameters:**
- `offset` (int, default 0)
- `limit` (int, default 50, max 100)

**Response `200 OK`:**
```json
{
  "run_id": "string",
  "items": [
    {
      "id": "string",
      "run_id": "string",
      "report_id": "string | null",
      "claim_text": "CO2 concentrations have increased from 280 ppm to over 420 ppm.",
      "claim_type": "statistical",
      "originating_section": "key_findings",
      "is_high_impact": true,
      "created_at": "2026-11-10T10:00:00Z",
      "verification": {
        "id": "string",
        "claim_id": "string",
        "run_id": "string",
        "verification_status": "supported",
        "supporting_evidence_ids": ["ev-id-1", "ev-id-2"],
        "contradicting_evidence_ids": [],
        "reasoning_summary": "string | null",
        "evidence_limitations": "string | null",
        "confidence": 0.92,
        "verified_at": "2026-11-10T10:00:00Z"
      }
    }
  ],
  "total": 12
}
```

**Verification status values:**
- `supported` — at least one evidence item directly supports the claim
- `partially_supported` — evidence supports the general direction but not the specific claim
- `contradicted` — evidence directly contradicts the claim
- `insufficient_evidence` — no relevant evidence found (does not mean the claim is false)
- `unverified` — claim not yet processed or LLM error occurred
- `not_applicable` — value judgment or opinion, not a verifiable factual claim

**Claim type values:** `factual`, `statistical`, `causal`, `correlational`, `interpretative`, `prediction`, `opinion`

**Error responses:**
- `404` — run not found

---

## Critic Review

### `GET /projects/{project_id}/runs/{run_id}/review`

Returns the most recent Critic Agent review for a multi-agent run.

**Notes:**
- Returns `404` for sequential workflow runs (no Critic Agent in sequential mode)
- Returns `404` if the run has not yet reached the review stage

**Response `200 OK`:**
```json
{
  "id": "string",
  "run_id": "string",
  "review_version": 1,
  "overall_assessment": "adequate",
  "review_status": "approved",
  "recommended_action": "approve_report",
  "unsupported_claims": [],
  "citation_issues": [],
  "contradictory_findings": [],
  "missing_evidence": [],
  "source_quality_issues": [],
  "reasoning_issues": [],
  "review_summary": "The report provides adequate coverage of the research question with well-supported key findings.",
  "created_at": "2026-11-10T10:05:00Z"
}
```

**`overall_assessment` values:** `strong`, `adequate`, `weak`, `inadequate`

**`review_status` values:** `approved`, `needs_attention`, `rejected`, `failed`

**`recommended_action` values:** `approve_report`, `request_additional_research`, `request_reverification`, `revise_report`, `reject`, `mark_needs_attention`

**Error responses:**
- `404` — run not found, or no review available (sequential runs or pre-review stage)

---

## Citations

### `GET /projects/{project_id}/runs/{run_id}/citations`

Returns the full bibliography for a research run. Citations link every `[SOURCE N]` reference in the report to a traceable evidence–source chain.

**Notes:**
- Available for both sequential and multi-agent runs
- Citation formatting is deterministic (APA/IEEE computed from structured `Source` data, never LLM-generated)
- Returns an empty list if the run has not completed claim verification and citation generation

**Response `200 OK`:**
```json
{
  "run_id": "string",
  "report_id": "string | null",
  "total": 8,
  "verified_count": 7,
  "citations": [
    {
      "id": "string",
      "run_id": "string",
      "report_id": "string",
      "claim_id": "string | null",
      "evidence_id": "string",
      "source_id": "string | null",
      "citation_key": "[SOURCE 1]",
      "page_reference": "string | null",
      "section_reference": "string | null",
      "url": "string | null",
      "doi": "string | null",
      "apa_formatted": "Author, A. (2023). Title. Journal, 12(4), 100–110.",
      "ieee_formatted": "[1] A. Author, \"Title,\" Journal, vol. 12, no. 4, pp. 100–110, 2023.",
      "is_verified": true,
      "validation_notes": "string | null",
      "created_at": "2026-11-10T10:00:00Z"
    }
  ]
}
```

**`is_verified` = `true` when all 7 citation validator checks pass:**
1. Citation key exists in the report text
2. Linked evidence record is present in DB
3. Evidence has `fetch_status = "success"` or `"partial"`
4. URL (if present) passes SSRF safety check
5. At least one claim or source is linked
6. Evidence is not contradicting the associated claim
7. Source is not flagged as inaccessible

**Error responses:**
- `404` — run not found

---

## Changes to Existing Endpoints

### `GET /projects/{project_id}/runs/{run_id}` — Updated Response

`RunResponse` now includes Phase 4 fields:

```json
{
  "...existing fields...",
  "verification_depth": "basic",
  "llm_call_count": 12,
  "total_tokens_used": 24800,
  "estimated_cost_usd": 0.0248
}
```

### `POST /projects/{project_id}/runs` — Updated Request

`StartRunRequest` now accepts:

```json
{
  "...existing fields...",
  "verification_depth": "basic"
}
```

`verification_depth` values: `basic` (default) | `thorough`

- `basic` — extracts claims from `key_findings` and high-impact claims only
- `thorough` — extracts claims from the full report text (executive summary, observations, contradictions)

---

## Error Response Format

All endpoints return errors in this format:

```json
{
  "detail": "Human-readable error message"
}
```

| HTTP Status | Meaning |
|------------|---------|
| `400` | Bad request (validation error at business logic level) |
| `404` | Resource not found |
| `422` | Request validation failure (Pydantic schema) |
| `500` | Unexpected server error |

---

## Interactive Documentation

The full interactive API documentation is available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`
