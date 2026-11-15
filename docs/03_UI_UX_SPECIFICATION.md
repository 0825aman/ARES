# 03 — UI/UX Specification

## Multi-Agent Autonomous Researcher (MAAR)
### Phase 1: Application Foundation

---

## 1. Design Direction

### 1.1 Design Language

MAAR targets the visual quality of modern AI SaaS products — specifically the precision and restraint of Linear, the information hierarchy of Vercel's dashboard, and the purposeful typography of Notion. The interface must feel like the foundation of a serious professional tool, not a tutorial project.

Key principles:
- **Clarity over decoration**: Every visual element serves a functional purpose.
- **Controlled density**: Enough information per screen to be productive; not so much that the user is overwhelmed.
- **Purposeful whitespace**: Spacing creates hierarchy, not emptiness.
- **Data confidence**: Numbers, statuses, and labels appear as authoritative information, not filler.

### 1.2 Color Palette

The application uses a neutral base with a single accent color. Dark mode tokens are defined from the start even if the toggle is not implemented in Phase 1. This avoids costly color refactors later.

**Light Mode**

| Role | Token name | Hex |
|---|---|---|
| Background | `--bg-base` | `#FAFAFA` |
| Surface (card) | `--bg-surface` | `#FFFFFF` |
| Surface raised | `--bg-surface-raised` | `#F4F4F5` |
| Border subtle | `--border-subtle` | `#E4E4E7` |
| Border default | `--border-default` | `#D4D4D8` |
| Text primary | `--text-primary` | `#09090B` |
| Text secondary | `--text-secondary` | `#71717A` |
| Text muted | `--text-muted` | `#A1A1AA` |
| Accent | `--accent` | `#2563EB` |
| Accent hover | `--accent-hover` | `#1D4ED8` |
| Success | `--status-success` | `#16A34A` |
| Warning | `--status-warning` | `#D97706` |
| Neutral | `--status-neutral` | `#71717A` |
| Destructive | `--status-destructive` | `#DC2626` |

**Dark Mode** (tokens defined, toggle deferred)

| Role | Hex |
|---|---|
| Background | `#09090B` |
| Surface | `#18181B` |
| Surface raised | `#27272A` |
| Border subtle | `#27272A` |
| Border default | `#3F3F46` |
| Text primary | `#FAFAFA` |
| Text secondary | `#A1A1AA` |
| Accent | `#3B82F6` |

### 1.3 Typography

| Usage | Font | Weight | Size |
|---|---|---|---|
| App name/logo | Inter | 700 | 15px |
| Page title | Inter | 600 | 24px |
| Section heading | Inter | 600 | 16px |
| Card title | Inter | 500 | 14px |
| Body text | Inter | 400 | 14px |
| Caption / metadata | Inter | 400 | 12px |
| Status badge | Inter | 500 | 11px |
| Button | Inter | 500 | 14px |
| Input | Inter | 400 | 14px |

Inter is available via `next/font/google`.

### 1.4 Spacing System

Tailwind's default spacing scale (4px base unit). Key values:

- Component padding: `p-4` (16px) or `p-6` (24px) for cards.
- Section gaps: `gap-6` (24px) between major sections.
- Sidebar width: `w-64` (256px) fixed.
- Header height: `h-14` (56px).
- Card border radius: `rounded-lg` (8px).

### 1.5 Status Badge Color Mapping

| Status | Background | Text | Border |
|---|---|---|---|
| Not Started | `#F4F4F5` | `#71717A` | `#E4E4E7` |
| In Progress | `#EFF6FF` | `#2563EB` | `#BFDBFE` |
| Completed | `#F0FDF4` | `#16A34A` | `#BBF7D0` |
| Archived | `#FFF7ED` | `#D97706` | `#FED7AA` |

---

## 2. Application Layout

### 2.1 Shell Structure

The application uses a persistent sidebar + main content layout. The sidebar is never hidden on desktop.

```
┌─────────────────────────────────────────────────────┐
│  Sidebar (256px fixed)  │  Main Area (flex-fill)    │
│                         │                           │
│  [Logo + App Name]      │  [Page Header 56px]       │
│                         ├───────────────────────────┤
│  ─── NAVIGATION ──────  │                           │
│  Dashboard              │  [Page Content]           │
│  Research Projects      │                           │
│  New Research           │                           │
│  ──────────────────     │                           │
│  Settings               │                           │
│                         │                           │
│  [Footer: version]      │                           │
└─────────────────────────────────────────────────────┘
```

### 2.2 Sidebar Specification

**Header area**
- Application logo (geometric icon, e.g. a network/node icon from Lucide) + "MAAR" wordmark.
- Tagline: "Autonomous Research" in muted text below.

**Navigation items**
Each item: icon (16px) + label + active indicator.

| Item | Icon | Route |
|---|---|---|
| Dashboard | `LayoutDashboard` | `/` |
| Research Projects | `FolderOpen` | `/projects` |
| New Research | `Plus` | `/projects/new` |
| Settings | `Settings` | `/settings` |

Active state: Left border accent line (`border-l-2 border-accent`) + accent text color + subtle background.

Hover state: Subtle background fill `bg-surface-raised`.

**Footer area**
- Version number: `v0.1.0` in muted caption text.

### 2.3 Page Header

A consistent header bar at the top of the main content area.

- Left: Current page title in `text-xl font-semibold`.
- Right: Contextual action button (e.g., "New Research" button on the Projects page).
- Height: 56px, with bottom border.

---

## 3. Page Specifications

### 3.1 Dashboard (`/`)

**Purpose**: First-impression page. Communicates the application's purpose and the user's current research activity at a glance.

**Layout**

```
[Page Header: "Dashboard"]
─────────────────────────────────────────────────────────
[Welcome banner — conditional on first visit logic or always shown]

[Stats Row: 3 cards across]
  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
  │  Total Projects  │ │   In Progress    │ │   Completed      │
  │       12         │ │        4         │ │        7         │
  └──────────────────┘ └──────────────────┘ └──────────────────┘

[Section header: "Recent Projects"]   [Button: View All →]
  ┌──────────────────────────────────────────────────────────┐
  │  Project title        Category badge   Status badge  Date│
  ├──────────────────────────────────────────────────────────┤
  │  Project title        Category badge   Status badge  Date│
  ├──────────────────────────────────────────────────────────┤
  │  Project title        Category badge   Status badge  Date│
  └──────────────────────────────────────────────────────────┘
```

**Stat Card Specification**
- White card with subtle border.
- Icon in top-right corner (muted color).
- Large number `text-3xl font-bold`.
- Label below in muted text.
- No chart, no sparkline — clean and minimal.

Icons: Total → `Layers`; In Progress → `Activity`; Completed → `CheckCircle2`.

**Recent Projects List**
- Shows up to 5 most recently created projects.
- Each row: title (bold), category (small badge), status (colored badge), creation date (muted).
- Entire row is clickable; navigates to `/projects/[id]`.
- Subtle hover state on rows.

**Empty State (no projects)**
Replace the stats row and recent projects list with a centered empty state:
- Icon: `SearchX` or `Microscope` (large, muted).
- Heading: "No research projects yet."
- Sub-text: "Create your first research project to get started."
- Primary CTA button: "Create Research Project" → navigates to `/projects/new`.

**Welcome Banner**
- Shown on every visit in Phase 1 (no "dismiss" logic required).
- Dark card (uses `--bg-surface` elevated): "Welcome to MAAR — Multi-Agent Autonomous Researcher."
- One sentence description of what MAAR will do.
- No close button in Phase 1.

---

### 3.2 Research Projects (`/projects`)

**Purpose**: Browse and manage all research projects.

**Layout**

```
[Page Header: "Research Projects"]   [Button: + New Research]
─────────────────────────────────────────────────────────
[Search input (Phase 2 placeholder — disabled, shown for UI completeness)]
[Filter row: Status filter (Phase 2 placeholder)]

[Project Grid — 2 or 3 columns, responsive]
  ┌─────────────────────────┐  ┌─────────────────────────┐
  │  [Status badge]          │  │  [Status badge]          │
  │                          │  │                          │
  │  Project Title           │  │  Project Title           │
  │  Research question...    │  │  Research question...    │
  │  (2 lines, truncated)    │  │  (2 lines, truncated)    │
  │                          │  │                          │
  │  [Category]   Created: X │  │  [Category]   Created: X│
  └─────────────────────────┘  └─────────────────────────┘
```

**Project Card Specification**
- White card with border and `rounded-lg`.
- Subtle shadow on hover: `shadow-sm`.
- Top of card: status badge (left-aligned).
- Title: `font-semibold text-sm`, 2-line max with ellipsis.
- Research question preview: `text-muted text-xs`, 2-line max.
- Footer: category badge (optional) + creation date.
- Entire card is clickable → `/projects/[id]`.

**Empty State**
- Centered illustration + "No research projects found."
- CTA: "Create your first research project".

**Search/Filter Bar**
- Visible but inputs are disabled with a `cursor-not-allowed` style.
- Tooltip on hover: "Search is available in Phase 2."
- This communicates roadmap without cluttering the interface.

---

### 3.3 New Research Project (`/projects/new`)

**Purpose**: Create a new research project.

**Layout**

```
[Page Header: "New Research Project"]
─────────────────────────────────────────────────────────
[Centered form card — max-width 640px]
  ┌──────────────────────────────────────────────┐
  │  Research Title *                            │
  │  [Input field]                               │
  │                                              │
  │  Research Question *                         │
  │  [Textarea — 4 rows]                         │
  │                                              │
  │  Description (optional)                      │
  │  [Textarea — 3 rows]                         │
  │                                              │
  │  Category                                    │
  │  [Select dropdown]                           │
  │                                              │
  │  [Cancel]            [Create Research →]     │
  └──────────────────────────────────────────────┘
```

**Form Behavior**
- All required fields show inline error messages below the input on blur and on submit attempt.
- The "Create Research" button is disabled while the API request is in flight; shows spinner.
- On success: redirect to `/projects/[id]` of the newly created project + toast notification: "Research project created successfully."
- On API error: toast notification with the error message; form remains filled.
- Cancel navigates back to `/projects`.

**Field Specifications**

| Field | Type | Required | Max length | Placeholder |
|---|---|---|---|---|
| Research Title | text input | Yes | 200 | "e.g. Impact of AI on Healthcare Diagnostics" |
| Research Question | textarea | Yes | 1000 | "What specific question is this research trying to answer?" |
| Description | textarea | No | 2000 | "Provide additional context or background..." |
| Category | select | No | — | "Select a category" |

**Validation Error Messages**

| Field | Error |
|---|---|
| Research Title (empty) | "Research title is required." |
| Research Title (too long) | "Title must be 200 characters or fewer." |
| Research Question (empty) | "Research question is required." |
| Research Question (too long) | "Research question must be 1000 characters or fewer." |

---

### 3.4 Research Workspace (`/projects/[id]`)

**Purpose**: The main working view for an individual research project.

**Layout**

```
[Page Header: Project Title]   [Status dropdown]   [⋯ menu]
─────────────────────────────────────────────────────────
[← Back to Projects]

[Two-column layout: main content (2/3) | sidebar (1/3)]

Main Content:
  ┌──────────────────────────────────────────┐
  │  Research Question                       │
  │  [Full research question text]           │
  └──────────────────────────────────────────┘

  ┌──────────────────────────────────────────┐
  │  Description                             │
  │  [Description text or "No description   │
  │   provided."]                            │
  └──────────────────────────────────────────┘

  ┌──────────────────────────────────────────┐
  │  🔬  Research Findings                   │
  │  ─────────────────────────────────────── │
  │  [Coming in Phase 2]                     │
  │  Research findings will appear here as   │
  │  agents complete their investigation.    │
  └──────────────────────────────────────────┘

  ┌──────────────────────────────────────────┐
  │  📚  Sources & Citations                 │
  │  ─────────────────────────────────────── │
  │  [Coming in Phase 2]                     │
  └──────────────────────────────────────────┘

  ┌──────────────────────────────────────────┐
  │  🤖  Agent Activity                      │
  │  ─────────────────────────────────────── │
  │  [Coming in Phase 2]                     │
  │  The agent activity log will display     │
  │  real-time research progress here.       │
  └──────────────────────────────────────────┘

Sidebar:
  ┌────────────────────────┐
  │  Project Details       │
  │  ────────────────────  │
  │  Status                │
  │  [Status badge]        │
  │  Category              │
  │  [Category badge]      │
  │  Created               │
  │  Jan 15, 2025          │
  │  Last Updated          │
  │  Jan 16, 2025          │
  │  Project ID            │
  │  [short ID]            │
  └────────────────────────┘
```

**Status Update**
- The status badge in the page header is an editable dropdown (shadcn/ui Select component).
- Changing the status triggers a PATCH request to the backend immediately.
- Shows a loading indicator on the status control during the update.
- On success: the status updates in place + toast "Status updated."

**Placeholder Section Style**
- Each placeholder card has a dashed border and muted background.
- Icon + section title in normal text weight.
- "Coming in Phase 2" label with a `Badge` component variant: `secondary`.
- One-line description of what will appear.
- Consistent appearance communicates intentionality, not incompleteness.

**404 State**
- If a project ID does not exist, display a centered 404 state:
  - "Project not found."
  - CTA: "Return to Research Projects."

---

### 3.5 Settings (`/settings`)

**Purpose**: Placeholder for future application settings.

**Layout**

```
[Page Header: "Settings"]
─────────────────────────────────────────────────────────
[Centered content card]
  "Application settings will be available in a future release."
  [Icon: Settings]
  Version: 0.1.0
```

Simple, honest placeholder. No fake form fields.

---

## 4. Interaction States

Every interactive element must have clearly defined states.

### 4.1 Buttons

| State | Style |
|---|---|
| Default | Solid accent background, white text |
| Hover | `accent-hover` background |
| Focus | 2px accent ring offset |
| Disabled | 50% opacity, cursor not allowed |
| Loading | Spinner icon replaces or precedes label |

### 4.2 Form Inputs

| State | Style |
|---|---|
| Default | 1px `border-default` |
| Focus | 2px accent ring |
| Error | Red border + red error message below |
| Disabled | Muted background, `cursor-not-allowed` |

### 4.3 Loading States

- **Page-level data loading**: shadcn/ui `Skeleton` components matching the layout of the actual content. Used for dashboard stats and project list.
- **Button loading**: Inline `Loader2` icon with rotation animation, label changes to "Creating..." etc.
- **Status update**: Spinner overlaid on the status control.

### 4.4 Toast Notifications

- Using shadcn/ui Toaster.
- Position: bottom-right.
- Duration: 4000ms.
- Types: success (green), error (red), info (neutral).

---

## 5. Responsive Behavior

Phase 1 targets desktop-first design (1280px+). Tablet and mobile are supported at a basic level.

| Breakpoint | Behavior |
|---|---|
| `lg` (1024px+) | Full sidebar + content layout |
| `md` (768px) | Sidebar collapses to icon-only (stretch goal) or is hidden |
| `sm` (640px) | Single-column, stacked layout; forms fill width |

For Phase 1, a graceful degradation at 768px is acceptable. A fully responsive sidebar is a stretch goal.

---

## 6. shadcn/ui Components Used

| Component | Usage |
|---|---|
| Button | All CTAs and form actions |
| Card | Dashboard stats, project cards, workspace sections |
| Badge | Status, category |
| Input | Form text inputs |
| Textarea | Form multi-line inputs |
| Select | Category selection, status update |
| Skeleton | Loading states |
| Toast / Toaster | Feedback notifications |
| Separator | Section dividers |
| Dialog | Confirmation dialogs (e.g. delete) |
| Tooltip | Disabled control explanations |
| DropdownMenu | Workspace action menu (⋯) |

---

## 7. Design Decisions and Rationale

| Decision | Rationale |
|---|---|
| No dark mode toggle in Phase 1 | Adds significant component complexity; dark mode tokens are defined so adding the toggle is a future one-liner |
| Disabled search/filter with tooltip | Communicates roadmap honestly; does not break layout; does not require future redesign |
| Placeholder sections with dashed border | Distinguishes future from present without removing intentional structure |
| Sidebar always visible on desktop | Research tools are productivity applications; persistent navigation is expected |
| Status update in-place (no modal) | Reduces friction for the most common workspace action |
| Max-width form container (640px) | Improves readability and focus; forms wider than this feel unconstrained |
