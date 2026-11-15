# 02 — Technical Architecture

## Multi-Agent Autonomous Researcher (MAAR)
### Phase 1: Application Foundation

---

## 1. Architecture Overview

MAAR Phase 1 is a two-tier local web application:

- **Frontend**: A Next.js application running at `http://localhost:3000` that renders the UI, manages client-side state, and communicates with the backend over HTTP.
- **Backend**: A FastAPI application running at `http://localhost:8000` that handles all business logic, data validation, and database access.
- **Database**: A SQLite file stored locally, accessed exclusively through the backend.

The two applications are decoupled. The frontend has no direct database access. All data operations go through the REST API.

```
┌──────────────────────────────────────────────────────────┐
│                      Browser                             │
│                                                          │
│   Next.js App (localhost:3000)                           │
│   ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│   │Dashboard │  │Projects  │  │Research Workspace     │ │
│   └────┬─────┘  └────┬─────┘  └──────────┬───────────┘ │
│        └─────────────┴───────────────────┘              │
│                       │  HTTP / JSON                     │
└───────────────────────┼──────────────────────────────────┘
                        │
┌───────────────────────┼──────────────────────────────────┐
│                  FastAPI (localhost:8000)                 │
│                       │                                  │
│   ┌───────────────────▼──────────────────┐              │
│   │         API Routers                  │              │
│   │  /health   /projects                 │              │
│   └───────────────────┬──────────────────┘              │
│                       │                                  │
│   ┌───────────────────▼──────────────────┐              │
│   │         Service Layer                │              │
│   │  ProjectService                      │              │
│   └───────────────────┬──────────────────┘              │
│                       │                                  │
│   ┌───────────────────▼──────────────────┐              │
│   │    SQLAlchemy ORM + SQLite            │              │
│   │    maar_dev.db                        │              │
│   └──────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Frontend Architecture

### 2.1 Framework and Runtime

| Concern | Choice |
|---|---|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript (strict mode) |
| Styling | Tailwind CSS v3 |
| Component library | shadcn/ui |
| Icons | Lucide React |
| HTTP client | Native fetch via a typed API client module |
| State management | React Server Components + useState/useEffect for client state |

**Why App Router over Pages Router**: App Router is the current Next.js standard. It enables React Server Components (RSC), which means initial project data can be fetched on the server for faster first load. However, interactive components (forms, status dropdowns) remain client components. This is the correct pattern for a data-heavy dashboard.

### 2.2 Frontend Layer Structure

```
frontend/
  src/
    app/                    ← Next.js App Router pages
    components/
      ui/                   ← shadcn/ui primitives
      layout/               ← Sidebar, Header, PageWrapper
      projects/             ← Project-specific components
      dashboard/            ← Dashboard-specific components
      workspace/            ← Workspace-specific components
    lib/
      api/                  ← Typed API client functions
      types/                ← Shared TypeScript interfaces
      utils/                ← Utility functions
    hooks/                  ← Custom React hooks
```

### 2.3 Routing

| Route | Page |
|---|---|
| `/` | Dashboard |
| `/projects` | Project list |
| `/projects/new` | Create new project |
| `/projects/[id]` | Research workspace |
| `/settings` | Settings placeholder |

### 2.4 API Client Pattern

All backend communication is centralized in `src/lib/api/`. No component directly constructs URLs or calls `fetch`. This allows the base URL to be configured from environment variables and makes future API changes contained.

The API client module exposes two internal base-URL resolvers:

- **`getServerApiUrl()`** — used by React Server Components (RSC). Reads the server-only `API_URL` environment variable. This value is never sent to the browser.
- **`getClientApiUrl()`** — used by client components (`"use client"`). Reads `NEXT_PUBLIC_API_URL`, which is inlined into the browser bundle at build time.

In local development both variables point to `http://localhost:8000`. In a future deployment they can differ — for example, `API_URL` might resolve to an internal Docker service name while `NEXT_PUBLIC_API_URL` resolves to a public hostname.

```typescript
// Pattern (not implementation)
// src/lib/api/projects.ts
export async function getProjects(): Promise<Project[]> { ... }       // called from RSC — uses API_URL
export async function createProject(data: CreateProjectInput): Promise<Project> { ... }  // client — uses NEXT_PUBLIC_API_URL
export async function getProject(id: string): Promise<Project> { ... }  // RSC — uses API_URL
export async function updateProject(id: string, data: UpdateProjectInput): Promise<Project> { ... }  // client — uses NEXT_PUBLIC_API_URL
export async function deleteProject(id: string): Promise<void> { ... }  // client — uses NEXT_PUBLIC_API_URL
```

### 2.5 Data Fetching Strategy

- **Dashboard and project list**: Fetched as React Server Components for SEO and initial load performance. Data is loaded server-side using `API_URL`.
- **Project workspace**: Also a server component for the initial data load; the status update control is a client component that uses `NEXT_PUBLIC_API_URL`.
- **Create project form**: Entirely client-side; submits via POST using `NEXT_PUBLIC_API_URL` and redirects on success.
- **Mutation feedback**: `useRouter` redirect + toast notification (shadcn/ui Toaster).

---

## 3. Backend Architecture

### 3.1 Framework and Runtime

| Concern | Choice |
|---|---|
| Framework | FastAPI |
| Language | Python 3.11+ |
| Validation | Pydantic v2 |
| ORM | SQLAlchemy 2.x (declarative ORM) |
| Database driver | aiosqlite (async SQLite) |
| ASGI server | Uvicorn |
| Dependency management | pip + requirements.txt |

### 3.2 Backend Layer Structure

```
backend/
  app/
    api/
      v1/
        routes/
          health.py       ← GET /health
          projects.py     ← CRUD /projects
        router.py         ← Mounts all route modules
    core/
      config.py           ← Settings from .env
      database.py         ← SQLAlchemy engine + session factory
    models/
      project.py          ← SQLAlchemy ORM model
    schemas/
      project.py          ← Pydantic request/response schemas
    services/
      project_service.py  ← Business logic, calls ORM
    main.py               ← FastAPI app factory, CORS, startup
```

### 3.3 Layered Responsibility

| Layer | File(s) | Responsibility |
|---|---|---|
| Routes | `api/v1/routes/` | HTTP handler, dependency injection, status codes |
| Schemas | `schemas/` | Request validation and response serialization |
| Services | `services/` | Business logic, orchestrates ORM calls |
| Models | `models/` | SQLAlchemy ORM declarations |
| Core | `core/` | App config, DB session, startup |

This separation ensures that when the database is swapped to PostgreSQL, only `core/config.py` and the connection string change.

### 3.4 Database Session Management

A single `AsyncSession` factory is created at startup. Each request receives a session via FastAPI's dependency injection (`Depends(get_db)`). Sessions are committed and closed automatically via context managers.

### 3.5 Startup Behavior

On startup, the application:
1. Reads configuration from `.env`.
2. Creates the SQLite database file if it does not exist.
3. Runs `create_all()` to initialize the schema (suitable for Phase 1; replaced by Alembic migrations in later phases).

---

## 4. Database Architecture

### 4.1 Engine

SQLite via aiosqlite and SQLAlchemy async engine. The database file path is controlled by the `DATABASE_URL` environment variable.

### 4.2 Schema Compatibility

All column types used in the SQLAlchemy model map directly to PostgreSQL equivalents:

| SQLite usage | PostgreSQL equivalent |
|---|---|
| String | VARCHAR |
| Text | TEXT |
| DateTime | TIMESTAMP WITH TIME ZONE |
| Enum (string-stored) | VARCHAR with CHECK constraint |

When migrating to PostgreSQL, the `DATABASE_URL` is updated; no ORM code changes.

---

## 5. Communication Contract

### 5.1 Ports

| Service | Port |
|---|---|
| Next.js frontend | 3000 |
| FastAPI backend | 8000 |

### 5.2 API Base URL

The frontend uses **two separate environment variables** for backend communication, reflecting the server/browser execution boundary:

| Variable | Read by | Exposed to browser | Purpose |
|---|---|---|---|
| `API_URL` | Next.js server (RSC, Route Handlers) | No | Server-to-backend communication |
| `NEXT_PUBLIC_API_URL` | Browser (client components) | Yes (build-time inlined) | Browser-to-backend communication |

In local development both are set to `http://localhost:8000`. In future environments:
- `API_URL` can use an internal hostname (e.g., `http://backend:8000` in Docker) that is unreachable from the browser.
- `NEXT_PUBLIC_API_URL` must always be a URL the user's browser can reach.

Both variables default to `http://localhost:8000` if not set, so the application works out of the box without configuration.

### 5.3 CORS

The backend allows requests from `http://localhost:3000`. CORS is configured using FastAPI's built-in `CORSMiddleware`.

### 5.4 Content Type

All API requests and responses use `application/json`.

---

## 6. Environment Variables

### Frontend (`frontend/.env.local`)

| Variable | Default | Exposed to browser | Purpose |
|---|---|---|---|
| `API_URL` | `http://localhost:8000` | No | Backend URL used by server components (RSC) |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Yes | Backend URL used by browser (client components) |

Both must be set to the same value in local development. They can diverge in Docker or production deployments.

### Backend (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./maar_dev.db` | SQLAlchemy connection string |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allowed origins |
| `APP_ENV` | `development` | Environment name |

---

## 7. Extensibility for Future Phases

The architecture is intentionally designed to accommodate Phase 2+ without structural rewrites:

| Future capability | Where it slots in |
|---|---|
| AI agent execution | New service in `backend/app/services/` |
| Agent task queue | New `tasks/` module; Celery or ARQ |
| Vector search | New service; Qdrant client in `services/` |
| Document storage | New `documents` router and model |
| Auth | FastAPI middleware; `users` model and router |
| PostgreSQL | Update `DATABASE_URL`; add Alembic |
| WebSocket updates | New `/ws` router in FastAPI |

---

## 8. Technology Stack Summary

| Layer | Technology | Version |
|---|---|---|
| Frontend framework | Next.js | 14 |
| UI language | TypeScript | 5 |
| Styling | Tailwind CSS | 3 |
| Component library | shadcn/ui | latest |
| Icons | Lucide React | latest |
| Backend framework | FastAPI | 0.111+ |
| Backend language | Python | 3.11+ |
| Validation | Pydantic | v2 |
| ORM | SQLAlchemy | 2.x |
| Database | SQLite | (bundled) |
| Async driver | aiosqlite | latest |
| ASGI server | Uvicorn | latest |
