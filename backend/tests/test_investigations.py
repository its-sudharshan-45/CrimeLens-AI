import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_investigation_success(client: AsyncClient, admin_token_headers, db_session, report_id, investigator_id):
    """Test successful investigation creation by an authorized user."""
    payload = {
        "report_id": str(report_id),
        "investigator_id": str(investigator_id),
        "priority": "HIGH",
    }

    response = await client.post("/api/v1/investigations", json=payload, headers=admin_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPEN"
    assert data["priority"] == "HIGH"
    assert data["report_id"] == str(report_id)
    assert data["investigator_id"] == str(investigator_id)


@pytest.mark.asyncio
async def test_create_investigation_unauthenticated(client: AsyncClient, report_id, investigator_id):
    """Test that unauthenticated requests cannot create investigations."""
    payload = {
        "report_id": str(report_id),
        "investigator_id": str(investigator_id),
        "priority": "MEDIUM",
    }

    response = await client.post("/api/v1/investigations", json=payload)

    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_assign_investigator_changes_status(client: AsyncClient, admin_token_headers, db_session, report_id, investigator_id, new_investigator_id):
    """Test that assigning an investigator to an OPEN investigation transitions it to UNDER_INVESTIGATION."""
    create_resp = await client.post(
        "/api/v1/investigations",
        json={"report_id": str(report_id), "investigator_id": str(investigator_id), "priority": "MEDIUM"},
        headers=admin_token_headers
    )
    assert create_resp.status_code == 200
    inv_id = create_resp.json()["id"]

    assign_resp = await client.post(
        f"/api/v1/investigations/{inv_id}/assign",
        json={"investigator_id": str(new_investigator_id)},
        headers=admin_token_headers
    )
    assert assign_resp.status_code == 200
    data = assign_resp.json()
    assert data["status"] == "UNDER_INVESTIGATION"
    assert data["investigator_id"] == str(new_investigator_id)


@pytest.mark.asyncio
async def test_duplicate_active_assignment_rejected(client: AsyncClient, admin_token_headers, db_session, report_id, investigator_id):
    """Test that assigning the same investigator twice raises a 400 error."""
    create_resp = await client.post(
        "/api/v1/investigations",
        json={"report_id": str(report_id), "investigator_id": str(investigator_id), "priority": "LOW"},
        headers=admin_token_headers
    )
    inv_id = create_resp.json()["id"]

    assign_resp = await client.post(
        f"/api/v1/investigations/{inv_id}/assign",
        json={"investigator_id": str(investigator_id)},
        headers=admin_token_headers
    )
    assert assign_resp.status_code == 400


@pytest.mark.asyncio
async def test_invalid_status_transition_rejected(client: AsyncClient, admin_token_headers, db_session, report_id, investigator_id):
    """Test that transitioning from OPEN directly to CLOSED is rejected (400)."""
    create_resp = await client.post(
        "/api/v1/investigations",
        json={"report_id": str(report_id), "investigator_id": str(investigator_id), "priority": "MEDIUM"},
        headers=admin_token_headers
    )
    inv_id = create_resp.json()["id"]

    status_resp = await client.patch(
        f"/api/v1/investigations/{inv_id}/status",
        json={"status": "CLOSED"},
        headers=admin_token_headers
    )
    assert status_resp.status_code == 400
    assert "Invalid status transition" in status_resp.json()["detail"]


@pytest.mark.asyncio
async def test_valid_status_transition_succeeds(client: AsyncClient, admin_token_headers, db_session, report_id, investigator_id):
    """Test that transitioning from OPEN to UNDER_INVESTIGATION succeeds."""
    create_resp = await client.post(
        "/api/v1/investigations",
        json={"report_id": str(report_id), "investigator_id": str(investigator_id), "priority": "MEDIUM"},
        headers=admin_token_headers
    )
    inv_id = create_resp.json()["id"]

    status_resp = await client.patch(
        f"/api/v1/investigations/{inv_id}/status",
        json={"status": "UNDER_INVESTIGATION"},
        headers=admin_token_headers
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "UNDER_INVESTIGATION"


@pytest.mark.asyncio
async def test_archived_investigation_is_read_only(client: AsyncClient, admin_token_headers, db_session, report_id, investigator_id):
    """Test that an archived investigation cannot be modified."""
    create_resp = await client.post(
        "/api/v1/investigations",
        json={"report_id": str(report_id), "investigator_id": str(investigator_id), "priority": "LOW"},
        headers=admin_token_headers
    )
    inv_id = create_resp.json()["id"]

    await client.patch(f"/api/v1/investigations/{inv_id}/status", json={"status": "UNDER_INVESTIGATION"}, headers=admin_token_headers)
    await client.patch(f"/api/v1/investigations/{inv_id}/status", json={"status": "CLOSED"}, headers=admin_token_headers)
    await client.patch(f"/api/v1/investigations/{inv_id}/status", json={"status": "ARCHIVED"}, headers=admin_token_headers)

    response = await client.patch(
        f"/api/v1/investigations/{inv_id}/status",
        json={"status": "OPEN"},
        headers=admin_token_headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_and_edit_note(client: AsyncClient, admin_token_headers, db_session, report_id, investigator_id):
    """Test creating a note and verifying edited flag after PATCH."""
    create_resp = await client.post(
        "/api/v1/investigations",
        json={"report_id": str(report_id), "investigator_id": str(investigator_id), "priority": "MEDIUM"},
        headers=admin_token_headers
    )
    inv_id = create_resp.json()["id"]

    note_resp = await client.post(
        f"/api/v1/investigations/{inv_id}/notes",
        json={"note": "Initial investigation note."},
        headers=admin_token_headers
    )
    assert note_resp.status_code == 200
    note_data = note_resp.json()
    note_id = note_data["id"]
    assert note_data["edited"] is False

    edit_resp = await client.patch(
        f"/api/v1/investigations/notes/{note_id}",
        json={"note": "Updated investigation note."},
        headers=admin_token_headers
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["edited"] is True
    assert edit_resp.json()["note"] == "Updated investigation note."


@pytest.mark.asyncio
async def test_timeline_records_events(client: AsyncClient, admin_token_headers, db_session, report_id, investigator_id):
    """Test that investigation creation generates timeline events."""
    create_resp = await client.post(
        "/api/v1/investigations",
        json={"report_id": str(report_id), "investigator_id": str(investigator_id), "priority": "CRITICAL"},
        headers=admin_token_headers
    )
    inv_id = create_resp.json()["id"]

    timeline_resp = await client.get(
        f"/api/v1/investigations/{inv_id}/timeline",
        headers=admin_token_headers
    )
    assert timeline_resp.status_code == 200
    events = timeline_resp.json()
    actions = [e["action"] for e in events]
    assert "Investigation Created" in actions
    assert "Officer Assigned" in actions


@pytest.mark.asyncio
async def test_list_investigations_filter_by_status(client: AsyncClient, admin_token_headers, db_session):
    """Test filtering investigations by status."""
    response = await client.get(
        "/api/v1/investigations?status=OPEN&page=1&page_size=10",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    for item in data["items"]:
        assert item["status"] == "OPEN"


@pytest.mark.asyncio
async def test_list_investigations_filter_by_priority(client: AsyncClient, admin_token_headers, db_session):
    """Test filtering investigations by priority."""
    response = await client.get(
        "/api/v1/investigations?priority=CRITICAL&page=1&page_size=10",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["priority"] == "CRITICAL"
