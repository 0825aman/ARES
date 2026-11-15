# 46 — Frontend Research Workspace Specification

## Phase 5 · Module M5.7

---

## 1. Purpose

This document specifies the complete Phase 5 state of the Research Workspace — the primary working view for an active or completed research run. It describes all panels, their layout, their interaction with SSE, and all new UI components introduced in Phase 5.

This replaces the Phase 4 workspace specification for the purposes of implementation.

---

## 2. Workspace Route

Route: `/projects/{project_id}/runs/{run_id}`

This route already exists. Phase 5 does not change the routing structure.

---

## 3. Top-Level Workspace Layout

The workspace uses a single-page layout with a persistent header, a two-column main area, and an optional right drawer.

```
┌────────────────────────────────────────────────────────────────────────────┐
│ HEADER: Project title · Run badge · Run controls (start / stop)           │
├────────────────────────────────────────────────────────────────────────────┤
│ APPROVAL BANNER (conditional — only when run status = awaiting_approval)  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  LEFT COLUMN (flex-grow)             RIGHT COLUMN (fixed ~360px)           │
│  ─────────────────────────────────   ─────────────────────────────────     │
│  RunStatusCard (live progress)       AgentActivityFeed (live SSE events)   │
│  MultiAgentStatusCard (agents)       [SSE connection indicator]            │
│  ─────────────────────────────────                                         │
│  [Tab bar: Overview · Sources · Evidence · Claims · Report]                │
│  ─────────────────────────────────                                         │
│  [Tab content panel]                                                       │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘

[RIGHT DRAWER: SourceDetailDrawer or EvidenceDetailDrawer — slides in from right]
```

### Responsive behaviour

- Above 1280px: two-column layout as above
- 768px – 1280px: single column; AgentActivityFeed moves below MultiAgentStatusCard and collapses to 300px height
- Below 768px: full single column; tab bar becomes a scrollable horizontal chip bar

---

## 4. Header

**Contents:**
- Back arrow → `/projects/{project_id}` (breadcrumb navigation)
- Project name (from `ResearchProject.title`)
- Run status badge (colour-coded, see status colour table below)
- SSE connection indicator dot (green = connected, grey = polling fallback)
- "Start Research" button (disabled if run is not in `not_started` status)
- "Stop" button (only visible when run is `running` or `awaiting_approval`)

**Status colour table:**

| Status | Badge colour | Label |
|---|---|---|
| not_started | slate | Not Started |
| running | blue (pulsing) | Running |
| awaiting_approval | amber | Awaiting Approval |
| completed | green | Completed |
| failed | red | Failed |
| paused | orange | Paused |

---

## 5. Approval Banner

Conditionally rendered between header and main content when `run.status === "awaiting_approval"`.

See document 44 for full approval banner and modal specification.

**Integration with workspace:**
- When SSE receives `approval_required`, set a local `pendingApproval` state variable
- Render `ApprovalBanner` component with `pendingApproval` data
- When user submits decision via the modal, call `POST /approval/{id}/decide`
- On success, clear `pendingApproval` state; SSE will deliver `approval_resolved` shortly after

---

## 6. RunStatusCard (Updated for Phase 5)

**Existing in Phase 4:** Polls `GET /runs/{run_id}` every 3s (active) / 60s (inactive).

**Phase 5 updates:**
- Remove polling loop; instead subscribe to SSE `run_status_changed` events
- Keep a 60s polling fallback (via `setInterval`) in case SSE connection drops
- Add display for `awaiting_approval` status with amber styling
- Add SSE connection status indicator

**Content:**
- Run title and research question
- Status badge
- Progress bar: `current_stage / total_stages` percentage
- Stage label: current stage name (human-readable)
- Start time and elapsed time
- Workflow mode badge (quick / standard / deep)

---

## 7. MultiAgentStatusCard (Updated for Phase 5)

**Existing in Phase 4:** Polls every 3–4s.

**Phase 5 updates:**
- Transition to SSE for `agent_status_changed` events
- Keep polling fallback at 60s interval

**Content:**
- List of all agents with their current status (idle / running / completed / failed)
- Agent type icon (research, analysis, critic, supervisor, planner)
- Last activity timestamp per agent
- Current task name when running

---

## 8. AgentActivityFeed (Updated for Phase 5)

**Existing in Phase 4:** Polls `GET /activity?run_id=` every 3s.

**Phase 5 updates:**
- Connect to SSE stream at component mount
- Receive `activity_event` SSE messages and prepend to local list
- Remove polling loop (SSE replaces it)
- Keep a 60s polling fallback if SSE disconnects
- On SSE reconnect: use `Last-Event-ID` header so the server replays missed events

**Content per event row:**
- Agent name (colour-coded icon)
- Event type (e.g., "source fetched", "claim extracted")
- Summary text
- Relative timestamp

**Behaviour:**
- Auto-scroll to latest event when feed is at bottom
- If user has scrolled up, stop auto-scroll (show "New activity" badge at bottom)
- Maximum 200 events shown; older events are removed from top

---

## 9. Tab System

The main content area below `RunStatusCard` and `MultiAgentStatusCard` uses a tab system with 5 tabs.

```
[Overview]  [Sources]  [Evidence]  [Claims]  [Report]
```

All tabs are always visible (not disabled when content is empty — they show empty states).

### Tab: Overview

Content:
- Research question (full text)
- Research plan summary (from `ResearchPlan.plan_summary`, or placeholder if not yet generated)
- Planned tasks list with status icons (from `ResearchTask` records)
- Run metadata: created_at, started_at, workflow_mode, estimated_sources

This tab is the default/active tab when the workspace opens.

### Tab: Sources

Renders the `SourcePanel` component (see document 43).

Live badge on tab showing current source count — updates when SSE pushes `source_added` events.

### Tab: Evidence

Renders the `EvidenceExplorer` component (see document 43).

Live badge on tab showing current evidence count.

### Tab: Claims

Renders the existing `ClaimVerificationPanel` component from Phase 4.

No changes to this component in Phase 5 beyond receiving cross-link opens from Evidence Viewer.

### Tab: Report

Renders `ResearchReportView` (existing Phase 4 component) when a report exists, followed by the new `ExportPanel` component (see document 45).

When no report exists: placeholder section reading "The research report will appear here when all agents have completed their work."

---

## 10. New Components Required for Phase 5

| Component | File | Description |
|---|---|---|
| `ApprovalBanner` | `workspace/ApprovalBanner.tsx` | Amber banner with approval CTA |
| `ApprovalModal` | `workspace/ApprovalModal.tsx` | Full-detail modal for decision |
| `SourceDetailDrawer` | `workspace/SourceDetailDrawer.tsx` | Sheet drawer for source detail |
| `EvidenceDetailDrawer` | `workspace/EvidenceDetailDrawer.tsx` | Sheet drawer for evidence detail |
| `ExportPanel` | `workspace/ExportPanel.tsx` | Report version selector and export buttons |
| `SSEConnectionIndicator` | `workspace/SSEConnectionIndicator.tsx` | Dot indicator for SSE status |
| `LiveBadge` | `workspace/LiveBadge.tsx` | Animated count badge for tabs |

---

## 11. SSE Hook

A shared React hook `useSSE(runId)` manages the SSE connection for the entire workspace page.

**Behaviour:**
- Opens `EventSource` to `/api/v1/runs/{runId}/stream` at component mount
- Parses incoming messages and dispatches to relevant component state via callbacks
- Stores `lastEventId` and passes it as `Last-Event-ID` header on reconnect (requires `fetch`-based SSE since native `EventSource` does not support custom headers — use a simple `fetch`-based reconnecting SSE client)
- Exposes `connected: boolean` state
- On disconnect: sets `connected = false`, starts 60s polling fallback interval for critical data
- On reconnect: resumes SSE, clears polling interval

**Events handled by hook:**
- `activity_event` → AgentActivityFeed
- `run_status_changed` → RunStatusCard
- `agent_status_changed` → MultiAgentStatusCard
- `source_added` → SourcePanel
- `evidence_added` → EvidenceExplorer
- `approval_required` → workspace-level `pendingApproval` state
- `approval_resolved` → clear `pendingApproval`

---

## 12. Loading and Error States

### Workspace initial load

While `GET /runs/{run_id}` is in-flight:
- Show skeleton placeholders for RunStatusCard and MultiAgentStatusCard
- Tab content area shows a spinner

### Tab content loading

Each tab panel shows a skeleton list while its data loads.

### SSE connection failure

- Connection indicator turns grey
- A subtle banner appears: "Live updates paused — showing latest data" (non-blocking, dismissible)
- Polling fallback activates

### Run failure

When `run.status === "failed"`:
- Status badge turns red
- A failure banner shows with `run.error_message` (if available)
- Approval banner is hidden
- Progress bar shows last known percentage, no animation

---

## 13. UX Guidelines for Phase 5 Workspace

1. **No full-page refreshes** — all data updates happen via SSE or in-place refetch
2. **Smooth transitions** — new items in feeds and lists use a 200ms fade-in (not slide)
3. **No layout shifts** — tab content areas have a minimum height to avoid reflow when switching tabs
4. **Meaningful empty states** — every empty panel has context-specific copy explaining what will appear there
5. **Non-blocking notifications** — approval banners and SSE errors appear inline; no toast notifications that obscure content
6. **Consistent badge colours** — use the status colour table from section 4 throughout all components

---

## 14. Pages Not Changed in Phase 5

The following pages/routes are not modified in Phase 5:

- `/` — Dashboard
- `/projects` — Project list
- `/projects/new` — New project form
- `/projects/{id}` — Project detail / run list
- `/settings` — Settings placeholder

No changes to the global sidebar navigation, header layout, or theme configuration.
