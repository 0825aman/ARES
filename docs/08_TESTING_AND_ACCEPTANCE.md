# 08 — Testing and Acceptance

## Multi-Agent Autonomous Researcher (MAAR)
### Phase 1: Application Foundation

---

## 1. Testing Philosophy

Phase 1 testing focuses on verifying that the core user workflows function correctly, APIs behave as documented, data persists correctly, and the application produces appropriate errors for invalid inputs.

The test strategy is practical and minimal:
- **Backend**: Pytest-based API tests using the FastAPI test client (httpx). Tests verify the HTTP contract.
- **Frontend**: Manual verification against defined acceptance criteria, supplemented by TypeScript compiler and ESLint as static checks.
- **Integration**: End-to-end workflow verification covering the full stack, conducted manually.

Automated UI testing (Playwright, Cypress) is deferred to Phase 2, when the interface is more stable.

---

## 2. Backend Tests

### 2.1 Test Setup

**Framework**: pytest + pytest-asyncio  
**HTTP Client**: httpx `AsyncClient` with FastAPI's `ASGITransport`  
**Database**: A separate in-memory SQLite database per test session (does not touch `maar_dev.db`)

```
backend/
└── tests/
    ├── conftest.py           ← Pytest fixtures (test client, test DB)
    ├── test_health.py        ← Health check endpoint
    └── test_projects.py      ← All project endpoint tests
```

### 2.2 Health Check Tests

| Test ID | Test Description | Expected Result |
|---|---|---|
| `test_health_returns_200` | GET /health | HTTP 200 |
| `test_health_response_shape` | GET /health response contains `status`, `version`, `environment`, `database` | All keys present |
| `test_health_status_is_ok` | GET /health `status` field value | `"ok"` |
| `test_health_database_ok` | GET /health when DB is reachable | `database: "ok"` |
| `test_health_database_error` | GET /health when DB is unreachable (mock DB failure) | HTTP 200, `database: "error"` |

### 2.3 Project Creation Tests

| Test ID | Test Description | Expected Result |
|---|---|---|
| `test_create_project_minimal` | POST with title and research_question only | HTTP 201, project returned |
| `test_create_project_full` | POST with all fields including description and category | HTTP 201, all fields in response |
| `test_create_project_default_status` | POST a new project | `status` is `"not_started"` |
| `test_create_project_generates_uuid` | POST a new project | `id` is a valid UUID string |
| `test_create_project_timestamps_present` | POST a new project | `created_at` and `updated_at` are present |
| `test_create_project_timestamps_equal` | POST a new project | `created_at` equals `updated_at` on creation |
| `test_create_project_timestamps_utc` | POST a new project | `created_at` string ends with `Z` |
| `test_create_project_missing_title` | POST with no `title` | HTTP 422 |
| `test_create_project_empty_title` | POST with `title: ""` | HTTP 422 |
| `test_create_project_whitespace_only_title` | POST with `title: "   "` | HTTP 422 (stripped to empty) |
| `test_create_project_title_too_long` | POST with 201-character title | HTTP 422 |
| `test_create_project_missing_question` | POST with no `research_question` | HTTP 422 |
| `test_create_project_invalid_category` | POST with `category: "InvalidCategory"` | **HTTP 422** (not 400) |
| `test_create_project_invalid_category_error_type` | POST with invalid category | `detail[0].type == "enum"` |
| `test_create_project_null_category` | POST with `category: null` | HTTP 201 |
| `test_create_project_null_description` | POST with no `description` | HTTP 201, `description` is null |
| `test_create_project_all_categories_valid` | POST once with each valid `ProjectCategory` value | HTTP 201 for each |

### 2.4 Project List Tests

| Test ID | Test Description | Expected Result |
|---|---|---|
| `test_list_projects_empty` | GET /projects with no data | HTTP 200, `items: []`, `total: 0` |
| `test_list_projects_returns_all` | Create 3 projects, then GET /projects | `total: 3`, 3 items returned |
| `test_list_projects_ordered_by_date` | Create 3 projects, GET /projects | Newest project is first in `items` |
| `test_list_projects_response_shape` | GET /projects | Response has `items`, `total`, `limit`, `offset` |
| `test_list_projects_limit` | GET /projects?limit=2 with 5 projects | 2 items returned, `limit: 2` in response |
| `test_list_projects_limit_reflected` | GET /projects?limit=2 | Response `limit` field equals 2 |
| `test_list_projects_offset` | GET /projects?offset=2 with 5 projects | 3 items returned (items 3–5) |
| `test_list_projects_offset_reflected` | GET /projects?offset=2 | Response `offset` field equals 2 |
| `test_list_projects_total_is_pre_pagination` | Create 5 projects, GET /projects?limit=2 | `total: 5`, `items` has 2 entries |
| `test_list_projects_filter_by_status` | Create mix of statuses, GET /projects?status=in_progress | Only in_progress projects returned |
| `test_list_projects_filter_total` | Create 2 in_progress + 3 completed, filter by in_progress | `total: 2` |
| `test_list_projects_invalid_status_filter` | GET /projects?status=flying | HTTP 422 |
| `test_list_projects_limit_too_large` | GET /projects?limit=501 | HTTP 422 |
| `test_list_projects_limit_zero` | GET /projects?limit=0 | HTTP 422 |
| `test_list_projects_negative_offset` | GET /projects?offset=-1 | HTTP 422 |

### 2.5 Project Retrieval Tests

| Test ID | Test Description | Expected Result |
|---|---|---|
| `test_get_project_exists` | Create a project, then GET /projects/{id} | HTTP 200, correct project data |
| `test_get_project_not_found` | GET /projects/{random_uuid} | HTTP 404 |
| `test_get_project_invalid_id` | GET /projects/not-a-uuid | HTTP 422 |
| `test_get_project_all_fields_present` | GET /projects/{id} | All required fields in response |

### 2.6 Project Summary Tests

| Test ID | Test Description | Expected Result |
|---|---|---|
| `test_summary_empty` | GET /projects/summary with no data | `total: 0`, all statuses 0 |
| `test_summary_counts_by_status` | Create projects with different statuses, GET /summary | `by_status` counts match |
| `test_summary_recent_projects` | Create 7 projects, GET /summary | `recent_projects` has ≤ 5 items |
| `test_summary_recent_projects_ordered` | Create multiple projects | `recent_projects` ordered newest-first |

### 2.7 Project Update Tests

| Test ID | Test Description | Expected Result |
|---|---|---|
| `test_update_status` | PATCH {id} with `{"status": "in_progress"}` | HTTP 200, `status` is `"in_progress"` |
| `test_update_title` | PATCH {id} with new title | HTTP 200, title updated |
| `test_update_multiple_fields` | PATCH {id} with title and status | Both fields updated |
| `test_update_not_found` | PATCH non-existent UUID | HTTP 404 |
| `test_update_invalid_status` | PATCH with `{"status": "flying"}` | HTTP 422 |
| `test_update_invalid_category` | PATCH with `{"category": "Nonsense"}` | **HTTP 422** (not 400) |
| `test_update_updates_timestamp` | PATCH project with a field change, check `updated_at` | `updated_at` > original `updated_at` |
| `test_update_does_not_change_created_at` | PATCH project | `created_at` unchanged |
| `test_update_empty_body_no_timestamp_change` | PATCH with `{}` | HTTP 200, `updated_at` unchanged |
| `test_update_omitted_field_unchanged` | PATCH with only `status`; verify `title` unchanged | `title` equals original value |
| `test_update_clear_optional_field` | PATCH with `{"description": null}` after setting description | HTTP 200, `description` is `null` |
| `test_update_clear_category` | PATCH with `{"category": null}` | HTTP 200, `category` is `null` |
| `test_update_title_to_null_rejected` | PATCH with `{"title": null}` | HTTP 422 |
| `test_update_research_question_to_null_rejected` | PATCH with `{"research_question": null}` | HTTP 422 |
| `test_update_whitespace_only_title_rejected` | PATCH with `{"title": "   "}` | HTTP 422 (stripped to empty) |
| `test_update_timestamps_are_utc` | PATCH project, inspect `updated_at` | `updated_at` string ends with `Z` |

### 2.8 Project Delete Tests

| Test ID | Test Description | Expected Result |
|---|---|---|
| `test_delete_project` | Create then DELETE /projects/{id} | HTTP 204 |
| `test_delete_project_removed` | Delete, then GET same {id} | HTTP 404 |
| `test_delete_not_found` | DELETE non-existent UUID | HTTP 404 |
| `test_delete_invalid_uuid` | DELETE /projects/not-a-uuid | HTTP 422 |
| `test_delete_does_not_affect_other_projects` | Create 2, delete 1, GET /projects | `total: 1`, only undeleted project returned |

### 2.9 Database Error Tests

These tests mock or simulate database failures to verify the application handles them gracefully.

| Test ID | Test Description | Expected Result |
|---|---|---|
| `test_db_failure_returns_500` | Simulate DB error during GET /projects | HTTP 500 |
| `test_db_failure_does_not_leak_internals` | Simulate DB error, inspect response | `detail` does not contain a Python traceback or internal path |
| `test_health_db_error_reflected` | Mock `SELECT 1` to raise, GET /health | HTTP 200, `database: "error"` |

These tests use `pytest` monkeypatching or `unittest.mock.patch` to replace the database session's execute method with one that raises `SQLAlchemyError`.

### 2.10 Running Backend Tests

**macOS / Linux**
```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
pytest tests/ -v --cov=app --cov-report=term-missing
```

**Windows PowerShell**
```powershell
cd backend
.venv\Scripts\Activate.ps1
pytest tests/ -v
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## 3. Frontend Verification

Frontend verification is manual in Phase 1. The following acceptance criteria must be checked for each page.

### 3.1 Application Shell

| Check | Expected |
|---|---|
| Visit any page | Sidebar is visible with all navigation items |
| Active page | Correct nav item is highlighted |
| Sidebar links | All links route to correct pages without full page reload |
| Page header | Shows correct page title for each route |
| TypeScript | `npm run build` completes with zero type errors |
| Lint | `npm run lint` completes with zero errors |

### 3.2 Dashboard

| Check | Expected |
|---|---|
| No projects | Empty state displays with CTA |
| With projects | Stat cards show correct counts |
| Recent projects | Up to 5 most recent projects listed |
| Recent project link | Clicking a row navigates to its workspace |
| "New Research" button | Navigates to `/projects/new` |
| Data source | Stats are fetched from API (verify via Network tab; no hardcoded numbers) |
| Skeleton loading | Brief skeleton visible before data loads |

### 3.3 Project List

| Check | Expected |
|---|---|
| No projects | Empty state with CTA |
| With projects | All projects shown as cards |
| Project card content | Title, category badge, status badge, creation date visible |
| Project card link | Clicking navigates to workspace |
| "+ New Research" button | Navigates to `/projects/new` |

### 3.4 Create Project Form

| Check | Expected |
|---|---|
| Submit with empty fields | Title and research question show required errors |
| Title over 200 chars | Error: "Title must be 200 characters or fewer." |
| Research question over 1000 chars | Error shown |
| Valid submission | Button shows spinner during API call |
| Successful creation | Redirect to workspace + success toast |
| Cancel | Returns to `/projects` |
| Created project | Visible in project list after creation |
| Browser refresh | Project persists (not lost) |

### 3.5 Research Workspace

| Check | Expected |
|---|---|
| Open valid project | Title, research question, description, category, status, dates displayed |
| Status dropdown | Shows current status |
| Change status | API call made; status updates in place; success toast |
| Description missing | "No description provided." text displayed |
| Three placeholder sections | Visible with "Coming in Phase 2" badge |
| Invalid project ID | 404 state displayed |
| Back link | Returns to `/projects` |

---

## 4. Integration Verification

These tests verify the full frontend-to-database workflow.

| Check | Expected |
|---|---|
| Create project via form | Project appears in backend database |
| Refresh dashboard | Stats update to reflect the new project |
| Refresh project list | New project appears |
| Refresh workspace | Data matches database |
| Update status via workspace | Database `status` column updates (verify via API call) |
| Restart backend | Projects created before restart are still visible in the frontend |
| Invalid API request | Frontend shows error toast, not a blank or broken page |
| Backend offline | Frontend shows a clear error, not an unhandled crash |

---

## 5. Phase 1 Completion Checklist

The following checklist defines when Phase 1 is considered complete. All items must be checked.

### Backend
- [ ] All backend unit tests pass with zero failures.
- [ ] All 7 API endpoints respond correctly for valid requests.
- [ ] Validation errors are returned for all documented invalid inputs.
- [ ] Database initializes automatically on startup.
- [ ] Created projects persist across backend restarts.
- [ ] FastAPI docs available at `/docs`.

### Frontend
- [ ] `npm run build` completes with zero TypeScript errors.
- [ ] `npm run lint` completes with zero lint errors.
- [ ] All 5 routes render without console errors.
- [ ] All navigation links work.
- [ ] Dashboard shows correct data from API.
- [ ] Project creation form validates and submits correctly.
- [ ] Project list shows all persisted projects.
- [ ] Research workspace shows correct project data.
- [ ] Status update works from the workspace.
- [ ] Empty states are displayed where appropriate.
- [ ] Loading states (skeletons) are displayed during data fetching.
- [ ] Error states are displayed for failed API calls.
- [ ] Success toasts confirm mutations.

### Integration
- [ ] Frontend communicates with FastAPI backend (no hardcoded arrays as primary data source).
- [ ] Creating a project through the UI persists to SQLite.
- [ ] Dashboard stat counts match the actual database content.
- [ ] Browser refresh does not lose any project data.
- [ ] Invalid form submissions return clear error messages.
- [ ] Two terminal commands start the full application after initial setup.

### Design and UX
- [ ] Application is visually consistent with the UI/UX specification.
- [ ] Color palette matches defined tokens.
- [ ] Typography uses the Inter font throughout.
- [ ] Status badges use the correct colors per status.
- [ ] Placeholder sections communicate future functionality without pretending it exists.
- [ ] Application does not look like a generic admin dashboard template.
