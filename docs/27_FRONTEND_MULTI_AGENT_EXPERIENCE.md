# 27 — Frontend Multi-Agent Experience

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 3
**Status**: Draft — Awaiting Approval

---

## 1. Design Principles

Phase 3 frontend changes follow these constraints:

1. **Preserve the existing visual language** — same design tokens, shadcn/ui components, typography, and spacing
2. **Additive, not replacement** — existing `ResearchPanel`, `RunStatusCard`, `ResearchReportView` are extended, not replaced
3. **No redesign** — new components slot into the existing workspace layout
4. **Graceful degradation** — if a run has `workflow_mode="sequential"`, the existing Phase 2 UI renders unchanged
5. **Polling is sufficient** — no WebSockets required; 3-second polling is acceptable
6. **Progressive disclosure** — basic progress is visible by default; detailed agent activity is expandable

---

## 2. Component Impact Assessment

### Components that change

| Component | Change |
|---|---|
| `ResearchPanel.tsx` | Detect `workflow_mode`; route to Phase 3 components when multi_agent |
| `RunStatusCard.tsx` | Show current agent name + task progress instead of single stage |
| `ResearchForm.tsx` | Add `workflow_mode` toggle (Simple / Multi-Agent) |
| `lib/api/runs.ts` | Add `getPlan()`, `getTasks()`, `getActivity()` API functions |
| `lib/types/run.ts` | Add `ResearchPlan`, `ResearchTask`, `AgentEvent` types |

### New components

| Component | Purpose |
|---|---|
| `ResearchPlanView.tsx` | Display plan objectives and task list |
| `TaskProgressList.tsx` | Show all tasks with status badges |
| `AgentActivityFeed.tsx` | Expandable execution timeline |
| `MultiAgentStatusCard.tsx` | Active agent + task progress (replaces RunStatusCard for multi_agent runs) |

### Components that do NOT change

| Component | Reason |
|---|---|
| `ResearchReportView.tsx` | Final report rendering is identical |
| `WorkspaceHeader.tsx` | No change needed |
| `StatusSelector.tsx` | No change needed |
| `ProjectDetails.tsx` | No change needed |
| `DashboardClient.tsx` | Summary stats unchanged |
| `ProjectsClient.tsx` | Project list unchanged |

---

## 3. Workspace Layout — Phase 3

The existing two-column workspace layout is preserved. The main content area (left column) shows the research panel. The sidebar (right column) shows project metadata.

**Main content area changes for multi-agent runs**:

```
┌─────────────────────────────────────────────────┐
│ Tabs: [Current Run] [History] [New Run]          │
├─────────────────────────────────────────────────┤
│                                                  │
│  WHEN STATUS IS "pending" or "running":          │
│  ┌──────────────────────────────────────────┐   │
│  │ MultiAgentStatusCard                     │   │
│  │  Active Agent: Research Planning Agent   │   │
│  │  Current Task: Task 2 of 5               │   │
│  │  [progress bar]                          │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │ ResearchPlanView (visible once created)  │   │
│  │  Objectives: ...                         │   │
│  │  ▶ Task 1: [completed ✓]                │   │
│  │  ▶ Task 2: [running ↻]                  │   │
│  │  ▶ Task 3: [pending ○]                  │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ▼ Agent Activity (collapsed by default)        │
│  ┌──────────────────────────────────────────┐   │
│  │ AgentActivityFeed                        │   │
│  │  10:32 · Supervisor · execute_next_task  │   │
│  │  10:31 · Planner · plan_created          │   │
│  │  10:30 · Supervisor · request_plan       │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  WHEN STATUS IS "completed":                     │
│  ResearchReportView (unchanged)                  │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

## 4. New TypeScript Types

Add to `src/lib/types/run.ts`:

```typescript
export interface ResearchTask {
  id: string;
  objective: string;
  search_query: string;
  expected_evidence_type: string | null;
  priority: number;
  status: 'pending' | 'running' | 'completed' | 'partial' | 'failed';
  findings: string | null;
  evidence_count: number;
  unanswered_questions: string[];
  limitations: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ResearchPlan {
  id: string;
  run_id: string;
  objectives: string[];
  tasks: ResearchTask[];
  plan_version: number;
  created_at: string;
  updated_at: string;
}

export interface AgentEvent {
  id: string;
  agent_name: 'supervisor' | 'planner' | 'researcher' | 'system';
  event_type: string;
  summary: string;
  input_ref: string | null;
  output_ref: string | null;
  iteration: number;
  created_at: string;
}

export interface AgentActivity {
  run_id: string;
  events: AgentEvent[];
  total: number;
}
```

Modify `ResearchRun` in `src/lib/types/run.ts`:
```typescript
export interface ResearchRun {
  // ... existing fields ...
  workflow_mode: 'sequential' | 'multi_agent';  // ADD THIS
}
```

---

## 5. New API Functions

Add to `src/lib/api/runs.ts`:

```typescript
export async function getPlan(
  projectId: string,
  runId: string
): Promise<ResearchPlan> {
  return apiFetch<ResearchPlan>(
    `/api/v1/projects/${projectId}/runs/${runId}/plan`
  );
}

export async function getTasks(
  projectId: string,
  runId: string
): Promise<{ items: ResearchTask[]; total: number }> {
  return apiFetch(`/api/v1/projects/${projectId}/runs/${runId}/tasks`);
}

export async function getActivity(
  projectId: string,
  runId: string
): Promise<AgentActivity> {
  return apiFetch<AgentActivity>(
    `/api/v1/projects/${projectId}/runs/${runId}/activity`
  );
}
```

---

## 6. Component Specifications

### 6.1 `ResearchForm.tsx` — Add Workflow Mode Toggle

Add a toggle above the submit button:

```
Research Mode:
  ○ Simple Research      — single-pass research (fast, Phase 2 behaviour)
  ● Multi-Agent Research — structured planning and multi-task research
```

Implemented as two radio-style `Button` components or shadcn/ui `RadioGroup`. Default: `"sequential"` (Simple Research).

The selected value is passed as `workflow_mode` in the `startRun()` API call.

No other form changes.

---

### 6.2 `MultiAgentStatusCard.tsx` — Active Agent + Progress (NEW)

Replaces `RunStatusCard` display for multi-agent runs. Uses the same polling mechanism (3-second interval).

**Layout**:
```
┌──────────────────────────────────────────────────────┐
│ [↻ spinner] Multi-Agent Research in Progress         │
│                                              [badge] │
├──────────────────────────────────────────────────────┤
│ Active Agent                                         │
│ Research Agent                                       │
│                                                      │
│ Current Task                                         │
│ "Investigate clinical decision-making impact"        │
│                                                      │
│ Task Progress ━━━━━━━━━━░░░░░░░░  2 of 5 complete  │
│                                                      │
│ ⏱ Running for 1m 23s                                │
└──────────────────────────────────────────────────────┘
```

**Data sources**:
- `getRun()` — for overall status and stage
- `getTasks()` — for task count and current task objective
- Active agent derived from `current_stage` field of the run (already updated by nodes)

**On completion**: calls `onRunCompleted()` callback (same pattern as `RunStatusCard`), which triggers `loadRuns()` in `ResearchPanel`.

---

### 6.3 `ResearchPlanView.tsx` — Plan and Task List (NEW)

Displays the research plan when available. Visible during active runs and after completion.

**Layout**:
```
┌──────────────────────────────────────────────────────┐
│ Research Plan                          [v1] [badge]  │
├──────────────────────────────────────────────────────┤
│ Objectives                                           │
│ • Understand causes of AI hallucinations             │
│ • Investigate clinical decision-making effects       │
│ • ...                                                │
├──────────────────────────────────────────────────────┤
│ Research Tasks                                       │
│                                                      │
│ ✓ Task 1  AI hallucination causes            [done] │
│   "2 sources collected"                             │
│                                                      │
│ ↻ Task 2  Clinical decision-making impact  [running]│
│   "Searching..."                                    │
│                                                      │
│ ○ Task 3  Patient safety risks             [pending]│
│ ○ Task 4  Real-world cases                 [pending]│
└──────────────────────────────────────────────────────┘
```

**Data source**: `getPlan()` API call — fetched once, then refreshed every 5 seconds while run is active.

**Task status icons**:
- `pending` → ○ (empty circle, slate)
- `running` → ↻ (spinner, blue)
- `completed` → ✓ (check, green)
- `partial` → ◑ (half circle, amber)
- `failed` → ✗ (cross, red)

**Expandable task rows**: clicking a completed task row expands to show `findings` text.

---

### 6.4 `AgentActivityFeed.tsx` — Execution Timeline (NEW)

Collapsible section at the bottom of the research panel. Collapsed by default to avoid overwhelming users.

**Collapsed state**:
```
▶ Agent Activity  (12 events)
```

**Expanded state**:
```
▼ Agent Activity  (12 events)
┌──────────────────────────────────────────────────────┐
│ 10:32:15  researcher  task_completed                 │
│           Task 2 completed — 3 evidence items        │
│                                                      │
│ 10:32:01  supervisor  research_delegated             │
│           Delegated task 2 to Research Agent         │
│                                                      │
│ 10:31:45  supervisor  accept_plan                    │
│           Plan accepted — 5 tasks queued             │
│                                                      │
│ 10:31:30  planner     plan_created                   │
│           Created research plan v1 with 5 tasks      │
│                                                      │
│ 10:31:15  supervisor  request_plan                   │
│           Initiated research planning                │
└──────────────────────────────────────────────────────┘
```

**Agent name badges**:
- `supervisor` — blue badge
- `planner` — purple badge
- `researcher` — green badge
- `system` — slate badge

**Data source**: `getActivity()` — fetched once after run completes; polled every 5 seconds during active runs.

**Implementation notes**:
- Use shadcn/ui `Collapsible` component (already available)
- Show newest events at top (reverse chronological)
- Maximum 20 events displayed; "View all" link opens a full list (deferred)

---

### 6.5 `ResearchPanel.tsx` — Updated Routing Logic

Current routing: `state='loading' | 'empty' | 'active' | 'completed' | 'failed'`

Phase 3 addition: when `state='active'` or `state='completed'`, check `activeRun.workflow_mode`:

```typescript
// In the "current" tab content:

{state === 'active' && activeRun && (
  activeRun.workflow_mode === 'multi_agent'
    ? <MultiAgentStatusCard ... />
    : <RunStatusCard ... />
)}

{/* ResearchPlanView shown for multi-agent runs in both active and completed states */}
{activeRun?.workflow_mode === 'multi_agent' && (
  <ResearchPlanView projectId={projectId} runId={activeRun.id} isActive={state === 'active'} />
)}

{/* AgentActivityFeed shown for multi-agent runs */}
{activeRun?.workflow_mode === 'multi_agent' && (
  <AgentActivityFeed projectId={projectId} runId={activeRun.id} />
)}

{state === 'completed' && report && (
  <ResearchReportView report={report} />
)}
```

---

## 7. Polling Strategy

| Data | Component | Poll Interval | When |
|---|---|---|---|
| Run status | MultiAgentStatusCard | 3 seconds | While status is pending/running |
| Run status | RunStatusCard (Phase 2) | 3 seconds | While status is pending/running (unchanged) |
| Task list | ResearchPlanView | 5 seconds | While run is active |
| Plan | ResearchPlanView | 5 seconds | While run is active, once on load |
| Activity feed | AgentActivityFeed | 5 seconds | While run is active |
| Report | ResearchPanel | Once on `onRunCompleted` callback | After run completes |

All polling uses `setInterval` + `clearInterval` in `useEffect` with cleanup, matching the existing `RunStatusCard` pattern.

---

## 8. Error and Empty States

**Plan not yet available** (during early stages):
```
┌──────────────────────────────────────────────────────┐
│ Research plan being prepared…                        │
│ [skeleton placeholder]                               │
└──────────────────────────────────────────────────────┘
```

**Task failed**:
```
✗ Task 3  Patient safety risks       [failed]
  "Web search returned no results for this query."
```

**Workflow failed with partial results** (new state in ResearchPanel):
```
┌──────────────────────────────────────────────────────┐
│ ⚠ Research Incomplete                                │
│ The research workflow failed partway through.        │
│ {error_message}                                      │
│                                                      │
│ Tasks completed: 2 of 5                              │
│ [View partial plan] [Start new run]                  │
└──────────────────────────────────────────────────────┘
```

---

## 9. Backward Compatibility

- Runs with `workflow_mode="sequential"` (all existing Phase 2 runs): `ResearchPanel` renders the existing `RunStatusCard` and `ResearchReportView` exactly as before. No visual change.
- `getPlan()` returning 404 for sequential runs: `ResearchPlanView` does not render (null check).
- The `workflow_mode` field defaults to `"sequential"` in `ResearchForm` — users who don't change the toggle get identical Phase 2 behaviour.

---

## 10. `npm run build` Requirements

Before implementation begins in agent mode:
- All new types must be added to `src/lib/types/run.ts`
- All new API functions must be exported from `src/lib/api/runs.ts`
- All new components must use `'use client'` directive where they use hooks
- No `any` types in the data layer
- `npm run build` must pass with zero TypeScript errors
