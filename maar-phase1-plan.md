# MAAR Phase 1 — Master Implementation Plan

**Project**: Multi-Agent Autonomous Researcher (MAAR)  
**Phase**: 1 — Application Foundation  
**Status**: ✅ Phase 1 Complete

---

## Overview

This plan governs the sequential implementation of MAAR Phase 1 — a polished, functional local web application with a Next.js frontend, FastAPI backend, SQLite database, and complete project-management workflows. No AI research capabilities are included.

All planning documents are in `maar/docs/`. Before beginning any sub-task, the implementing agent must read the relevant planning document to obtain full context and specifications.

**Two-command startup (after setup):**

macOS / Linux:
- Terminal 1: `cd maar/backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000`
- Terminal 2: `cd maar/frontend && npm run dev`

Windows PowerShell:
- Terminal 1: `cd maar\backend; .venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000`
- Terminal 2: `cd maar\frontend; npm run dev`

> See `docs/07_IMPLEMENTATION_ROADMAP.md` Section 4 for full setup instructions including the Windows execution policy note.

---

## Sub-Tasks

---

### Sub-Task 1: Repository Setup and Environment

**Status**: [x] done

**Intent**  
Create the repository structure, initialize both applications (Next.js and FastAPI), and verify that both run locally. This is the prerequisite for all other sub-tasks.

**Relevant Documents**  
- `docs/06_REPOSITORY_STRUCTURE.md` — full folder tree and file purposes
- `docs/07_IMPLEMENTATION_ROADMAP.md` — M1 acceptance criteria and setup instructions
- `docs/09_ARCHITECTURAL_DECISIONS.md` — ADR-001 (App Router), ADR-002 (FastAPI)

**Todo List**
1. Create root `maar/` directory, `docs/` directory, `README.md`, and `.gitignore`.
2. Scaffold `maar/frontend/` with Next.js 14, TypeScript, Tailwind CSS (App Router, strict mode).
3. Configure `components.json` for shadcn/ui.
4. Create `frontend/.env.local.example`.
5. Scaffold `maar/backend/` with Python virtual environment structure.
6. Create `requirements.txt` and `requirements-dev.txt` with all specified dependencies.
7. Create minimal `app/main.py` (FastAPI app instance, no routes yet).
8. Create `backend/.env.example`.
9. Verify: `npm run dev` starts at port 3000 without errors.
10. Verify: `uvicorn app.main:app --reload` starts at port 8000 without errors.
11. Write `README.md` with setup and run instructions.

**Expected Outcomes**
- Both applications start simultaneously without errors.
- `.gitignore` covers all specified exclusions.
- Environment variable example files are committed.

---

### Sub-Task 2: Backend Foundation and Database

**Status**: [x] done

**Intent**  
Implement the data layer: settings, database connection, ORM model, and automatic schema initialization. The SQLite database must be created and the `research_projects` table must exist before any routes are built.

**Relevant Documents**  
- `docs/05_DATABASE_DESIGN.md` — full schema, field definitions, ORM model specification
- `docs/02_TECHNICAL_ARCHITECTURE.md` — Section 3 (backend architecture), Section 4 (database architecture)
- `docs/09_ARCHITECTURAL_DECISIONS.md` — ADR-003, ADR-004, ADR-005, ADR-011

**Todo List**
1. Implement `app/core/config.py` using pydantic-settings (`Settings` class with `DATABASE_URL`, `ALLOWED_ORIGINS`, `APP_ENV`).
2. Implement `app/core/database.py` (async engine, `AsyncSession` factory, `get_db` dependency).
3. Implement `app/models/base.py` (`DeclarativeBase`).
4. Implement `app/models/project.py` (`ResearchProject` ORM model with all columns and indexes).
5. Update `app/main.py` lifespan to run `create_all()` on startup.
6. Verify: Starting the backend creates `maar_dev.db` with the `research_projects` table.

**Expected Outcomes**
- Backend starts with no errors.
- `maar_dev.db` is created automatically on first run.
- The `research_projects` table has all specified columns.
- `DATABASE_URL` controls the database file location.

---

### Sub-Task 3: Backend API Endpoints

**Status**: [x] done

**Intent**  
Implement all 7 API endpoints with full validation, error handling, CORS, and service layer. This delivers a complete, independently testable backend.

**Relevant Documents**  
- `docs/04_BACKEND_API_SPECIFICATION.md` — all endpoint specs, schemas, validation rules, error responses
- `docs/08_TESTING_AND_ACCEPTANCE.md` — Section 2 (backend tests)
- `docs/09_ARCHITECTURAL_DECISIONS.md` — ADR-009 (PATCH), ADR-010 (service layer)

**Todo List**
1. Implement `app/schemas/project.py` (all Pydantic schemas and enums: `ProjectStatus`, `ProjectCategory`, `ProjectCreateRequest`, `ProjectUpdateRequest`, `ProjectResponse`, `ProjectListResponse`, `ProjectSummaryResponse`, `ProjectBriefResponse` — see `docs/04_BACKEND_API_SPECIFICATION.md` Sections 2 and 5 for exact schema definitions).
2. Implement `app/services/project_service.py` (CRUD methods; category validation is handled by `ProjectCategory` enum in Pydantic — no service-layer `VALID_CATEGORIES` list needed).
3. Implement `app/api/v1/routes/health.py` (`GET /health`).
4. Implement `app/api/v1/routes/projects.py` (all 6 project endpoints in correct route registration order).
5. Implement `app/api/v1/router.py` (mount health and projects routers).
6. Add CORS middleware to `app/main.py` using `ALLOWED_ORIGINS` from settings.
7. Create `tests/conftest.py` with test client and in-memory SQLite test database fixtures.
8. Implement `tests/test_health.py`.
9. Implement `tests/test_projects.py` covering all test cases in `08_TESTING_AND_ACCEPTANCE.md`.
10. Run `pytest tests/ -v` — all tests must pass.

**Expected Outcomes**
- All 7 endpoints documented in the API specification are functional.
- FastAPI docs accessible at `http://localhost:8000/docs`.
- All backend unit tests pass.
- CORS does not block requests from `http://localhost:3000`.

---

### Sub-Task 4: Frontend Foundation and Layout

**Status**: [x] done

**Intent**
Build the application shell: design tokens, sidebar, page header, navigation, and all shared components. Every subsequent page depends on this foundation.

**Relevant Documents**  
- `docs/03_UI_UX_SPECIFICATION.md` — Sections 1 (design direction), 2 (application layout), 6 (shadcn/ui components), 4 (interaction states)
- `docs/06_REPOSITORY_STRUCTURE.md` — Section 3 (frontend structure)
- `docs/02_TECHNICAL_ARCHITECTURE.md` — Section 2 (frontend architecture), Section 6 (environment variables)

**Todo List**
1. Configure `globals.css` with all color token CSS variables (light mode).
2. Configure Inter font in `layout.tsx` via `next/font/google`.
3. Install all required shadcn/ui components (Button, Card, Badge, Input, Textarea, Select, Skeleton, Toast/Toaster, Separator, Dialog, Tooltip, DropdownMenu).
4. Implement `src/lib/types/project.ts` (TypeScript interfaces for `Project`, `ProjectStatus`, `ProjectListResponse`, etc.).
5. Implement `src/lib/api/client.ts` (base fetch wrapper with `getServerApiUrl()` reading `API_URL` for RSC calls and `getClientApiUrl()` reading `NEXT_PUBLIC_API_URL` for client component calls — see `docs/02_TECHNICAL_ARCHITECTURE.md` Section 2.4).
6. Implement `src/lib/api/projects.ts` (typed functions for all project API calls).
7. Implement `src/lib/constants/categories.ts` (categories array matching backend).
8. Implement `src/lib/utils/cn.ts` and `src/lib/utils/format.ts`.
9. Implement `NavItem.tsx`, `Sidebar.tsx`, `PageHeader.tsx`, `AppShell.tsx` per spec.
10. Update `src/app/layout.tsx` to use `AppShell` and mount `Toaster`.
11. Create stub pages for all 5 routes (Dashboard, Projects, New, Workspace, Settings) that render within the shell.
12. Implement `StatusBadge.tsx` and `CategoryBadge.tsx`.
13. Verify: All routes render in the shell; active nav item highlights correctly; `npm run build` passes.

**Expected Outcomes**
- All pages share the sidebar and page header layout.
- Active navigation highlighting works.
- `npm run build` and `npm run lint` pass with zero errors.
- Design tokens are applied from CSS variables.

---

### Sub-Task 5: Dashboard Page

**Status**: [x] done

**Intent**
Build the dashboard (`/`) using live data from `GET /api/v1/projects/summary`. This is the first page users see and must be polished with proper empty states and loading states.

**Relevant Documents**  
- `docs/03_UI_UX_SPECIFICATION.md` — Section 3.1 (Dashboard specifications)
- `docs/04_BACKEND_API_SPECIFICATION.md` — Section 5 (summary endpoint)
- `docs/08_TESTING_AND_ACCEPTANCE.md` — Section 3.2 (Dashboard verification)

**Todo List**
1. Implement `WelcomeBanner.tsx` component.
2. Implement `StatCard.tsx` component (icon, number, label).
3. Implement `StatsRow.tsx` component (three stat cards).
4. Implement `RecentProjects.tsx` component (row list with clickable rows).
5. Implement skeleton loading versions for stat cards and recent project rows.
6. Implement the empty state for zero projects.
7. Update `src/app/page.tsx` to fetch from `/api/v1/projects/summary` as a Server Component and render all dashboard components.
8. Verify: Dashboard loads real data; empty state shows correctly; stat counts are accurate.

**Expected Outcomes**
- Dashboard displays live stats from the database.
- Skeleton loading appears during fetch.
- Empty state displays when no projects exist.
- Recent project rows link to correct workspaces.

---

### Sub-Task 6: Research Projects Pages

**Status**: [x] done

**Intent**
Build the project list page and the create project form — the primary project-management workflow. Form validation, API submission, success/error feedback, and post-creation routing must all work correctly.

**Relevant Documents**  
- `docs/03_UI_UX_SPECIFICATION.md` — Sections 3.2 (Project List), 3.3 (New Project Form)
- `docs/04_BACKEND_API_SPECIFICATION.md` — Sections 2.2 (create), 2.3 (list)
- `docs/08_TESTING_AND_ACCEPTANCE.md` — Sections 3.3, 3.4 (frontend verification)

**Todo List**
1. Implement `StatusBadge.tsx` and `CategoryBadge.tsx` (if not done in Sub-Task 4).
2. Implement `ProjectCard.tsx` component per spec.
3. Implement `ProjectGrid.tsx` component.
4. Implement empty state for project list.
5. Update `src/app/projects/page.tsx` to fetch all projects as RSC and render `ProjectGrid`.
6. Implement `ProjectForm.tsx` as a client component with:
   - Controlled form state.
   - Inline validation (required, max-length) on blur and submit.
   - Submit button with spinner and disabled-during-request state.
   - API call to `POST /api/v1/projects`.
   - Redirect to workspace on success + success toast.
   - Error toast on API failure.
   - Cancel button.
7. Update `src/app/projects/new/page.tsx` to render the form.
8. Verify all acceptance criteria in `08_TESTING_AND_ACCEPTANCE.md` Section 3.4.

**Expected Outcomes**
- Project list shows all persisted projects as cards.
- Create form validates, submits, and redirects correctly.
- Created project appears in the project list immediately after creation.
- Empty states render correctly.

---

### Sub-Task 7: Research Workspace Page

**Status**: [x] done

**Intent**
Build the individual project workspace — the main working surface. Must display all project data, support inline status updates, and present three well-designed placeholder sections for future functionality.

**Relevant Documents**  
- `docs/03_UI_UX_SPECIFICATION.md` — Section 3.4 (Research Workspace)
- `docs/04_BACKEND_API_SPECIFICATION.md` — Sections 2.4 (get by ID), 2.5 (update)
- `docs/08_TESTING_AND_ACCEPTANCE.md` — Section 3.5 (workspace verification)
- `docs/09_ARCHITECTURAL_DECISIONS.md` — ADR-009 (PATCH semantics)

**Todo List**
1. Implement `PlaceholderSection.tsx` (reusable dashed-border card with "Coming in Phase 2" badge).
2. Implement `ProjectDetails.tsx` (metadata sidebar: status, category, created, updated, ID).
3. Implement `StatusSelector.tsx` as a client component (dropdown, PATCH on change, loading state, success toast).
4. Implement `WorkspaceHeader.tsx` (project title + status selector + action menu `⋯`).
5. Implement delete action in the `⋯` menu using shadcn/ui `AlertDialog`:
   - Dialog states the project title explicitly and warns the action is permanent.
   - "Delete" button is destructive-styled; "Cancel" button closes without action.
   - On confirm: call `DELETE /api/v1/projects/{id}`; on 204 redirect to `/projects` + toast "Project deleted."; on 404 show toast "Project not found." + redirect.
6. Update `src/app/projects/[id]/page.tsx` as an RSC:
   - Fetch `GET /api/v1/projects/{id}`.
   - Return 404 state for non-existent IDs.
   - Render two-column layout: main content + sidebar.
   - Render three placeholder sections in main content.
7. Verify all acceptance criteria in `08_TESTING_AND_ACCEPTANCE.md` Section 3.5.

**Expected Outcomes**
- Workspace displays all project fields correctly.
- Status update works in-place with toast feedback.
- Three placeholder sections are visible and styled per spec.
- 404 state renders for non-existent project IDs.
- `npm run build` passes with zero errors.

---

## Phase 1 Completion Gate

Before Phase 1 is declared complete, all items in `docs/08_TESTING_AND_ACCEPTANCE.md` Section 5 (Phase 1 Completion Checklist) must be checked off.

---

## Notes for Agent Mode Implementation

- Implement sub-tasks sequentially: 1 → 2 → 3 → 4, then 5/6/7 can be done in any order.
- After completing each sub-task, update its **Status** in this file to `[x] done`.
- After completing each sub-task, run the relevant validation: backend tests (`pytest tests/ -v`), frontend build (`npm run build`), and lint (`npm run lint`).
- Do not begin the next sub-task until the current one passes all its acceptance criteria.
- Sub-Tasks 5, 6, and 7 all require both Sub-Task 3 (backend API) and Sub-Task 4 (frontend layout) to be complete first.
