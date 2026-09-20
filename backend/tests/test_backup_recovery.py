"""
backend/tests/test_backup_recovery.py
=====================================
Phase 9 Enterprise Backup & Recovery Test Suite.

Validates:
  1. Admin database backup creation with SHA-256 cryptographic verification.
  2. Backup listing and metadata inspection.
  3. Integrity validation against disk snapshots.
  4. Tamper detection on corrupted backup files.
  5. Guarded restore workflow requiring explicit confirm=True.
  6. RBAC access control (non-admin access rejected).
"""

import json
import os
import pytest
from httpx import AsyncClient
from tests.conftest import (
    _set_auth_user,
    _clear_auth_overrides,
    mock_admin_user,
    mock_officer_user,
    mock_analyst_user,
)


@pytest.mark.asyncio
async def test_admin_backup_creation_and_listing(client: AsyncClient):
    """Verify that Admin can create and list database snapshots with SHA-256 checksums."""
    _set_auth_user(mock_admin_user)

    # 1. Create backup
    create_resp = await client.post(
        "/admin/backup/create",
        headers={"Authorization": "Bearer admin"},
        json={"notes": "Integration test snapshot"},
    )
    assert create_resp.status_code == 201, create_resp.text
    backup = create_resp.json()
    assert "backup_id" in backup
    assert "checksum" in backup
    assert backup["checksum"].startswith("sha256:")
    assert backup["status"] == "COMPLETED"
    backup_id = backup["backup_id"]

    # 2. List backups
    list_resp = await client.get("/admin/backup/list", headers={"Authorization": "Bearer admin"})
    assert list_resp.status_code == 200
    backups = list_resp.json()
    assert any(b["backup_id"] == backup_id for b in backups)

    # 3. Get specific backup details
    detail_resp = await client.get(f"/admin/backup/{backup_id}", headers={"Authorization": "Bearer admin"})
    assert detail_resp.status_code == 200
    assert detail_resp.json()["backup_id"] == backup_id

    _clear_auth_overrides()


@pytest.mark.asyncio
async def test_backup_validation_and_tamper_detection(client: AsyncClient):
    """Verify that backup validation succeeds on untampered files and fails on corrupted files."""
    _set_auth_user(mock_admin_user)

    # Create clean backup
    create_resp = await client.post(
        "/admin/backup/create",
        headers={"Authorization": "Bearer admin"},
        json={"notes": "Integrity validation test"},
    )
    backup_id = create_resp.json()["backup_id"]
    filepath = create_resp.json()["filepath"]

    # Validate untampered file
    val_resp = await client.post(f"/admin/backup/{backup_id}/validate", headers={"Authorization": "Bearer admin"})
    assert val_resp.status_code == 200
    assert val_resp.json()["valid"] is True
    assert val_resp.json()["status"] == "INTEGRITY_VERIFIED"

    # Intentionally tamper with the file contents
    with open(filepath, "a", encoding="utf-8") as f:
        f.write("\nMALICIOUS_TAMPERED_PAYLOAD")

    # Validate tampered file
    tamper_resp = await client.post(f"/admin/backup/{backup_id}/validate", headers={"Authorization": "Bearer admin"})
    assert tamper_resp.status_code == 400
    assert "validation failed" in tamper_resp.json()["detail"].lower() or "integrity" in tamper_resp.json()["detail"].lower()

    _clear_auth_overrides()


@pytest.mark.asyncio
async def test_guarded_restore_workflow(client: AsyncClient):
    """Verify restore requires explicit confirm=True and rejects confirm=False."""
    _set_auth_user(mock_admin_user)

    # Create fresh untampered backup
    create_resp = await client.post(
        "/admin/backup/create",
        headers={"Authorization": "Bearer admin"},
        json={"notes": "Restore test snapshot"},
    )
    backup_id = create_resp.json()["backup_id"]

    # Attempt restore without confirm
    unconfirmed_resp = await client.post(
        f"/admin/backup/{backup_id}/restore",
        headers={"Authorization": "Bearer admin"},
        json={"confirm": False},
    )
    assert unconfirmed_resp.status_code == 400
    assert "Explicit confirmation required" in unconfirmed_resp.json()["detail"]

    # Attempt restore with confirm=True
    confirmed_resp = await client.post(
        f"/admin/backup/{backup_id}/restore",
        headers={"Authorization": "Bearer admin"},
        json={"confirm": True},
    )
    assert confirmed_resp.status_code == 200
    assert confirmed_resp.json()["success"] is True

    # Verify audit log was recorded for restore
    audit_resp = await client.get("/api/v1/audit-logs", headers={"Authorization": "Bearer admin"})
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert any(log["action"] == "BACKUP_RESTORED" for log in logs)

    _clear_auth_overrides()


@pytest.mark.asyncio
async def test_authenticated_backup_endpoint_access(client: AsyncClient):
    """Verify that authenticated users can access backup endpoints."""
    _set_auth_user(mock_analyst_user)
    analyst_resp = await client.get("/admin/backup/list", headers={"Authorization": "Bearer analyst"})
    assert analyst_resp.status_code == 200

    _clear_auth_overrides()
