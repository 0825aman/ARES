# 01 — Phase 1 Requirements

## Multi-Agent Autonomous Researcher (MAAR)
### Phase 1: Application Foundation

---

## 1. Purpose

This document defines the scope, objectives, features, assumptions, and explicit exclusions for Phase 1 of the MAAR project.

Phase 1 establishes the application foundation — a polished, working local web application with a professional interface, a REST API backend, and a persistent database. No AI research capabilities are included at this stage.

---

## 2. Phase 1 Objectives

By the end of Phase 1, the following must be achievable:

1. The application opens in a browser at `http://localhost:3000`.
2. A polished, professional dashboard is visible on first load.
3. Users can navigate between all application sections.
4. Users can create a new research project via a form.
5. All previously created projects are visible in a project list.
6. Users can open an individual project and view its workspace.
7. Each workspace displays the project title, research question, status, and metadata.
8. All project data is persisted in a SQLite database via the FastAPI backend.
9. The frontend fetches and submits all project data through real API calls.
10. Refreshing the browser does not lose any created project data.

---

## 3. In-Scope Features

### 3.1 Dashboard
- Welcome header with application name and tagline.
- Summary statistics: total projects, completed, in-progress.
- List of recent research projects (up to 5).
- Quick action button: "New Research Project".
- Meaningful empty state when no projects have been created.
- Data is loaded from the backend, not hardcoded.

### 3.2 Research Projects
- Project list page showing all created projects.
- Each project card shows: title, category, status badge, creation date.
- Create New Project form with the following fields:
  - Research Title (required, max 200 characters)
  - Research Question (required, max 1000 characters)
  - Description (optional, max 2000 characters)
  - Category (optional, select from a defined list)
  - Initial Status defaults to "Not Started"
- Form validation with clear inline error messages.
- Success feedback after project creation (toast notification or redirect).
- Empty state for the project list when no projects exist.

### 3.3 Research Workspace
- Individual page for each project, accessible by project ID.
- Displays: title, research question, description, category, status, creation date, last updated date.
- Status can be manually updated from the workspace.
- Placeholder sections with descriptive labels:
  - Research Findings (Coming in Phase 2)
  - Sources & Citations (Coming in Phase 2)
  - Agent Activity Log (Coming in Phase 2)
- A back-navigation to the project list.

### 3.4 Navigation
- Persistent sidebar with links to: Dashboard, Research Projects, New Research, Settings.
- Settings page is a visible placeholder (no functional settings required).
- Active navigation item is visually highlighted.
- Application name/logo in the sidebar header.
- Consistent page header with the current section title.

### 3.5 API Backend
- Health check endpoint.
- Full CRUD for research projects (Create, Read, Update, Delete).
- Input validation with meaningful error responses.
- CORS configured for local frontend origin.

### 3.6 Database
- SQLite database, initialized automatically on first backend start.
- Single `research_projects` table with all required fields.
- Database file stored in a configurable location via `.env`.

---

## 4. Project Status Values

| Status | Meaning |
|---|---|
| `not_started` | Project created, no work begun |
| `in_progress` | Research is actively being conducted |
| `completed` | Research is finished |
| `archived` | Project is no longer active |

Default status on creation: `not_started`.

---

## 5. Research Categories

A fixed list of categories is provided at the application level (not database-driven in Phase 1):

- Technology
- Science
- Business
- Health & Medicine
- Society & Culture
- Environment
- Economics
- History
- Law & Policy
- Other

---

## 6. Out of Scope — Phase 1

The following are explicitly excluded from Phase 1:

- AI research execution of any kind.
- LLM integration (OpenAI, Anthropic, etc.).
- Multi-agent orchestration.
- LangGraph or any agent framework.
- Vector databases or semantic search.
- Document ingestion or processing.
- Web scraping or search tool integration.
- Real-time updates or WebSockets.
- User authentication or authorization.
- Multi-user support.
- Cloud deployment or infrastructure.
- Docker (optional convenience, not required).
- Redis or any caching layer.
- Background task queues.
- Email notifications.
- File upload or storage.

---

## 7. Assumptions

- The developer is running macOS, Linux, or Windows with WSL.
- Node.js 18+ and Python 3.11+ are available.
- The application runs locally only; no production deployment is planned at this phase.
- A single developer will work on the project at a time; no collaboration or branch strategy is specified for Phase 1.
- SQLite is sufficient for local development; the schema is designed to be forward-compatible with PostgreSQL.
- Sample/mock data is only used during UI development and is clearly marked; it does not persist or populate the production database.
- Dark mode is planned but the theme toggle infrastructure is deferred; a dark-mode-ready color system is established in Phase 1 to make the toggle easy to add.

---

## 8. Constraints

- The frontend must use actual API calls for all project data; hardcoded arrays in components are not acceptable for the primary data source.
- The database must be initialized without manual SQL commands; the backend handles migration automatically on startup.
- The project must run with two terminal commands after initial setup.
- No TypeScript `any` types in the frontend data layer.

---

## 9. Success Criteria

Phase 1 is complete when all of the following are true:

- [ ] Dashboard loads and shows correct statistics from the database.
- [ ] A research project can be created through the UI form and persists after browser refresh.
- [ ] The project list displays all persisted projects.
- [ ] An individual project workspace opens and displays correct data.
- [ ] Project status can be updated from the workspace.
- [ ] The backend returns appropriate HTTP error codes for invalid requests.
- [ ] All navigation links route to the correct pages.
- [ ] The application is visually consistent and matches the design direction.
- [ ] Backend unit tests for all API endpoints pass.
- [ ] Frontend renders without console errors in normal operation.
