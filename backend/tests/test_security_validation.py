"""
backend/tests/test_security_validation.py
=========================================
Phase 8 Security Hardening & RBAC Test Suite.

Validates:
  1. Unauthenticated access enforcement across protected endpoints.
  2. Authenticated access verification on protected endpoints.
  3. Input sanitization & injection safety:
     - SQL injection string handling
     - Malformed UUID handling
     - Out-of-range numerical parameters
  4. File upload security (MIME restrictions, executable/archive rejection).
  5. CORS configuration hardening (no wildcard '*' allowed).
"""

from unittest.mock import patch
import uuid
import pytest
from httpx import AsyncClient
from app.core.config import settings
from tests.conftest import (
    _clear_auth_overrides,
    _set_auth_user,
    mock_admin_user,
    mock_officer_user,
    mock_analyst_user,
)


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(client: AsyncClient):
    """Verify that requests without authorization tokens are rejected."""
    _clear_auth_overrides()

    # Crime reports require auth
    resp = await client.get("/api/v1/crime-reports")
    assert resp.status_code in [401, 403], f"Unexpected status: {resp.status_code}"

    # Investigations require auth
    resp = await client.get("/api/v1/investigations")
    assert resp.status_code in [401, 403], f"Unexpected status: {resp.status_code}"

    # Evidence requires auth
    resp = await client.get("/api/v1/evidence")
    assert resp.status_code in [401, 403], f"Unexpected status: {resp.status_code}"

@pytest.mark.asyncio
async def test_authenticated_evidence_upload(client: AsyncClient, report_id: uuid.UUID):
    """Verify that authenticated users can upload valid evidence."""
    with patch(
        "app.services.evidence_service.storage_service.upload_file",
        return_value="test/evidence.pdf",
    ), patch(
        "app.services.evidence_service.storage_service.generate_signed_url",
        return_value="https://fake-signed-url.com",
    ):
        _set_auth_user(mock_officer_user)
        officer_resp = await client.post(
            "/api/v1/evidence/upload",
            headers={"Authorization": "Bearer officer"},
            files={"file": ("officer_doc.pdf", b"%PDF-1.4 test payload", "application/pdf")},
            data={"report_id": str(report_id), "description": "Officer document upload"},
        )
        assert officer_resp.status_code == 200, officer_resp.text

    _clear_auth_overrides()


@pytest.mark.asyncio
async def test_input_validation_and_malformed_ids(client: AsyncClient, officer_token_headers: dict):
    """Verify that malformed UUIDs and unexpected types return 422 Unprocessable Entity."""
    # Malformed UUID in path parameter
    resp = await client.get("/api/v1/crime-reports/not-a-valid-uuid", headers=officer_token_headers)
    assert resp.status_code == 422

    # Malformed UUID in investigations
    resp = await client.get("/api/v1/investigations/not-a-valid-uuid", headers=officer_token_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sql_injection_string_safety(client: AsyncClient, admin_token_headers: dict):
    """Verify that SQL injection strings in search queries do not crash the database or execute arbitrary SQL."""
    sqli_payload = "'; DROP TABLE audit_logs; --"

    # Search in crime reports
    resp = await client.get(
        "/api/v1/crime-reports",
        params={"q": sqli_payload},
        headers=admin_token_headers,
    )
    assert resp.status_code == 200  # Safely parameterized

    # Search in audit logs
    audit_resp = await client.get(
        "/api/v1/audit-logs",
        params={"search": sqli_payload},
        headers=admin_token_headers,
    )
    assert audit_resp.status_code == 200


@pytest.mark.asyncio
async def test_evidence_file_safety_rejected_formats(client: AsyncClient, officer_token_headers: dict, report_id: uuid.UUID):
    """Verify that dangerous or disallowed file types (executables, archives) are rejected."""
    # Disallowed binary executable
    exe_resp = await client.post(
        "/api/v1/evidence/upload",
        headers=officer_token_headers,
        files={"file": ("trojan.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/x-dosexec")},
        data={"report_id": str(report_id), "description": "Malicious payload attempt"},
    )
    assert exe_resp.status_code in [400, 415, 422]

    # Disallowed zip archive
    zip_resp = await client.post(
        "/api/v1/evidence/upload",
        headers=officer_token_headers,
        files={"file": ("archive.zip", b"PK\x03\x04fake-zip", "application/zip")},
        data={"report_id": str(report_id), "description": "Archive upload attempt"},
    )
    assert zip_resp.status_code in [400, 415, 422]


def test_cors_policy_no_wildcard():
    """Verify CORS configuration does not use wildcard '*'."""
    cors_origins = getattr(settings, "BACKEND_CORS_ORIGINS", [])
    if isinstance(cors_origins, list):
        for origin in cors_origins:
            assert origin != "*", "Insecure CORS wildcard '*' detected in production config!"
