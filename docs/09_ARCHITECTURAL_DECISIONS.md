# 09 — Architectural Decisions

## Multi-Agent Autonomous Researcher (MAAR)
### Phase 1: Application Foundation

---

## ADR-001: Next.js App Router over Pages Router

**Status**: Accepted

**Context**: Next.js supports two routing systems. The Pages Router is the original system; the App Router (introduced in Next.js 13, stable in 14) is the current recommendation from Vercel.

**Decision**: Use the App Router.

**Rationale**:
- App Router is the current standard for new Next.js projects. Pages Router is in maintenance mode.
- React Server Components (RSC) allow dashboard and project data to be fetched server-side, eliminating client-side loading flash for initial page renders.
- Layout files (`layout.tsx`) are simpler to manage with App Router for a sidebar-based application.
- The ecosystem (shadcn/ui, documentation) is increasingly written for App Router.

**Consequences**:
- Client-only React patterns (useState, useEffect) require the `"use client"` directive. Interactive components (forms, status selectors) are explicitly client components.
- Server-to-client data passing requires careful use of server props or client-side fetch — this is managed by fetching in RSC pages and passing data to client subcomponents.

**Alternatives considered**: Pages Router — rejected because it does not support RSC, it is in maintenance mode, and migrating later would require significant restructuring.

---

## ADR-002: FastAPI over Django REST Framework

**Status**: Accepted

**Context**: The backend could have been built with Django REST Framework (DRF), Flask, or FastAPI.

**Decision**: Use FastAPI.

**Rationale**:
- FastAPI's async-first design is aligned with future AI agent workloads, which require async I/O for LLM API calls, web scraping, and long-running tasks.
- Automatic OpenAPI documentation (`/docs`) is valuable for development and testing.
- Pydantic v2 is native to FastAPI and provides excellent validation performance.
- FastAPI's dependency injection system is clean and testable.
- DRF carries significant Django ORM coupling that is unnecessary for a new project that may migrate to PostgreSQL and benefit from async ORM patterns.
- Flask requires more boilerplate for validation, serialization, and documentation.

**Consequences**:
- Python async patterns (`async def`, `await`, `AsyncSession`) must be used consistently. Mixing sync and async code causes issues.
- The developer needs familiarity with Python type hints and Pydantic models.

**Alternatives considered**: Django REST Framework — rejected due to sync ORM coupling and unnecessary overhead. Flask — rejected due to lack of built-in validation and documentation generation.

---

## ADR-003: SQLite for Phase 1, PostgreSQL-ready schema

**Status**: Accepted

**Context**: The database must be chosen for Phase 1 local development. The long-term target is likely PostgreSQL.

**Decision**: Use SQLite with aiosqlite for Phase 1. Design the schema and ORM layer to be PostgreSQL-compatible.

**Rationale**:
- SQLite requires zero installation and setup. Onboarding a new developer requires no database server.
- The database initializes automatically on the first run.
- For a single-user local application, SQLite's write-lock constraints are irrelevant.
- All column types used (VARCHAR, TEXT, DATETIME) map directly to PostgreSQL equivalents.
- Switching is a one-line `DATABASE_URL` change plus adding `asyncpg` to requirements.

**Consequences**:
- SQLite's TEXT storage for UUIDs vs. PostgreSQL's native UUID type creates a minor inconsistency. Accepted as a Phase 1 trade-off; resolved with a targeted ORM type override when migrating.
- SQLite does not enforce `ENUM` types at the database level; validation is enforced at the Pydantic/service layer.

**Alternatives considered**: PostgreSQL immediately — rejected because it requires Docker or a local installation, adding friction to the setup process. The benefits (native UUID, ENUM, better concurrency) are not needed for Phase 1.

---

## ADR-004: SQLAlchemy 2.x Async ORM over Tortoise ORM or raw SQL

**Status**: Accepted

**Context**: Several Python ORM options are available for async database access.

**Decision**: Use SQLAlchemy 2.x with the async engine.

**Rationale**:
- SQLAlchemy is the most widely adopted Python ORM. It has better documentation, community support, and third-party integrations than alternatives.
- SQLAlchemy 2.x introduced a cleaner declarative API with Python type hints and `Mapped[]` syntax.
- Alembic (migrations) integrates directly with SQLAlchemy with no additional setup.
- SQLAlchemy's abstraction layer supports SQLite, PostgreSQL, and other databases with the same model code.

**Alternatives considered**: Tortoise ORM — async-native but has a smaller ecosystem and does not integrate with Alembic. Raw SQL with aiosqlite — full control but requires manual schema management and offers no abstraction for future database migration.

---

## ADR-005: Pydantic v2 for Request and Response Validation

**Status**: Accepted

**Context**: FastAPI requires a validation library for request schemas and response serialization.

**Decision**: Use Pydantic v2.

**Rationale**:
- Pydantic v2 is the default for FastAPI 0.100+.
- v2 is significantly faster than v1 due to the Rust core.
- The `ConfigDict(from_attributes=True)` pattern cleanly bridges SQLAlchemy ORM objects to Pydantic response models.
- pydantic-settings provides typed settings management from `.env` files.

**Consequences**:
- Breaking changes from Pydantic v1 (e.g., `model_config`, `model_validate`, validator decorators) must be followed. This is a non-issue for a new project.

**Alternatives considered**: marshmallow — rejected because it is not native to FastAPI and requires more integration code.

---

## ADR-006: shadcn/ui over Material UI, Chakra UI, or Mantine

**Status**: Accepted

**Context**: The frontend requires a component library for consistent UI primitives.

**Decision**: Use shadcn/ui.

**Rationale**:
- shadcn/ui generates component source code into the project — components are owned and customizable, not locked behind a library version.
- Built on Radix UI primitives for accessibility compliance.
- Designed for Tailwind CSS; no CSS-in-JS runtime overhead.
- The visual style is clean and neutral — suitable as the foundation for a premium SaaS product.
- Direct alignment with the design references (Linear, Vercel) in terms of visual restraint and quality.
- Widely used in modern Next.js applications; strong community and documentation.

**Consequences**:
- Components are generated locally; upgrading requires manually running `npx shadcn-ui@latest add` again, which may overwrite local customizations.
- More initial setup than a fully packaged library — requires running the CLI per component.

**Alternatives considered**: Material UI — rejected because its visual style is not aligned with the premium SaaS aesthetic; heavy theming is required to remove the Material Design look. Chakra UI — considered but shadcn/ui's Tailwind-native approach is better suited for this project's design strategy. Mantine — strong library but adds more opinions and defaults that conflict with a custom design language.

---

## ADR-007: UUID Primary Keys over Auto-Increment Integers

**Status**: Accepted

**Context**: The `research_projects` table needs a primary key strategy.

**Decision**: Use UUID v4 as primary keys.

**Rationale**:
- UUIDs are safe to expose in URLs (`/projects/550e8400-...`). Sequential integers expose record counts and allow enumeration attacks.
- UUIDs are compatible with distributed systems and future sharding without collision.
- When future tables add foreign keys to `research_projects`, UUID foreign keys are globally unique.
- Python's `uuid.uuid4()` is sufficient for Phase 1; no database-level UUID generation needed.

**Consequences**:
- UUIDs are larger than integers (36 characters vs. a few bytes). Negligible impact at Phase 1 scale.
- SQLite stores UUIDs as TEXT; PostgreSQL has a native UUID type. The ORM handles both correctly.

**Alternatives considered**: Auto-increment integers — convenient but exposes resource counts in URLs and makes distributed expansion harder later.

---

## ADR-008: React Server Components for Data Fetching, not SWR or React Query

**Status**: Accepted

**Context**: The frontend needs a strategy for fetching data from the backend.

**Decision**: Use React Server Components (RSC) for initial data loading in page components. Use client-side fetch (via the typed API client) for mutations and interactive updates.

**Rationale**:
- RSC eliminates client-side loading states for the initial render of data-heavy pages (dashboard, project list, workspace).
- No additional library (SWR, React Query) is needed for Phase 1's read-heavy workload.
- Mutations (create project, update status) are client-side actions; they call the API client directly and trigger Next.js router refreshes for updated data.
- Simpler dependency footprint.

**Consequences**:
- The `"use client"` boundary must be managed carefully. Pages are server components; interactive children are client components.
- For real-time or polling updates (not needed in Phase 1), SWR or React Query would be added.

**Alternatives considered**: SWR — excellent library but adds complexity not needed for Phase 1's simple read patterns. React Query (TanStack Query) — powerful but heavyweight for Phase 1. Will be reconsidered in Phase 2 when background refetching, optimistic updates, and real-time agents are introduced.

---

## ADR-009: PATCH over PUT for Project Updates

**Status**: Accepted

**Context**: The update endpoint needs an HTTP verb.

**Decision**: Use `PATCH` for partial updates.

**Rationale**:
- The workspace's primary update action is changing the status — a single-field update.
- `PATCH` semantics (partial update) match this use case exactly.
- `PUT` requires the client to send the complete resource representation, even when only one field changes — unnecessarily verbose for status updates.
- Pydantic's `model_update` pattern handles partial updates cleanly with `exclude_unset=True`.

**Alternatives considered**: PUT — rejected because it requires complete resource transmission for single-field updates.

---

## ADR-010: Service Layer over Route-Level Database Logic

**Status**: Accepted

**Context**: Database operations could be written directly in route handlers or extracted into a service layer.

**Decision**: Extract all database operations into a `ProjectService` class, called by route handlers.

**Rationale**:
- Route handlers stay thin: parse input, call service, return response.
- Service methods are independently testable without HTTP (important for testing database behavior).
- Future capabilities (caching, logging, business rule enforcement) can be added to the service layer without touching routes.
- The pattern scales naturally when agents, findings, and sources are introduced in Phase 2.

**Consequences**:
- Slight additional indirection for simple operations. Justified by the testability and extensibility gains.

---

## ADR-011: Deferred Alembic Migrations in Phase 1

**Status**: Accepted

**Context**: Database schema migrations can be managed with `create_all()` or Alembic.

**Decision**: Use SQLAlchemy `create_all()` on startup for Phase 1. Introduce Alembic in Phase 2.

**Rationale**:
- `create_all()` is sufficient for a single-developer Phase 1 where the schema changes frequently and data loss is acceptable during development.
- Alembic adds complexity (migration scripts, versioning) that provides no benefit in Phase 1.
- The transition to Alembic in Phase 2 requires adding one package, running two initialization commands, and replacing the lifespan startup logic — no model changes.

**Consequences**:
- If the schema changes in Phase 1, the developer must drop and recreate the database manually. Documented in the troubleshooting section.

---

## Summary Table

| ADR | Decision | Key Reason |
|---|---|---|
| 001 | App Router | Current standard; RSC for performance |
| 002 | FastAPI | Async-first; native Pydantic; auto-docs |
| 003 | SQLite now, PostgreSQL-ready | Zero setup; one-line migration path |
| 004 | SQLAlchemy 2.x async | Best ecosystem; Alembic integration |
| 005 | Pydantic v2 | FastAPI native; fast; clean ORM bridge |
| 006 | shadcn/ui | Owned components; Tailwind-native; premium aesthetic |
| 007 | UUID primary keys | URL safety; distributed compatibility |
| 008 | RSC for data loading | No extra library; clean server/client boundary |
| 009 | PATCH for updates | Correct semantics for partial updates |
| 010 | Service layer | Testability; separation of concerns |
| 011 | create_all() in Phase 1 | Zero complexity for rapid development |
