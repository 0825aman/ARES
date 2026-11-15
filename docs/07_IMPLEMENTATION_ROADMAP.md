# 07 — Implementation Roadmap

## Multi-Agent Autonomous Researcher (MAAR)
### Phase 1: Application Foundation

---

## 1. Roadmap Overview

Phase 1 is organized into 7 sequential milestones. Each milestone produces independently verifiable, working software. No milestone depends on the completion of a future one for its own deliverables.

| # | Milestone | Complexity |
|---|---|---|
| M1 | Repository Setup and Environment | Low |
| M2 | Backend Foundation and Database | Medium |
| M3 | Backend API Endpoints | Medium |
| M4 | Frontend Foundation and Layout | Medium |
| M5 | Dashboard Page | Medium |
| M6 | Research Projects Pages | High |
| M7 | Research Workspace Page | Medium |

---

## 2. Milestone Details

---

### M1 — Repository Setup and Environment

**Intent**: Establish the repository, folder structure, and working development environment for both frontend and backend before writing any application code. A clean, reproducible setup is the prerequisite for everything else.

**Dependencies**: None.

**Deliverables**
- Git repository initialized with `.gitignore`.
- `maar/frontend/` scaffold created with Next.js, TypeScript, Tailwind CSS, and shadcn/ui.
- `maar/backend/` scaffold created with Python virtual environment and all dependencies installable from `requirements.txt`.
- Both applications start without errors.
- Environment variable template files committed.
- `README.md` with setup and run instructions written.

**Acceptance Criteria**
- [ ] `cd frontend && npm install && npm run dev` starts Next.js at `http://localhost:3000`.
- [ ] `cd backend && uvicorn app.main:app --reload` starts FastAPI at `http://localhost:8000`.
- [ ] Both applications run simultaneously without port conflict.
- [ ] `.gitignore` prevents `node_modules/`, `.next/`, `.venv/`, `*.db`, `.env*` from being tracked.
- [ ] `frontend/.env.local.example` and `backend/.env.example` are committed.

---

### M2 — Backend Foundation and Database

**Intent**: Build the backend's data layer — the database connection, ORM model, and automatic schema initialization. This must work before any API routes are built.

**Dependencies**: M1 complete.

**Deliverables**
- `app/core/config.py` — typed settings from `.env`.
- `app/core/database.py` — async SQLAlchemy engine and `get_db` dependency.
- `app/models/base.py` — `DeclarativeBase`.
- `app/models/project.py` — `ResearchProject` ORM model with all fields.
- `app/main.py` lifespan — `create_all()` on startup.
- SQLite database file created automatically on first run.

**Acceptance Criteria**
- [ ] Starting the backend creates `maar_dev.db` if it does not exist.
- [ ] The `research_projects` table is created with the correct schema.
- [ ] No database errors appear in the startup logs.
- [ ] `DATABASE_URL` in `.env` controls where the database file is created.
- [ ] The model has the correct columns: `id`, `title`, `research_question`, `description`, `category`, `status`, `created_at`, `updated_at`.

---

### M3 — Backend API Endpoints

**Intent**: Implement all 7 API endpoints with full validation, error handling, and CORS. This milestone delivers a complete, testable backend that the frontend can connect to.

**Dependencies**: M2 complete.

**Deliverables**
- `app/schemas/project.py` — all Pydantic schemas and enums.
- `app/services/project_service.py` — CRUD operations.
- `app/api/v1/routes/health.py` — health check.
- `app/api/v1/routes/projects.py` — all project routes.
- `app/api/v1/router.py` — router mounting.
- CORS middleware configured in `main.py`.
- Backend unit tests covering all endpoints.

**Endpoints to deliver**
1. `GET /health`
2. `GET /api/v1/projects/summary`
3. `GET /api/v1/projects`
4. `POST /api/v1/projects`
5. `GET /api/v1/projects/{id}`
6. `PATCH /api/v1/projects/{id}`
7. `DELETE /api/v1/projects/{id}`

**Acceptance Criteria**
- [ ] `GET /health` returns `{"status": "ok", ...}` with HTTP 200.
- [ ] `POST /api/v1/projects` creates a project and returns HTTP 201 with the project data.
- [ ] `GET /api/v1/projects` returns all projects ordered by `created_at` descending.
- [ ] `GET /api/v1/projects/{id}` returns the project or HTTP 404.
- [ ] `PATCH /api/v1/projects/{id}` updates only provided fields and returns HTTP 200.
- [ ] `DELETE /api/v1/projects/{id}` removes the project and returns HTTP 204.
- [ ] `POST` with a missing `title` returns HTTP 422 with a validation error.
- [ ] `POST` with an invalid `category` returns HTTP 400.
- [ ] Created projects persist across backend restarts.
- [ ] Browser requests from `http://localhost:3000` are not blocked by CORS.
- [ ] FastAPI automatic docs are accessible at `http://localhost:8000/docs`.
- [ ] All backend unit tests pass.

---

### M4 — Frontend Foundation and Layout

**Intent**: Build the application shell — the sidebar, navigation, page header, and design system foundation. Every subsequent page is built inside this shell. Getting the layout and design language right here avoids rework in every later milestone.

**Dependencies**: M1 complete (M3 does not need to be complete for the layout to be built).

**Deliverables**
- Tailwind CSS color tokens defined in `globals.css`.
- Inter font configured via `next/font/google`.
- shadcn/ui components installed and configured: Button, Card, Badge, Input, Textarea, Select, Skeleton, Toast/Toaster, Separator, Dialog, Tooltip, DropdownMenu.
- `AppShell.tsx`, `Sidebar.tsx`, `PageHeader.tsx`, `NavItem.tsx` implemented.
- Root `layout.tsx` using `AppShell`.
- API client module structure in `src/lib/api/` (can return stub data until M3 is complete).
- TypeScript types in `src/lib/types/project.ts`.
- `StatusBadge.tsx` and `CategoryBadge.tsx` components.

**Acceptance Criteria**
- [ ] All pages share the same sidebar and page header layout.
- [ ] Sidebar highlights the active navigation item.
- [ ] Navigating between pages does not cause a full page reload (Next.js client-side routing).
- [ ] No TypeScript errors on `npm run build`.
- [ ] No ESLint errors.
- [ ] The color palette tokens are applied globally via CSS variables.
- [ ] The Inter font renders throughout the application.
- [ ] shadcn/ui components render correctly with the configured theme.

---

### M5 — Dashboard Page

**Intent**: Build the dashboard (`/`) using real data from the backend API. The dashboard is the first thing the user sees; it must be polished and communicate the application's purpose.

**Dependencies**: M3 (backend API), M4 (frontend layout).

**Deliverables**
- `WelcomeBanner.tsx` component.
- `StatCard.tsx` and `StatsRow.tsx` components.
- `RecentProjects.tsx` component.
- Dashboard `page.tsx` fetching from `GET /api/v1/projects/summary`.
- Empty state when no projects exist.
- Skeleton loading state while data is being fetched.

**Acceptance Criteria**
- [ ] Dashboard loads and displays data from the backend API.
- [ ] Total, in-progress, and completed counts match the database.
- [ ] Recent projects list shows up to 5 most recent projects.
- [ ] Each recent project row links to its workspace.
- [ ] Empty state displays when no projects exist.
- [ ] Skeleton components display during data loading.
- [ ] "New Research Project" button navigates to `/projects/new`.
- [ ] Dashboard refreshes with updated counts after new projects are created.

---

### M6 — Research Projects Pages

**Intent**: Build the project list and the create project form. This is the primary project-management workflow. The create form must validate input, call the backend, and give clear feedback.

**Dependencies**: M3 (backend API), M4 (frontend layout).

**Deliverables**
- `ProjectCard.tsx`, `ProjectGrid.tsx` components.
- Projects list `page.tsx` at `/projects` fetching from `GET /api/v1/projects`.
- Empty state for the project list.
- `ProjectForm.tsx` — client component with full validation.
- New project `page.tsx` at `/projects/new`.
- Category constants file matching backend category list.
- Success redirect and toast notification on project creation.
- Error toast on API failure.

**Acceptance Criteria**
- [ ] Project list page shows all persisted projects as cards.
- [ ] Each project card links to its workspace.
- [ ] Project list shows an empty state when no projects exist.
- [ ] Create project form validates: title required, research question required, max length constraints.
- [ ] Inline error messages appear on blur and on submit for invalid fields.
- [ ] The submit button shows a spinner and is disabled during the API request.
- [ ] Successful creation redirects to `/projects/[id]` of the new project.
- [ ] A success toast confirms creation.
- [ ] An API error shows an error toast and keeps the form filled.
- [ ] Cancel button returns to `/projects`.
- [ ] Created project appears in the project list after creation.
- [ ] Category dropdown shows all valid categories.

---

### M7 — Research Workspace Page

**Intent**: Build the individual project workspace — the main working surface for a research project. It must display all project data, allow status updates, and contain well-designed placeholders for future capabilities.

**Dependencies**: M3 (backend API), M4 (frontend layout).

**Deliverables**
- `WorkspaceHeader.tsx` — project title and status selector.
- `ProjectDetails.tsx` — metadata sidebar panel.
- `PlaceholderSection.tsx` — reusable future-feature card.
- `StatusSelector.tsx` — client component that calls `PATCH /api/v1/projects/{id}`.
- Workspace `page.tsx` at `/projects/[id]` fetching from `GET /api/v1/projects/{id}`.
- 404 state for non-existent project IDs.
- Toast notifications for status update success and failure.

**Acceptance Criteria**
- [ ] Workspace displays project title, research question, description, category, status, created date, updated date.
- [ ] Status dropdown allows changing status to any valid value.
- [ ] Changing status immediately calls the backend and updates the displayed status.
- [ ] A success toast confirms status updates.
- [ ] Three placeholder sections are visible: Research Findings, Sources & Citations, Agent Activity.
- [ ] Placeholders use the "Coming in Phase 2" badge style defined in the UI spec.
- [ ] A 404 state displays for URLs with non-existent project IDs.
- [ ] Back link returns to `/projects`.
- [ ] No TypeScript errors or console warnings in normal operation.

---

## 3. Implementation Order and Dependencies

```
M1 (Repo Setup)
     │
     ├──► M2 (Backend DB)
     │         │
     │         └──► M3 (Backend API) ─────────┐
     │                                         │
     └──► M4 (Frontend Layout) ───────────────►│
                                               │
                                    ┌──────────┘
                                    │
                           ┌────────┴────────┐
                           │                 │
                        M5 (Dashboard)    M6 (Projects)
                                             │
                                          M7 (Workspace)
```

M5, M6, and M7 can be developed in parallel once M3 and M4 are complete. M6 and M7 are independent of each other. In practice, M6 before M7 is recommended because the workspace page requires project data created by the project form.

---

## 4. Local Development Setup

### Prerequisites

| Tool | Minimum version |
|---|---|
| Node.js | 18.x |
| npm | 9.x |
| Python | 3.11 |
| pip | 23.x |
| Git | 2.x |

No Docker, no database server, no cloud account required.

### Initial Setup (one-time)

**macOS / Linux**
```bash
# 1. Clone the repository
git clone <repository-url>
cd maar

# 2. Set up backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# 3. Set up frontend
cd ../frontend
npm install
cp .env.local.example .env.local
```

**Windows (PowerShell)**
```powershell
# 1. Clone the repository
git clone <repository-url>
cd maar

# 2. Set up backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env

# 3. Set up frontend
cd ..\frontend
npm install
Copy-Item .env.local.example .env.local
```

> **Windows note — execution policy**: If PowerShell blocks `.ps1` scripts, run once:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**Windows (Command Prompt / cmd.exe)**
```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
```

### Running the Application (two commands)

**macOS / Linux — Terminal 1 (Backend)**
```bash
cd maar/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Windows PowerShell — Terminal 1 (Backend)**
```powershell
cd maar\backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend (all platforms)**
```bash
cd maar/frontend
npm run dev
```

### Local URLs

| Service | URL |
|---|---|
| Frontend application | http://localhost:3000 |
| FastAPI backend | http://localhost:8000 |
| FastAPI interactive docs | http://localhost:8000/docs |
| FastAPI OpenAPI JSON | http://localhost:8000/openapi.json |

---

## 5. Troubleshooting

| Symptom | Platform | Resolution |
|---|---|---|
| Port 3000 or 8000 already in use | macOS/Linux | `lsof -ti:3000 \| xargs kill` |
| Port 3000 or 8000 already in use | Windows PowerShell | `Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess \| Stop-Process` |
| Port 3000 or 8000 already in use | Windows cmd | `netstat -ano \| findstr :3000` then `taskkill /PID <pid> /F` |
| Frontend shows CORS error | All | Confirm backend is running on port 8000; check both `API_URL` and `NEXT_PUBLIC_API_URL` in `.env.local` |
| Backend shows `ModuleNotFoundError` | macOS/Linux | Virtual environment not activated; run `source .venv/bin/activate` |
| Backend shows `ModuleNotFoundError` | Windows | Virtual environment not activated; run `.venv\Scripts\Activate.ps1` |
| PowerShell blocks `.ps1` execution | Windows | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| SQLite database not created | All | Confirm `DATABASE_URL` in `backend/.env` is set; check backend startup logs |
| `npm run dev` fails with TS errors | All | Run `npm run build` for full error output; check `tsconfig.json` paths |
| shadcn/ui components missing | All | Run `npx shadcn-ui@latest add [component]` from the `frontend/` directory |
| `cp` command not found | Windows | Use `Copy-Item` in PowerShell or `copy` in cmd |
