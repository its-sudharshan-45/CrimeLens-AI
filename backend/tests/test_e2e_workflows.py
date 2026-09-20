"""
backend/tests/test_e2e_workflows.py
===================================
Phase 8 End-to-End Workflow Integration Test Suite.

Validates the complete operational lifecycle:
  1. Create Location (Officer) & Category (Admin)
  2. Create Crime Report -> DB persistence & AuditLog entry
  3. View and Update Crime Report
  4. Create Investigation linked to Report (Officer)
  5. Add Investigation Notes
  6. Upload Evidence linked to Crime Report
  7. Run AI Prediction (Hotspot, Temporal Risk, Investigation Lead)
  8. Verify complete cryptographic audit trail via GET /api/v1/audit-logs
"""

from unittest.mock import patch
import uuid
import pytest
from httpx import AsyncClient
from tests.conftest import (
    _set_auth_user,
    mock_admin_user,
    mock_officer_user,
    mock_investigator_user,
)


@pytest.mark.asyncio
async def test_full_operational_lifecycle(client: AsyncClient, investigator_id: uuid.UUID):
    """
    Test complete lifecycle from Crime Report creation through Investigation,
    Evidence attachment, AI Prediction, and Audit Log trail verification.
    """
    # ── Step 1: Create Location & Category ──────────────────────────────────
    _set_auth_user(mock_officer_user)
    loc_resp = await client.post(
        "/api/v1/crime-locations",
        headers={"Authorization": "Bearer officer"},
        json={
            "latitude": 19.0760,
            "longitude": 72.8777,
            "city": "Mumbai",
            "district": "South Mumbai",
            "state": "Maharashtra",
        },
    )
    assert loc_resp.status_code == 201, loc_resp.text
    location_id = loc_resp.json()["id"]

    _set_auth_user(mock_admin_user)
    cat_resp = await client.post(
        "/api/v1/crime-categories",
        headers={"Authorization": "Bearer admin"},
        json={
            "name": f"Armed Robbery-{uuid.uuid4().hex[:6]}",
            "description": "Armed commercial robbery",
            "severity_level": 4,
            "color_code": "#EF4444",
        },
    )
    assert cat_resp.status_code == 201, cat_resp.text
    category_id = cat_resp.json()["id"]

    # ── Step 2: Create Crime Report ─────────────────────────────────────────
    _set_auth_user(mock_officer_user)
    report_resp = await client.post(
        "/api/v1/crime-reports",
        headers={"Authorization": "Bearer officer"},
        json={
            "title": "Commercial Jewelry Store Heist",
            "description": "Suspects entered with firearms and fled in an unmarked van.",
            "incident_date": "2026-08-01T21:30:00Z",
            "priority": "HIGH",
            "category_id": category_id,
            "location_id": location_id,
        },
    )
    assert report_resp.status_code == 201, report_resp.text
    report_data = report_resp.json()
    report_id = report_data["id"]
    assert report_data["status"] == "OPEN"

    # ── Step 3: View and Update Crime Report ────────────────────────────────
    get_rep = await client.get(
        f"/api/v1/crime-reports/{report_id}",
        headers={"Authorization": "Bearer officer"},
    )
    assert get_rep.status_code == 200
    assert get_rep.json()["id"] == report_id

    update_rep = await client.patch(
        f"/api/v1/crime-reports/{report_id}",
        headers={"Authorization": "Bearer officer"},
        json={"priority": "HIGH"},
    )
    assert update_rep.status_code == 200

    # ── Step 4: Create Investigation Linked to Crime Report ─────────────────
    inv_resp = await client.post(
        "/api/v1/investigations",
        headers={"Authorization": "Bearer officer"},
        json={
            "report_id": str(report_id),
            "investigator_id": str(investigator_id),
            "priority": "HIGH",
        },
    )
    assert inv_resp.status_code == 200, inv_resp.text
    inv_data = inv_resp.json()
    investigation_id = inv_data["id"]
    assert inv_data["status"] == "OPEN"

    # ── Step 5: Add Investigation Note ──────────────────────────────────────
    note_resp = await client.post(
        f"/api/v1/investigations/{investigation_id}/notes",
        headers={"Authorization": "Bearer officer"},
        json={"note": "Recovered CCTV footage from adjacent ATM camera."},
    )
    assert note_resp.status_code == 200, note_resp.text
    assert "Recovered CCTV footage" in note_resp.json()["note"]

    # ── Step 6: Attach Evidence to Crime Report ─────────────────────────────
    with patch(
        "app.services.evidence_service.storage_service.upload_file",
        return_value="e2e/test.jpg",
    ), patch(
        "app.services.evidence_service.storage_service.generate_signed_url",
        return_value="https://fake-signed-url.com",
    ):
        evidence_resp = await client.post(
            "/api/v1/evidence/upload",
            headers={"Authorization": "Bearer officer"},
            files={"file": ("cctv_exterior.jpg", b"fake jpeg byte sequence", "image/jpeg")},
            data={
                "report_id": str(report_id),
                "description": "ATM external camera view at 21:32",
            },
        )
        assert evidence_resp.status_code == 200, evidence_resp.text
        assert evidence_resp.json()["file_name"] == "cctv_exterior.jpg"

    # ── Step 7: Run AI Predictions ──────────────────────────────────────────
    # 7a. Hotspot Forecasting
    hotspot_resp = await client.post("/predict/hotspots", json={"top_n": 5, "crime_type": "Robbery"})
    assert hotspot_resp.status_code == 200
    assert len(hotspot_resp.json()["hotspots"]) == 5

    # 7b. Temporal Risk Forecasting
    temporal_resp = await client.post("/predict/temporal-risk", json={"city": "Mumbai"})
    assert temporal_resp.status_code == 200
    assert len(temporal_resp.json()["forecast"]) == 7

    # 7c. Investigation Assistant Priorities
    leads_resp = await client.post("/predict/investigation-leads", json={"city": "Mumbai", "crime_type": "Robbery"})
    assert leads_resp.status_code == 200
    assert len(leads_resp.json()["leads"]) >= 3

    # ── Step 8: Verify Complete Audit Log Trail ─────────────────────────────
    _set_auth_user(mock_admin_user)
    audit_resp = await client.get("/api/v1/audit-logs", headers={"Authorization": "Bearer admin"})
    assert audit_resp.status_code == 200, audit_resp.text
    audit_logs = audit_resp.json()
    assert len(audit_logs) >= 3

    # Verify actions in audit trail
    actions_recorded = [log["action"] for log in audit_logs]
    assert any("PREDICTION" in a for a in actions_recorded), f"Prediction not logged: {actions_recorded}"
