# 43 — Source Explorer and Evidence Viewer Design

## Phase 5 · Module M5.3 & M5.4

---

## 1. Purpose

This document specifies the design for two closely related frontend panels that already have partial Phase 4 implementations:

- **Source Explorer** — browse, filter, and inspect all web/document sources collected during a research run
- **Evidence Viewer** — browse evidence items linked to claims, filter by relevance score, and inspect the full evidence detail with claim associations

Phase 5 upgrades these panels from static REST-polled displays into live, SSE-aware components that update as the research graph executes, and adds expanded detail views, filtering capabilities, and cross-linking between sources and evidence.

---

## 2. Existing Phase 4 State

### What already exists

| Component | Location | Current capability |
|---|---|---|
| `SourcePanel.tsx` | `workspace/SourcePanel.tsx` | Lists sources from `GET /sources?run_id=` — static, polled |
| `EvidenceExplorer.tsx` | `workspace/EvidenceExplorer.tsx` | Lists evidence items from `GET /evidence?run_id=` — static, polled |
| `CitationDetail.tsx` | `workspace/CitationDetail.tsx` | Shows one citation's full metadata |
| Source API routes | `api/v1/routes/sources.py` | `GET /sources`, `GET /sources/{id}` |
| Evidence API routes | `api/v1/routes/evidence.py` | `GET /evidence`, `GET /evidence/{id}` |
| Source model | `models/source.py` | `id, run_id, url, title, content_type, reliability_score, fetched_at, content_preview` |
| Evidence model | `models/evidence.py` | `id, run_id, source_id, claim_id, evidence_type, content, relevance_score, created_at` |

### What Phase 5 must add

1. Live update when SSE events include `source_added` or `evidence_added` event types
2. Filter bar (Source Explorer: by content_type, reliability score; Evidence Explorer: by relevance score, evidence_type)
3. Expanded detail drawer/panel for individual source and evidence inspection
4. Cross-link: from evidence item → open its parent source detail
5. Cross-link: from source detail → list all evidence derived from it
6. Pagination or virtual scrolling for runs with many sources/evidence items

---

## 3. Source Explorer — Design

### 3.1 Data Contract

**Existing endpoint** — no changes required:

```
GET /api/v1/sources?run_id={run_id}&page={n}&page_size={20}
```

**Response shape (already implemented):**
```json
{
  "items": [
    {
      "id": "uuid",
      "run_id": "uuid",
      "url": "https://...",
      "title": "Source Title",
      "content_type": "web_page | pdf | document",
      "reliability_score": 0.87,
      "fetched_at": "2026-11-12T10:00:00Z",
      "content_preview": "First 300 characters of content..."
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

**Individual source — already exists:**
```
GET /api/v1/sources/{source_id}
```
Returns full content and list of evidence derived from this source.

### 3.2 Live Update Behaviour

When the SSE stream (M5.1) emits an event with `event_type: "source_added"`, the Source Explorer must:

1. Check if the `run_id` matches the currently open workspace
2. Append the new source to the top of the local list without a full refetch
3. Briefly highlight the new row with a subtle entry animation (fade-in, not slide)
4. Update the source count badge in the panel header

The SSE payload for `source_added` will carry:
```json
{
  "event_type": "source_added",
  "run_id": "uuid",
  "data": { /* same shape as a single source item */ }
}
```

### 3.3 Filter Bar

Filters are applied client-side for the currently loaded page, and also passed as query params when fetching.

| Filter | Type | Values |
|---|---|---|
| Content Type | Multi-select chip | web_page, pdf, document, all |
| Min Reliability | Range slider | 0.0 – 1.0, default 0.0 |
| Search | Text input | Matches title or URL substring |

Filters are stateless — they reset when navigating away. No URL state persistence required for Phase 5.

### 3.4 Source Detail Drawer

Clicking a source row opens a right-side drawer (not a new page). The drawer contains:

**Header:**
- Source title (bold)
- URL with external link icon
- Content type badge
- Reliability score as a progress bar with percentage

**Body sections:**
1. **Content Preview** — full `content_preview` in a scrollable monospace block
2. **Metadata** — fetched_at timestamp, content_type, source_id
3. **Derived Evidence** — list of evidence items linked to this source, each as a compact card with relevance score and evidence type; clicking an evidence card cross-links to the Evidence Viewer

**Footer:**
- Close button

The drawer uses shadcn/ui `Sheet` component (already installed).

### 3.5 Layout

```
┌─ Source Explorer ────────────────────────────────┐
│ [Sources  42]  [Filter ▼]  [Search ________________] │
│                                                   │
│ ● example.com — Web Research          Score: 0.91 │
│   "First 200 chars of content..."   web_page  2m ago │
│                                                   │
│ ● arxiv.org — Peer-Reviewed Paper     Score: 0.88 │
│   "Abstract text preview..."           pdf  5m ago │
│                                                   │
│ [Load more]                                       │
└───────────────────────────────────────────────────┘
```

Each row:
- Domain favicon (or generic icon)
- Title (bold)
- Content type badge (small, muted)
- Reliability score (coloured dot or progress)
- Time since fetched (relative)
- Content preview (one line, truncated)

Empty state: "No sources collected yet. Sources will appear here as the research agents browse the web."

---

## 4. Evidence Viewer — Design

### 4.1 Data Contract

**Existing endpoint:**
```
GET /api/v1/evidence?run_id={run_id}&page={n}&page_size={20}
```

**Response shape (already implemented):**
```json
{
  "items": [
    {
      "id": "uuid",
      "run_id": "uuid",
      "source_id": "uuid",
      "claim_id": "uuid or null",
      "evidence_type": "supporting | contradicting | neutral",
      "content": "The actual evidence text...",
      "relevance_score": 0.92,
      "created_at": "2026-11-12T10:00:00Z"
    }
  ],
  "total": 18,
  "page": 1,
  "page_size": 20
}
```

### 4.2 Live Update Behaviour

When SSE emits `evidence_added`:

1. Prepend new evidence item to the list
2. Brief highlight animation on new row
3. Update evidence count badge

SSE payload for `evidence_added`:
```json
{
  "event_type": "evidence_added",
  "run_id": "uuid",
  "data": { /* same shape as single evidence item */ }
}
```

### 4.3 Filter Bar

| Filter | Type | Values |
|---|---|---|
| Evidence Type | Multi-select chip | supporting, contradicting, neutral, all |
| Min Relevance | Range slider | 0.0 – 1.0, default 0.0 |
| Linked to Claim | Toggle | All / Linked / Unlinked |

### 4.4 Evidence Detail Drawer

Clicking an evidence row opens a right-side `Sheet` drawer:

**Header:**
- Evidence type badge (colour-coded: green = supporting, red = contradicting, grey = neutral)
- Relevance score badge

**Body:**
1. **Evidence Content** — full text in a scrollable readable block
2. **Linked Claim** — if `claim_id` is set, show the claim text with a link that opens the Claim Verification panel filtered to that claim
3. **Source Origin** — source title, URL, and reliability score; clicking opens the Source Explorer drawer for that source
4. **Metadata** — evidence_id, created_at

### 4.5 Layout

```
┌─ Evidence Viewer ─────────────────────────────────┐
│ [Evidence 18]  [Type ▼]  [Relevance ▶───── 0.7+]  │
│                                                    │
│ ✓ Supporting  · Relevance: 0.92                    │
│   "Studies confirm that AI-assisted..."            │
│   Source: arxiv.org · Claim: C-001                 │
│                                                    │
│ ✗ Contradicting  · Relevance: 0.78                 │
│   "However, critics argue that..."                 │
│   Source: example.com · No linked claim            │
│                                                    │
└────────────────────────────────────────────────────┘
```

Row colour coding:
- Supporting: left border green
- Contradicting: left border red/rose
- Neutral: left border grey/slate

Empty state: "No evidence collected yet. Evidence items will appear here as agents analyse sources."

---

## 5. Cross-Component Linking

Both drawers must support being opened from other panels. The mechanism is a shared context or a simple state prop passed through the workspace page:

```
WorkspacePage
  └─ activeSourceId: string | null  (opens SourcePanel drawer)
  └─ activeEvidenceId: string | null  (opens EvidenceViewer drawer)
```

When `ClaimVerificationPanel` or `CriticReviewPanel` references a source or evidence item, clicking it sets the relevant workspace-level state, which causes the appropriate drawer to open. No router change required — all within the workspace page.

---

## 6. Pagination Strategy

Both panels use a "Load more" button pattern (not infinite scroll):

- Initial fetch: page 1, page_size 20
- "Load more" appends next page to existing list
- When SSE pushes new items, they are prepended to the existing list (no re-fetch required)
- Total count shown in header badge always reflects server total, not local list length

This avoids complexity of virtual scrolling for Phase 5 while handling typical research run sizes (usually < 100 sources, < 200 evidence items).

---

## 7. Component Responsibilities Summary

| Component | Phase 4 state | Phase 5 additions |
|---|---|---|
| `SourcePanel.tsx` | Lists sources | Filter bar, drawer, SSE live update, cross-links |
| `EvidenceExplorer.tsx` | Lists evidence | Filter bar, drawer, SSE live update, cross-links |
| `SourceDetailDrawer.tsx` | Does not exist | New component — Sheet drawer for source detail |
| `EvidenceDetailDrawer.tsx` | Does not exist | New component — Sheet drawer for evidence detail |
| `CitationDetail.tsx` | Shows citation | No changes required |

---

## 8. Non-Goals for Phase 5

- No full-text search across source content (future phase)
- No source de-duplication UI
- No manual source addition by user
- No evidence flagging or annotation by user
- No export of individual source or evidence items (covered by Report Export module)
