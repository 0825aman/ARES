from __future__ import annotations

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import SQLAlchemyError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE = "/api/v1/projects"


async def _create(client: AsyncClient, **kwargs) -> dict:
    """Create a project and return the JSON response body."""
    payload = {
        "title": kwargs.get("title", "Test Project"),
        "research_question": kwargs.get(
            "research_question", "What is the question?"
        ),
    }
    for key in ("description", "category", "status"):
        if key in kwargs:
            payload[key] = kwargs[key]
    response = await client.post(BASE + "/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# ===========================================================================
# 2.3 Project Creation Tests
# ===========================================================================


async def test_create_project_minimal(async_client: AsyncClient):
    resp = await async_client.post(
        BASE + "/",
        json={"title": "Minimal", "research_question": "RQ?"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Minimal"


async def test_create_project_full(async_client: AsyncClient):
    resp = await async_client.post(
        BASE + "/",
        json={
            "title": "Full",
            "research_question": "RQ?",
            "description": "Desc",
            "category": "Technology",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Full"
    assert data["description"] == "Desc"
    assert data["category"] == "Technology"


async def test_create_project_default_status(async_client: AsyncClient):
    data = await _create(async_client)
    assert data["status"] == "not_started"


async def test_create_project_generates_uuid(async_client: AsyncClient):
    data = await _create(async_client)
    # Should not raise
    uuid.UUID(data["id"])


async def test_create_project_timestamps_present(async_client: AsyncClient):
    data = await _create(async_client)
    assert "created_at" in data
    assert "updated_at" in data


async def test_create_project_timestamps_equal(async_client: AsyncClient):
    data = await _create(async_client)
    assert data["created_at"] == data["updated_at"]


async def test_create_project_timestamps_utc(async_client: AsyncClient):
    data = await _create(async_client)
    assert data["created_at"].endswith("Z")


async def test_create_project_missing_title(async_client: AsyncClient):
    resp = await async_client.post(
        BASE + "/", json={"research_question": "RQ?"}
    )
    assert resp.status_code == 422


async def test_create_project_empty_title(async_client: AsyncClient):
    resp = await async_client.post(
        BASE + "/", json={"title": "", "research_question": "RQ?"}
    )
    assert resp.status_code == 422


async def test_create_project_whitespace_only_title(async_client: AsyncClient):
    resp = await async_client.post(
        BASE + "/", json={"title": "   ", "research_question": "RQ?"}
    )
    assert resp.status_code == 422


async def test_create_project_title_too_long(async_client: AsyncClient):
    resp = await async_client.post(
        BASE + "/", json={"title": "a" * 201, "research_question": "RQ?"}
    )
    assert resp.status_code == 422


async def test_create_project_missing_question(async_client: AsyncClient):
    resp = await async_client.post(BASE + "/", json={"title": "T"})
    assert resp.status_code == 422


async def test_create_project_invalid_category(async_client: AsyncClient):
    resp = await async_client.post(
        BASE + "/",
        json={"title": "T", "research_question": "RQ?", "category": "InvalidCategory"},
    )
    assert resp.status_code == 422


async def test_create_project_invalid_category_error_type(async_client: AsyncClient):
    resp = await async_client.post(
        BASE + "/",
        json={"title": "T", "research_question": "RQ?", "category": "InvalidCategory"},
    )
    detail = resp.json()["detail"]
    assert any(d.get("type") == "enum" for d in detail)


async def test_create_project_null_category(async_client: AsyncClient):
    resp = await async_client.post(
        BASE + "/",
        json={"title": "T", "research_question": "RQ?", "category": None},
    )
    assert resp.status_code == 201


async def test_create_project_null_description(async_client: AsyncClient):
    data = await _create(async_client)
    assert data["description"] is None


async def test_create_project_all_categories_valid(async_client: AsyncClient):
    valid_categories = [
        "Technology",
        "Science",
        "Business",
        "Health & Medicine",
        "Society & Culture",
        "Environment",
        "Economics",
        "History",
        "Law & Policy",
        "Other",
    ]
    for cat in valid_categories:
        resp = await async_client.post(
            BASE + "/",
            json={"title": f"Project {cat}", "research_question": "RQ?", "category": cat},
        )
        assert resp.status_code == 201, f"Category '{cat}' failed: {resp.text}"


# ===========================================================================
# 2.4 Project List Tests
# ===========================================================================


async def test_list_projects_empty(async_client: AsyncClient):
    resp = await async_client.get(BASE + "/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_projects_returns_all(async_client: AsyncClient):
    for i in range(3):
        await _create(async_client, title=f"P{i}")
    resp = await async_client.get(BASE + "/")
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


async def test_list_projects_ordered_by_date(async_client: AsyncClient):
    p1 = await _create(async_client, title="First")
    await asyncio.sleep(0.01)
    p2 = await _create(async_client, title="Second")
    await asyncio.sleep(0.01)
    p3 = await _create(async_client, title="Third")
    resp = await async_client.get(BASE + "/")
    items = resp.json()["items"]
    # Newest first
    assert items[0]["id"] == p3["id"]
    assert items[1]["id"] == p2["id"]
    assert items[2]["id"] == p1["id"]


async def test_list_projects_response_shape(async_client: AsyncClient):
    resp = await async_client.get(BASE + "/")
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


async def test_list_projects_limit(async_client: AsyncClient):
    for i in range(5):
        await _create(async_client, title=f"P{i}")
    resp = await async_client.get(BASE + "/?limit=2")
    data = resp.json()
    assert len(data["items"]) == 2


async def test_list_projects_limit_reflected(async_client: AsyncClient):
    resp = await async_client.get(BASE + "/?limit=2")
    assert resp.json()["limit"] == 2


async def test_list_projects_offset(async_client: AsyncClient):
    for i in range(5):
        await _create(async_client, title=f"P{i}")
    resp = await async_client.get(BASE + "/?offset=2")
    data = resp.json()
    assert len(data["items"]) == 3


async def test_list_projects_offset_reflected(async_client: AsyncClient):
    resp = await async_client.get(BASE + "/?offset=2")
    assert resp.json()["offset"] == 2


async def test_list_projects_total_is_pre_pagination(async_client: AsyncClient):
    for i in range(5):
        await _create(async_client, title=f"P{i}")
    resp = await async_client.get(BASE + "/?limit=2")
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2


async def test_list_projects_filter_by_status(async_client: AsyncClient):
    # Create in_progress by patching after creation
    p1 = await _create(async_client, title="IP1")
    p2 = await _create(async_client, title="IP2")
    p3 = await _create(async_client, title="NS")
    await async_client.patch(BASE + f"/{p1['id']}", json={"status": "in_progress"})
    await async_client.patch(BASE + f"/{p2['id']}", json={"status": "in_progress"})

    resp = await async_client.get(BASE + "/?status=in_progress")
    data = resp.json()
    assert all(item["status"] == "in_progress" for item in data["items"])


async def test_list_projects_filter_total(async_client: AsyncClient):
    for i in range(2):
        p = await _create(async_client, title=f"IP{i}")
        await async_client.patch(BASE + f"/{p['id']}", json={"status": "in_progress"})
    for i in range(3):
        p = await _create(async_client, title=f"C{i}")
        await async_client.patch(BASE + f"/{p['id']}", json={"status": "completed"})

    resp = await async_client.get(BASE + "/?status=in_progress")
    assert resp.json()["total"] == 2


async def test_list_projects_invalid_status_filter(async_client: AsyncClient):
    resp = await async_client.get(BASE + "/?status=flying")
    assert resp.status_code == 422


async def test_list_projects_limit_too_large(async_client: AsyncClient):
    resp = await async_client.get(BASE + "/?limit=501")
    assert resp.status_code == 422


async def test_list_projects_limit_zero(async_client: AsyncClient):
    resp = await async_client.get(BASE + "/?limit=0")
    assert resp.status_code == 422


async def test_list_projects_negative_offset(async_client: AsyncClient):
    resp = await async_client.get(BASE + "/?offset=-1")
    assert resp.status_code == 422


# ===========================================================================
# 2.5 Project Retrieval Tests
# ===========================================================================


async def test_get_project_exists(async_client: AsyncClient):
    p = await _create(async_client, title="Exists")
    resp = await async_client.get(BASE + f"/{p['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Exists"


async def test_get_project_not_found(async_client: AsyncClient):
    resp = await async_client.get(BASE + f"/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_get_project_invalid_id(async_client: AsyncClient):
    resp = await async_client.get(BASE + "/not-a-uuid")
    assert resp.status_code == 422


async def test_get_project_all_fields_present(async_client: AsyncClient):
    p = await _create(
        async_client,
        title="AllFields",
        description="Desc",
        category="Science",
    )
    resp = await async_client.get(BASE + f"/{p['id']}")
    data = resp.json()
    for field in ("id", "title", "research_question", "description", "category", "status", "created_at", "updated_at"):
        assert field in data, f"Missing field: {field}"


# ===========================================================================
# 2.6 Project Summary Tests
# ===========================================================================


async def test_summary_empty(async_client: AsyncClient):
    resp = await async_client.get(BASE + "/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["by_status"]["not_started"] == 0
    assert data["by_status"]["in_progress"] == 0
    assert data["by_status"]["completed"] == 0
    assert data["by_status"]["archived"] == 0
    assert data["recent_projects"] == []


async def test_summary_counts_by_status(async_client: AsyncClient):
    p1 = await _create(async_client, title="P1")
    p2 = await _create(async_client, title="P2")
    p3 = await _create(async_client, title="P3")
    await async_client.patch(BASE + f"/{p2['id']}", json={"status": "in_progress"})
    await async_client.patch(BASE + f"/{p3['id']}", json={"status": "completed"})

    resp = await async_client.get(BASE + "/summary")
    data = resp.json()
    assert data["by_status"]["not_started"] == 1
    assert data["by_status"]["in_progress"] == 1
    assert data["by_status"]["completed"] == 1
    assert data["by_status"]["archived"] == 0


async def test_summary_recent_projects(async_client: AsyncClient):
    for i in range(7):
        await _create(async_client, title=f"P{i}")
    resp = await async_client.get(BASE + "/summary")
    data = resp.json()
    assert len(data["recent_projects"]) <= 5


async def test_summary_recent_projects_ordered(async_client: AsyncClient):
    for i in range(3):
        await _create(async_client, title=f"P{i}")
        await asyncio.sleep(0.01)
    resp = await async_client.get(BASE + "/summary")
    recent = resp.json()["recent_projects"]
    assert recent[0]["title"] == "P2"
    assert recent[1]["title"] == "P1"
    assert recent[2]["title"] == "P0"


# ===========================================================================
# 2.7 Project Update Tests
# ===========================================================================


async def test_update_status(async_client: AsyncClient):
    p = await _create(async_client)
    resp = await async_client.patch(BASE + f"/{p['id']}", json={"status": "in_progress"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


async def test_update_title(async_client: AsyncClient):
    p = await _create(async_client, title="Original")
    resp = await async_client.patch(BASE + f"/{p['id']}", json={"title": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated"


async def test_update_multiple_fields(async_client: AsyncClient):
    p = await _create(async_client, title="Original")
    resp = await async_client.patch(
        BASE + f"/{p['id']}",
        json={"title": "New Title", "status": "in_progress"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "New Title"
    assert data["status"] == "in_progress"


async def test_update_not_found(async_client: AsyncClient):
    resp = await async_client.patch(
        BASE + f"/{uuid.uuid4()}", json={"status": "in_progress"}
    )
    assert resp.status_code == 404


async def test_update_invalid_status(async_client: AsyncClient):
    p = await _create(async_client)
    resp = await async_client.patch(BASE + f"/{p['id']}", json={"status": "flying"})
    assert resp.status_code == 422


async def test_update_invalid_category(async_client: AsyncClient):
    p = await _create(async_client)
    resp = await async_client.patch(BASE + f"/{p['id']}", json={"category": "Nonsense"})
    assert resp.status_code == 422


async def test_update_updates_timestamp(async_client: AsyncClient):
    p = await _create(async_client)
    original_ts = p["updated_at"]
    await asyncio.sleep(0.05)
    resp = await async_client.patch(BASE + f"/{p['id']}", json={"status": "in_progress"})
    assert resp.json()["updated_at"] != original_ts


async def test_update_does_not_change_created_at(async_client: AsyncClient):
    p = await _create(async_client)
    resp = await async_client.patch(BASE + f"/{p['id']}", json={"status": "in_progress"})
    assert resp.json()["created_at"] == p["created_at"]


async def test_update_empty_body_no_timestamp_change(async_client: AsyncClient):
    p = await _create(async_client)
    resp = await async_client.patch(BASE + f"/{p['id']}", json={})
    assert resp.status_code == 200
    assert resp.json()["updated_at"] == p["updated_at"]


async def test_update_omitted_field_unchanged(async_client: AsyncClient):
    p = await _create(async_client, title="Original Title")
    resp = await async_client.patch(BASE + f"/{p['id']}", json={"status": "in_progress"})
    assert resp.json()["title"] == "Original Title"


async def test_update_clear_optional_field(async_client: AsyncClient):
    p = await _create(async_client, description="Has description")
    # Wait to allow timestamp diff; but first verify description set
    resp = await async_client.get(BASE + f"/{p['id']}")
    assert resp.json()["description"] == "Has description"
    # Now clear it
    resp = await async_client.patch(BASE + f"/{p['id']}", json={"description": None})
    assert resp.status_code == 200
    assert resp.json()["description"] is None


async def test_update_clear_category(async_client: AsyncClient):
    p = await _create(async_client, category="Technology")
    resp = await async_client.patch(BASE + f"/{p['id']}", json={"category": None})
    assert resp.status_code == 200
    assert resp.json()["category"] is None


async def test_update_title_to_null_rejected(async_client: AsyncClient):
    p = await _create(async_client)
    resp = await async_client.patch(BASE + f"/{p['id']}", json={"title": None})
    assert resp.status_code == 422


async def test_update_research_question_to_null_rejected(async_client: AsyncClient):
    p = await _create(async_client)
    resp = await async_client.patch(
        BASE + f"/{p['id']}", json={"research_question": None}
    )
    assert resp.status_code == 422


async def test_update_whitespace_only_title_rejected(async_client: AsyncClient):
    p = await _create(async_client)
    resp = await async_client.patch(BASE + f"/{p['id']}", json={"title": "   "})
    assert resp.status_code == 422


async def test_update_timestamps_are_utc(async_client: AsyncClient):
    p = await _create(async_client)
    await asyncio.sleep(0.05)
    resp = await async_client.patch(BASE + f"/{p['id']}", json={"status": "in_progress"})
    assert resp.json()["updated_at"].endswith("Z")


# ===========================================================================
# 2.8 Project Delete Tests
# ===========================================================================


async def test_delete_project(async_client: AsyncClient):
    p = await _create(async_client)
    resp = await async_client.delete(BASE + f"/{p['id']}")
    assert resp.status_code == 204


async def test_delete_project_removed(async_client: AsyncClient):
    p = await _create(async_client)
    await async_client.delete(BASE + f"/{p['id']}")
    resp = await async_client.get(BASE + f"/{p['id']}")
    assert resp.status_code == 404


async def test_delete_not_found(async_client: AsyncClient):
    resp = await async_client.delete(BASE + f"/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_delete_invalid_uuid(async_client: AsyncClient):
    resp = await async_client.delete(BASE + "/not-a-uuid")
    assert resp.status_code == 422


async def test_delete_does_not_affect_other_projects(async_client: AsyncClient):
    p1 = await _create(async_client, title="Keep")
    p2 = await _create(async_client, title="Delete")
    await async_client.delete(BASE + f"/{p2['id']}")
    resp = await async_client.get(BASE + "/")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == p1["id"]


# ===========================================================================
# 2.9 Database Error Tests
# ===========================================================================


async def test_db_failure_returns_500(async_client: AsyncClient):
    with patch(
        "app.services.project_service.ProjectService.get_projects",
        new_callable=AsyncMock,
        side_effect=SQLAlchemyError("DB error"),
    ):
        resp = await async_client.get(BASE + "/")
    assert resp.status_code == 500


async def test_db_failure_does_not_leak_internals(async_client: AsyncClient):
    with patch(
        "app.services.project_service.ProjectService.get_projects",
        new_callable=AsyncMock,
        side_effect=SQLAlchemyError("sensitive internal path"),
    ):
        resp = await async_client.get(BASE + "/")
    body = resp.text
    # Must not leak traceback or internal paths
    assert "Traceback" not in body
    assert "sensitive internal path" not in body
    assert resp.json()["detail"] == "Internal server error"


async def test_health_db_error_reflected(async_client: AsyncClient):
    with patch(
        "app.api.v1.routes.health.AsyncSession.execute",
        new_callable=AsyncMock,
        side_effect=SQLAlchemyError("DB connection failed"),
    ):
        resp = await async_client.get("/health")
    assert resp.status_code == 503
    assert resp.json()["database"] == "error"
