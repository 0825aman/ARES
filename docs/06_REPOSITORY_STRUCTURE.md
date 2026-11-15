# 06 — Repository Structure

## Multi-Agent Autonomous Researcher (MAAR)
### Phase 1: Application Foundation

---

## 1. Top-Level Structure

```
maar/
├── .gitignore
├── README.md
├── docs/
│   ├── 01_PHASE_1_REQUIREMENTS.md
│   ├── 02_TECHNICAL_ARCHITECTURE.md
│   ├── 03_UI_UX_SPECIFICATION.md
│   ├── 04_BACKEND_API_SPECIFICATION.md
│   ├── 05_DATABASE_DESIGN.md
│   ├── 06_REPOSITORY_STRUCTURE.md
│   ├── 07_IMPLEMENTATION_ROADMAP.md
│   ├── 08_TESTING_AND_ACCEPTANCE.md
│   └── 09_ARCHITECTURAL_DECISIONS.md
├── frontend/
│   └── (Next.js application — see Section 3)
└── backend/
    └── (FastAPI application — see Section 4)
```

---

## 2. Root Files

### `README.md`

The primary developer onboarding document. Contains:
- Project description.
- Architecture overview (brief).
- Prerequisites.
- Quick start instructions (two commands to run the full stack).
- Links to detailed documentation in `docs/`.
- Environment variable reference.
- Troubleshooting section.

### `.gitignore`

Covers both frontend and backend artifacts. Key exclusions:
- `node_modules/`
- `.next/`
- `__pycache__/`
- `*.pyc`
- `.env`, `.env.local` (environment variables are never committed)
- `maar_dev.db` (SQLite database file)
- `.venv/`
- `dist/`, `build/`
- `.DS_Store`
- `*.egg-info/`

### `docs/`

All planning and architecture documentation. Kept in the repository for developer reference. Not part of the production build.

---

## 3. Frontend Structure

```
frontend/
├── .env.local.example          ← Template for required env vars
├── .eslintrc.json
├── .prettierrc
├── next.config.mjs
├── package.json
├── tailwind.config.ts
├── tsconfig.json
├── components.json             ← shadcn/ui configuration
├── public/
│   └── favicon.ico
└── src/
    ├── app/
    │   ├── layout.tsx           ← Root layout (Shell, font, Toaster)
    │   ├── page.tsx             ← Dashboard (/)
    │   ├── globals.css          ← Tailwind directives + CSS variables
    │   ├── projects/
    │   │   ├── page.tsx         ← Project list (/projects)
    │   │   ├── new/
    │   │   │   └── page.tsx     ← Create project (/projects/new)
    │   │   └── [id]/
    │   │       └── page.tsx     ← Research workspace (/projects/[id])
    │   └── settings/
    │       └── page.tsx         ← Settings placeholder (/settings)
    ├── components/
    │   ├── ui/                  ← shadcn/ui generated primitives
    │   │   ├── button.tsx
    │   │   ├── card.tsx
    │   │   ├── badge.tsx
    │   │   ├── input.tsx
    │   │   ├── textarea.tsx
    │   │   ├── select.tsx
    │   │   ├── skeleton.tsx
    │   │   ├── toast.tsx
    │   │   ├── toaster.tsx
    │   │   ├── separator.tsx
    │   │   ├── dialog.tsx
    │   │   ├── tooltip.tsx
    │   │   └── dropdown-menu.tsx
    │   ├── layout/
    │   │   ├── AppShell.tsx     ← Sidebar + main area wrapper
    │   │   ├── Sidebar.tsx      ← Navigation sidebar component
    │   │   ├── PageHeader.tsx   ← Consistent page header bar
    │   │   └── NavItem.tsx      ← Individual sidebar nav item
    │   ├── dashboard/
    │   │   ├── StatCard.tsx     ← Individual stat card
    │   │   ├── StatsRow.tsx     ← Row of 3 stat cards
    │   │   ├── RecentProjects.tsx ← Recent project list
    │   │   └── WelcomeBanner.tsx
    │   ├── projects/
    │   │   ├── ProjectCard.tsx  ← Card in the project grid
    │   │   ├── ProjectGrid.tsx  ← Grid/list of project cards
    │   │   ├── ProjectForm.tsx  ← Create project form (client component)
    │   │   ├── StatusBadge.tsx  ← Colored status badge
    │   │   └── CategoryBadge.tsx
    │   └── workspace/
    │       ├── WorkspaceHeader.tsx  ← Title + status dropdown
    │       ├── ProjectDetails.tsx   ← Sidebar metadata panel
    │       ├── PlaceholderSection.tsx ← Reusable "coming in phase 2" card
    │       └── StatusSelector.tsx  ← Editable status dropdown (client)
    ├── lib/
    │   ├── api/
    │   │   ├── client.ts        ← Base fetch wrapper with error handling
    │   │   ├── projects.ts      ← Typed project API functions
    │   │   └── types.ts         ← Re-export of API types
    │   ├── types/
    │   │   └── project.ts       ← TypeScript interfaces for Project, Status, etc.
    │   ├── utils/
    │   │   ├── format.ts        ← Date formatting, string truncation
    │   │   └── cn.ts            ← Tailwind class merging utility
    │   └── constants/
    │       └── categories.ts    ← CATEGORIES array matching backend
    └── hooks/
        └── useToast.ts          ← shadcn/ui toast hook re-export
```

### Key File Explanations

**`src/app/layout.tsx`**
Root layout wrapping all pages. Mounts `AppShell` (sidebar + header structure), configures the Inter font, and includes the `Toaster` component for global toast notifications.

**`src/app/globals.css`**
Tailwind CSS directives plus all CSS custom property declarations (color tokens, spacing tokens). This is the single source of truth for design tokens.

**`src/lib/api/client.ts`**
A thin wrapper around the native `fetch` API. Provides two base-URL resolvers that keep server and browser contexts cleanly separated:
- **`getServerApiUrl()`** — reads `API_URL` (server-only, never in the browser bundle). Used by React Server Components.
- **`getClientApiUrl()`** — reads `NEXT_PUBLIC_API_URL` (build-time inlined). Used by `"use client"` components.

Both default to `http://localhost:8000` if their respective variable is not set, so the application works without any configuration in local development. Also handles:
- JSON serialization/deserialization.
- Throwing typed errors for non-2xx responses.
- Common headers.

**`src/lib/api/projects.ts`**
Typed functions for every project API call. Components import from here, never calling `fetch` directly.

**`src/components/layout/AppShell.tsx`**
The persistent layout wrapper used in `layout.tsx`. Contains the sidebar and the main content scroll area.

**`src/lib/types/project.ts`**
TypeScript interfaces mirroring the backend Pydantic schemas. Single source of truth for frontend type safety.

**`components.json`**
shadcn/ui configuration specifying: component path aliases, style variant (default), Tailwind configuration path, and TypeScript settings.

---

## 4. Backend Structure

```
backend/
├── .env.example                ← Template for required env vars
├── requirements.txt            ← Production dependencies
├── requirements-dev.txt        ← Development/test dependencies
├── maar_dev.db                 ← SQLite file (gitignored)
├── scripts/
│   └── seed_data.py            ← Optional: populate sample data
└── app/
    ├── main.py                 ← FastAPI app factory + lifespan
    ├── api/
    │   └── v1/
    │       ├── router.py       ← Mounts all v1 route modules
    │       └── routes/
    │           ├── health.py   ← GET /health
    │           └── projects.py ← All /api/v1/projects endpoints
    ├── core/
    │   ├── config.py           ← Settings via pydantic-settings
    │   └── database.py         ← Engine, session factory, get_db dependency
    ├── models/
    │   ├── base.py             ← DeclarativeBase
    │   └── project.py          ← ResearchProject ORM model
    ├── schemas/
    │   └── project.py          ← All Pydantic request/response schemas
    └── services/
        └── project_service.py  ← Business logic + ORM calls
```

### Key File Explanations

**`app/main.py`**
Application factory. Creates the FastAPI instance, registers middleware (CORS), mounts the v1 router, and defines the lifespan context manager for database initialization.

**`app/core/config.py`**
Uses `pydantic-settings` to read `.env` variables into a typed `Settings` class. Provides a `get_settings()` function used via FastAPI's `Depends()`. This is the only place environment variables are accessed.

**`app/core/database.py`**
Creates the SQLAlchemy async engine from `settings.DATABASE_URL`. Provides `AsyncSession` factory and the `get_db` dependency function injected into route handlers.

**`app/api/v1/routes/projects.py`**
All project CRUD route handlers. Each handler:
- Receives a validated Pydantic schema via request body parsing.
- Receives a database session via `Depends(get_db)`.
- Calls the appropriate `ProjectService` method.
- Returns a Pydantic response schema.

**`app/services/project_service.py`**
Contains all database interaction logic. Route handlers call service methods; service methods call ORM operations. This layer makes routes thin and business logic testable without HTTP.

**`app/models/project.py`**
SQLAlchemy ORM model for `research_projects`. Contains only mapping declarations, no business logic.

**`app/schemas/project.py`**
All Pydantic schemas: `ProjectCreateRequest`, `ProjectUpdateRequest`, `ProjectResponse`, `ProjectListResponse`, `ProjectSummaryResponse`, `ProjectBriefResponse`. The `ProjectStatus` enum is also defined here.

**`requirements.txt`**

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
sqlalchemy[asyncio]>=2.0.0
aiosqlite>=0.20.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
```

**`requirements-dev.txt`**

```
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0         # async test client for FastAPI
pytest-cov>=5.0.0
```

---

## 5. Environment Files

### `frontend/.env.local.example`

```
# URL used by React Server Components (Node.js server-side — never sent to the browser)
# In Docker or production, this can be an internal hostname, e.g. http://backend:8000
API_URL=http://localhost:8000

# URL used by browser (client components) — inlined into the JS bundle at build time
# Must always be a URL reachable by the user's browser
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Never committed**: `frontend/.env.local`

### `backend/.env.example`

```
DATABASE_URL=sqlite+aiosqlite:///./maar_dev.db
ALLOWED_ORIGINS=http://localhost:3000
APP_ENV=development
```

**Never committed**: `backend/.env`

---

## 6. Future-Phase Extension Points

The structure is designed to accommodate the following without restructuring:

| Phase 2+ module | Location |
|---|---|
| Agent orchestration service | `backend/app/services/agent_service.py` |
| Agent task model | `backend/app/models/agent_task.py` |
| Findings model | `backend/app/models/finding.py` |
| Sources model | `backend/app/models/source.py` |
| Agent API routes | `backend/app/api/v1/routes/agents.py` |
| Background tasks | `backend/app/workers/` |
| Alembic migrations | `backend/alembic/` |
| Frontend agent components | `frontend/src/components/agents/` |
| Frontend findings components | `frontend/src/components/findings/` |
| Auth middleware | `backend/app/core/auth.py` |
