# 16 — Frontend Implementation Specification

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 2 — First End-to-End Research Workflow
**Status**: Planning

---

## 1. Design Principles

- Preserve the Phase 1 visual language: dark sidebar (`#0F172A`), white cards, `bg-slate-50` content area, Inter font.
- Extend the existing workspace page — do not rebuild it.
- Replace the three `PlaceholderSection` components with live functionality.
- Keep the `AppShell`, `Sidebar`, `PageHeader`, and all Phase 1 components unchanged.
- All new components follow the existing `maar-card`, `section-label`, and `page-content` CSS class conventions.

---

## 2. Workspace Page Changes

The existing [`/projects/[id]/page.tsx`](../frontend/src/app/projects/%5Bid%5D/page.tsx) currently renders three `PlaceholderSection` components in the main content area.

**Phase 2 change**: Replace those three placeholders with a single `<ResearchPanel projectId={project.id} researchQuestion={project.research_question} />` component.

The rest of the workspace layout (PageHeader, WorkspaceHeader, ProjectDetails sidebar) is unchanged.

---

## 3. ResearchPanel Component

**File**: `src/components/workspace/ResearchPanel.tsx`
**Type**: Client Component (`'use client'`)

**Props**:
```typescript
interface ResearchPanelProps {
  projectId: string;
  researchQuestion: string;
}
```

**State logic**: On mount, fetches `GET /api/v1/projects/{projectId}/runs` to determine current state.

**Renders one of three states**:

| Condition | Renders |
|---|---|
| No runs exist for this project | `<ResearchForm>` (submission panel) |
| At least one run is `pending` or `running` | `<RunStatusCard>` (progress panel) |
| Most recent run is `completed` or `failed` | `<ResearchReport>` or `<RunFailedCard>` + `<RunHistory>` below |

**Tab design**: When runs exist, show two tabs at the top of the panel:
- **"Current Run"** — shows status card or completed report
- **"History"** — shows `<RunHistory>` list

Use shadcn/ui `Tabs` component (must be added in Phase 2).

---

## 4. ResearchForm Component

**File**: `src/components/workspace/ResearchForm.tsx`
**Type**: Client Component

**Layout**: A white `maar-card` with sections for:
1. Research question input (pre-filled from `props.researchQuestion`, editable)
2. Source selection (checkboxes: "Search the web", "Use uploaded documents")
3. Document upload area (shown only when "Use uploaded documents" is checked)
4. Start Research button

### 4.1 Research Question Input

- `<Textarea>` pre-filled with the project's `research_question`
- Label: "Research Question"
- Optional description: "You can refine the research question before starting."
- Max 1000 characters; character count shown below.
- Validation: required, non-empty after trimming.

### 4.2 Source Selection

Two checkboxes:
- ☑ **Search the web** (checked by default)
- ☐ **Use uploaded documents**

If neither is checked and the user clicks Start, show inline error: *"Select at least one information source."*

### 4.3 FileUploadArea Component

**File**: `src/components/workspace/FileUploadArea.tsx`
**Shown**: Only when "Use uploaded documents" is checked.

**Layout**:
- Dashed-border drop zone with a cloud-upload icon and "Drag files here or click to browse" text.
- Hidden `<input type="file" multiple accept=".pdf,.docx,.txt">`.
- Clicking the zone triggers the file input.
- Drag-over state: border turns blue, background lightens.

**Selected file list**: Below the drop zone, each selected file shows:
- File type icon (📄 for PDF, 📝 for DOCX/TXT)
- Filename (truncated at 40 chars)
- File size (formatted: "204 KB")
- Red ✕ remove button

**Validation**:
- Extension must be `.pdf`, `.docx`, or `.txt`. Invalid files show: *"filename.xyz — Unsupported type. Only PDF, DOCX, TXT accepted."* (red, below the file list)
- File size > `MAX_UPLOAD_SIZE_MB` shows: *"filename.pdf — Exceeds 20 MB limit."*
- Invalid files are shown in the error list but not added to the upload queue.

**Upload timing**: Files are uploaded immediately when added (eager upload), returning `document_id`s. This allows the form to show upload progress before the user clicks Start. On upload failure, the file is shown with a red error state and removed from the queue.

### 4.4 Start Research Button

- Label: "Start Research"
- Icon: `<FlaskConical>` (Lucide)
- Disabled while uploading files or submitting.
- During submission: spinner + "Starting…"
- On success: transitions the panel to `<RunStatusCard>`.
- On error: shows toast notification.

---

## 5. RunStatusCard Component

**File**: `src/components/workspace/RunStatusCard.tsx`
**Type**: Client Component (polls API)

**Props**:
```typescript
interface RunStatusCardProps {
  projectId: string;
  runId: string;
  initialStatus: RunStatus;
  initialStage: string | null;
}
```

**Layout**: White `maar-card` with:

```
┌─────────────────────────────────────────┐
│  🔬  Research in Progress               │
│                                         │
│  ◉ Searching the web...                 │  ← current_stage from API
│                                         │
│  [●●●●●●●●○○] Stage 3 of 7             │  ← visual stage indicator
│                                         │
│  Started: 2 minutes ago                 │
│                                [Refresh]│
└─────────────────────────────────────────┘
```

**Polling**: `useEffect` + `setInterval(3000)`. Calls `GET /api/v1/projects/{projectId}/runs/{runId}`.

**Stage progress indicator**: Map `current_stage` strings to step numbers (1–7) to render a horizontal step bar. Stages: Initializing → Processing documents → Searching the web → Collecting evidence → Synthesizing findings → Generating report → Complete.

**On `status = completed`**: Clear interval → call `router.refresh()` to reload the RSC parent → panel transitions to `<ResearchReport>`.

**On `status = failed`**: Clear interval → render `<RunFailedCard>` showing `error_message`.

**On backend unreachable** (fetch throws): Show "Unable to check status — retrying…" without clearing the interval.

---

## 6. ResearchReport Component

**File**: `src/components/workspace/ResearchReport.tsx`
**Type**: Server Component (RSC, rendered by page.tsx after run completes)

**Props**:
```typescript
interface ResearchReportProps {
  report: ResearchReport;  // full report from API
}
```

**Layout** (vertical sections within the main content area):

### Section 1 — Header
- Title: "Research Report"
- Subtitle: the `research_question`
- Generated timestamp
- Source count badge ("8 web sources · 1 document")

### Section 2 — Executive Summary
- White `maar-card`
- `executive_summary` prose text
- Section label: "Executive Summary"

### Section 3 — Key Findings
- White `maar-card`
- Numbered list of `key_findings` strings
- Each finding on its own line with a colored bullet

### Section 4 — Supporting Evidence
- White `maar-card`
- For each item in `evidence_used`:
  - `[SOURCE N]` badge
  - Web: clickable URL link + page title + excerpt
  - Document: filename + page number + excerpt

### Section 5 — Observations / Contradictions
- Rendered only if `observations` or `contradictions` are non-null
- Yellow-bordered `maar-card` for contradictions (visual warning)

### Section 6 — Limitations
- Grey `maar-card`
- `limitations` prose text

### Section 7 — Sources
**FindingsSection** (`src/components/workspace/FindingsSection.tsx`):
- Collapsible list of all sources
- Web: favicon + URL + title
- Document: paperclip icon + filename

---

## 7. RunHistory Component

**File**: `src/components/workspace/RunHistory.tsx`
**Type**: Client Component

**Layout**: Compact table/list below the main panel showing all past runs.

Each row:
- `StatusBadge` (reused from Phase 1)
- Date created
- Source types used (web / document / both — small icon row)
- Duration (if completed)
- "View Report →" link (only if `status = completed`)

Empty state: "No previous research runs."

---

## 8. New TypeScript Types

**File**: `src/lib/types/run.ts`

```typescript
export type RunStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface ResearchRun {
  id: string;
  project_id: string;
  research_question: string;
  use_web: boolean;
  use_documents: boolean;
  status: RunStatus;
  current_stage: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface RunListResponse {
  items: ResearchRun[];
  total: number;
  limit: number;
  offset: number;
}

export interface EvidenceReference {
  source_label: string;
  source_type: 'web' | 'document';
  url?: string;
  title?: string;
  excerpt?: string;
  filename?: string;
  chunk_index?: number;
  page_number?: number;
}

export interface ReportSource {
  type: 'web' | 'document';
  url?: string;
  title?: string;
  retrieved_at?: string;
  filename?: string;
  mime_type?: string;
}

export interface ResearchReport {
  id: string;
  run_id: string;
  research_question: string;
  executive_summary: string;
  key_findings: string[];
  evidence_used: EvidenceReference[];
  observations: string | null;
  contradictions: string | null;
  limitations: string;
  sources: ReportSource[];
  generated_at: string;
}

export interface UploadedDocument {
  id: string;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  uploaded_at: string;
}
```

---

## 9. New API Functions

**File**: `src/lib/api/runs.ts`

```typescript
export async function getRuns(projectId: string): Promise<RunListResponse>
export async function getRun(projectId: string, runId: string): Promise<ResearchRun>
export async function startRun(projectId: string, data: StartRunInput): Promise<ResearchRun>
export async function getReport(projectId: string, runId: string): Promise<ResearchReport>
export async function uploadDocuments(projectId: string, files: File[]): Promise<DocumentUploadResponse>
export async function listDocuments(projectId: string): Promise<DocumentListResponse>
export async function deleteDocument(projectId: string, documentId: string): Promise<void>
```

The `uploadDocuments` function uses `FormData` and a separate `apiFetchMultipart` wrapper (added to `client.ts`) that does not set `Content-Type: application/json` — it allows the browser to set `multipart/form-data` with the correct boundary.

---

## 10. State Definitions

### Empty States
- ResearchPanel: "No research runs yet" — large icon, description, Start Research button.
- RunHistory: "No previous runs" — one-line text, no icon needed.

### Loading States
- ResearchPanel initial load: `<Skeleton>` cards matching the form shape (3 skeleton lines).
- RunStatusCard stage update: Stage label updates immediately on poll response.

### Error States
- Backend unreachable (ResearchPanel load): Banner "Cannot reach backend — check that the API server is running."
- Upload failure: Inline file error row with red border and error message.
- Submission failure: `toast.error(message)`.
- Run failed: `<RunFailedCard>` with `error_message` in an amber-bordered card.
- Report not found: "Report not available — the run may have failed."

### Success States
- Upload success: File shows green checkmark and `document_id` is stored.
- Run created: Immediate transition to `<RunStatusCard>` + `toast.success("Research started.")`.
- Run completed: Transition to `<ResearchReport>` + `toast.success("Research complete.")`.

---

## 11. Responsive Behavior

- The workspace two-column layout (main + sidebar) remains unchanged.
- `ResearchForm`, `RunStatusCard`, and `ResearchReport` all live in the main column.
- On mobile (< `lg`), the sidebar collapses to below the main content (existing Phase 1 behavior).
- The `FileUploadArea` drop zone adjusts to full width on narrow viewports.
