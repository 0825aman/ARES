# 45 — Report Generation and Export Design

## Phase 5 · Module M5.6

---

## 1. Purpose

This document specifies the design for the research report generation service and the export subsystem in MAAR Phase 5.

At the end of a successful research run, the system produces a structured `ResearchReport` record in the database (this already happens in Phase 4). Phase 5 adds:

1. **Report Versioning** — the ability to regenerate a report (e.g., after a revision loop), creating a new version while archiving the previous one.
2. **Export Service** — generating downloadable files from the report in three formats: PDF, DOCX, and Markdown.
3. **Export API** — endpoints to trigger export, check export status, and download the exported file.
4. **Frontend Export UI** — an export panel within the workspace that shows report versions and allows format selection.

---

## 2. Existing Phase 4 State

### What already exists

| Item | Details |
|---|---|
| `ResearchReport` model | `id, run_id, title, executive_summary, methodology, findings, conclusions, sources_used, confidence_score, word_count, created_at` |
| `UNIQUE(run_id)` constraint | Only one report per run — **must be relaxed** |
| `GET /reports?run_id=` | Returns report for a run |
| `GET /reports/{id}` | Returns individual report |
| `ResearchReportView.tsx` | Frontend component displaying report content |
| `python-docx` | Already installed, can write DOCX |
| `pypdf` | Already installed, reading only — not used for generation |

### What Phase 5 must add

- `version_number` column on `ResearchReport`
- `report_versions` archive table
- `export_records` table
- Remove or relax `UNIQUE(run_id)` on `ResearchReport` (replace with `UNIQUE(run_id, version_number)`)
- `reportlab` library for PDF generation
- Export service class
- Export API endpoints
- Export storage directory

---

## 3. Database Changes

### 3.1 ResearchReport changes

**New column:**
- `version_number` — INTEGER, NOT NULL, DEFAULT 1

**Constraint change:**
- Remove `UNIQUE(run_id)`
- Add `UNIQUE(run_id, version_number)`
- Add column `is_current` BOOLEAN DEFAULT TRUE — only one record per run has `is_current = TRUE` at any time

**Index:** `CREATE INDEX idx_research_reports_run_current ON research_reports(run_id, is_current)`

### 3.2 New table: `report_versions`

Archive table that snapshots a report before it is superseded.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | |
| `report_id` | UUID (FK → research_reports.id) | The report this is a version of |
| `run_id` | UUID | Denormalised for efficient querying |
| `version_number` | INTEGER | Version at time of archival |
| `archived_at` | DATETIME | When this version was superseded |
| `content_snapshot` | TEXT (JSON) | Full report content serialised to JSON |

The `content_snapshot` contains: `title, executive_summary, methodology, findings, conclusions, sources_used, confidence_score, word_count`.

This table is append-only — no updates after insert.

### 3.3 New table: `export_records`

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | |
| `run_id` | UUID (FK → research_runs.id) | |
| `report_id` | UUID (FK → research_reports.id) | |
| `format` | VARCHAR(10) | `pdf`, `docx`, `markdown` |
| `status` | VARCHAR(20) | `pending`, `generating`, `ready`, `failed` |
| `file_path` | TEXT | Relative path from EXPORT_DIR |
| `file_size_bytes` | INTEGER | Set when ready |
| `error_message` | TEXT | Set if failed |
| `created_at` | DATETIME | |
| `completed_at` | DATETIME | |

Index: `CREATE INDEX idx_export_records_run_id ON export_records(run_id)`

---

## 4. Export Storage

Files are stored on the local filesystem under a configurable base directory.

**Setting:** `EXPORT_DIR` in `backend/app/core/config.py`, default `./exports`

**Path pattern:**
```
exports/
  {run_id}/
    v{version_number}_{timestamp}_{format}.{ext}

Examples:
  exports/abc123/v1_20261112_120000_report.pdf
  exports/abc123/v1_20261112_120001_report.docx
  exports/abc123/v1_20261112_120002_report.md
  exports/abc123/v2_20261112_150000_report.pdf
```

The `file_path` stored in `export_records` is relative to `EXPORT_DIR`.

`EXPORT_DIR` must be created at application startup if it does not exist.

**Cleanup:** No automatic cleanup in Phase 5. Files persist indefinitely on local disk.

---

## 5. Export Service

### 5.1 Service class: `ExportService`

Location: `backend/app/services/export_service.py`

Responsibilities:
- Receive a `ResearchReport` ORM object and a format string
- Generate the file at the correct path
- Return the file path and file size
- Handle and propagate exceptions cleanly

### 5.2 PDF Generation (reportlab)

Uses `reportlab.platypus` for structured document generation.

**Document structure:**

```
Title (H1)
Confidence Score badge line

Executive Summary (H2)
[executive_summary text]

Methodology (H2)
[methodology text]

Findings (H2)
[findings text — rendered as paragraphs, bullet items if list]

Conclusions (H2)
[conclusions text]

Sources (H2)
[numbered list of source URLs/titles from sources_used JSON]

---
Generated by MAAR · Run ID: {run_id} · Version {version_number}
```

**Styling:**
- Font: Helvetica (built into reportlab, no external font files required)
- Page size: A4
- Margins: 2.5cm all sides
- H1: 20pt bold
- H2: 14pt bold, space before
- Body: 11pt, 1.2 leading
- Footer: 9pt italic, page number

No images, charts, or embedded media in Phase 5.

### 5.3 DOCX Generation (python-docx)

**Document structure mirrors PDF.**

Uses `python-docx` `Document` object:
- `add_heading(text, level=0)` for title
- `add_heading(text, level=1)` for section headings
- `add_paragraph(text)` for body text
- `add_paragraph(item, style='List Bullet')` for list items in sources

**Styling:**
- Default Office theme
- No custom fonts (relies on Word's default document font)
- Header: document title
- Footer: "Generated by MAAR — Page X"

### 5.4 Markdown Generation

Pure Python string formatting — no library required.

**Template:**
```markdown
# {title}

**Confidence Score:** {confidence_score:.0%}  
**Run ID:** {run_id}  
**Generated:** {created_at}  
**Version:** {version_number}  

---

## Executive Summary

{executive_summary}

## Methodology

{methodology}

## Findings

{findings}

## Conclusions

{conclusions}

## Sources

{numbered list of sources}

---
*Generated by MAAR (Multi-Agent Autonomous Researcher)*
```

---

## 6. API Endpoints

### 6.1 Trigger export

```
POST /api/v1/runs/{run_id}/export
```

**Request body:**
```json
{
  "format": "pdf | docx | markdown",
  "report_id": "uuid (optional — defaults to current report)"
}
```

**Behaviour:**
1. Validate `format`
2. Find the current report for this run (or the specified `report_id`)
3. Create an `ExportRecord` with `status = pending`
4. Trigger export generation synchronously (not background task — files are small, generation is fast, < 1s typical)
5. On success: update `ExportRecord` to `ready`, set `file_path` and `file_size_bytes`
6. On failure: update `ExportRecord` to `failed`, set `error_message`
7. Return export record

**Response:**
```json
{
  "id": "uuid",
  "run_id": "uuid",
  "report_id": "uuid",
  "format": "pdf",
  "status": "ready",
  "file_size_bytes": 48320,
  "created_at": "...",
  "completed_at": "...",
  "download_url": "/api/v1/runs/{run_id}/export/{export_id}/download"
}
```

**HTTP status:**
- 200 — export ready (synchronous)
- 404 — run or report not found
- 422 — invalid format
- 500 — generation failed (with error detail)

**Note on synchronous execution:** Report files are text-based and small (typically < 100KB). Synchronous generation avoids background task complexity. If a report is large (> 500KB of text), generation may take 1–2 seconds, which is acceptable for a user-triggered action.

### 6.2 Download export file

```
GET /api/v1/runs/{run_id}/export/{export_id}/download
```

Returns the file as a binary response with appropriate MIME type and `Content-Disposition: attachment` header.

| Format | MIME Type | Filename |
|---|---|---|
| pdf | application/pdf | `{run_title}_report.pdf` |
| docx | application/vnd.openxmlformats-officedocument.wordprocessingml.document | `{run_title}_report.docx` |
| markdown | text/markdown | `{run_title}_report.md` |

**HTTP status:**
- 200 — file returned
- 404 — export record not found or file missing from disk
- 409 — export status is not `ready` (still pending or failed)

### 6.3 List exports for a run

```
GET /api/v1/runs/{run_id}/exports
```

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "format": "pdf",
      "status": "ready",
      "file_size_bytes": 48320,
      "created_at": "...",
      "completed_at": "...",
      "download_url": "..."
    }
  ]
}
```

### 6.4 List report versions for a run

```
GET /api/v1/runs/{run_id}/reports
```

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "version_number": 2,
      "is_current": true,
      "title": "...",
      "confidence_score": 0.84,
      "word_count": 1240,
      "created_at": "..."
    },
    {
      "id": "uuid",
      "version_number": 1,
      "is_current": false,
      "title": "...",
      "confidence_score": 0.71,
      "word_count": 980,
      "created_at": "...",
      "archived_at": "..."
    }
  ]
}
```

---

## 7. Report Versioning Flow

When a research run completes a revision loop (CP-2 `revision_requested` → agents re-run → critic approves → report node runs again):

1. The `finalize_report_node` calls the report service
2. The service finds the existing `ResearchReport` for this `run_id` with `is_current = TRUE`
3. It archives the existing report to `report_versions` (snapshot content to JSON)
4. Updates `is_current = FALSE` on the old report
5. Creates a new `ResearchReport` with `version_number = old_version + 1` and `is_current = TRUE`

The frontend fetches the current report via `GET /reports?run_id=` which returns only `is_current = TRUE` records, so it automatically displays the latest version.

---

## 8. Frontend Export Panel

### 8.1 Location

The export panel is a new collapsible section within the Research Workspace, rendered below `ResearchReportView` when a report exists.

### 8.2 Layout

```
┌─ Export Report ─────────────────────────────────────────────┐
│ Current Version: v2  ·  Confidence: 84%  ·  1,240 words    │
│                                                             │
│ Download as:  [PDF]  [Word Document]  [Markdown]            │
│                                                             │
│ Previous exports:                                           │
│  • report_v2.pdf    48 KB    Downloaded just now  [↓]      │
│  • report_v1.docx   35 KB    2 hours ago         [↓]      │
└─────────────────────────────────────────────────────────────┘
```

### 8.3 Behaviour

- **[PDF], [Word Document], [Markdown] buttons** — each triggers `POST /export` with the respective format, then immediately triggers a browser download via the `download_url`
- While generating (brief): button shows spinner and is disabled
- On success: file downloads automatically; a new row appears in "Previous exports"
- On failure: inline error message below the button
- **[↓] (re-download) buttons** — trigger `GET /export/{id}/download` for an existing export record

### 8.4 Report Version Selector

If `version_number > 1`, a version selector dropdown appears:
```
Viewing: Version 2 (current)  ▼
  Version 1 — 2026-11-12 10:00
  Version 2 — 2026-11-12 15:00 (current)
```

Selecting a previous version loads that version's content into `ResearchReportView` for reading, but export always defaults to the current version unless explicitly changed.

---

## 9. Non-Goals for Phase 5

- No asynchronous background export queue (synchronous is sufficient)
- No cloud storage (S3, etc.) — local filesystem only
- No export scheduling or recurring exports
- No HTML export format
- No custom styling/branding options for PDF
- No password protection or watermarking
- No bulk export (multiple runs at once)
