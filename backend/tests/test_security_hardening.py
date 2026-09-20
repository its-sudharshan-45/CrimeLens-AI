"""
backend/tests/test_security_hardening.py
========================================
Phase 9 Security Hardening & Abuse Protection Test Suite.

Validates:
  1. Mandatory security response headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP).
  2. In-memory rate limiting / abuse protection (burst requests trigger HTTP 429 + Retry-After).
  3. Rate limit bypass for automated test suites.
  4. CORS configuration hardening (trusted origin allowed, wildcard rejected).
"""

import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.core.rate_limit import rate_limiter
from tests.conftest import _set_auth_user, mock_admin_user, _clear_auth_overrides


@pytest.mark.asyncio
async def test_security_headers_present_on_all_responses(client: AsyncClient):
    """Verify that every API response includes mandatory security headers."""
    resp = await client.get("/")
    assert resp.status_code == 200

    headers = resp.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert "Content-Security-Policy" in headers
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]


@pytest.mark.asyncio
async def test_rate_limiting_triggers_429_on_burst(client: AsyncClient):
    """Verify that exceeding rate limits on sensitive endpoints returns HTTP 429."""
    rate_limiter.reset()

    # Rule: auth login limit is 15 req/min
    responses = []
    for _ in range(18):
        resp = await client.post("/api/v1/auth/login", json={"email": "test@test.com", "password": "wrong"})
        responses.append(resp.status_code)

    # At least one request beyond the limit must be rejected with 429
    assert 429 in responses, f"Expected 429 in responses, got: {responses}"

    # Verify 429 payload structure and headers
    idx = responses.index(429)
    # Make one more request to verify header
    resp_429 = await client.post("/api/v1/auth/login", json={"email": "test@test.com", "password": "wrong"})
    assert resp_429.status_code == 429
    assert "Retry-After" in resp_429.headers
    data = resp_429.json()
    assert "Rate limit exceeded" in data["detail"]

    # Reset history so subsequent tests are unaffected
    rate_limiter.reset()


@pytest.mark.asyncio
async def test_rate_limit_bypass_header_for_internal_tasks(client: AsyncClient):
    """Verify that internal test runner bypass header allows bursts without 429."""
    rate_limiter.reset()

    responses = []
    for _ in range(20):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@test.com", "password": "wrong"},
            headers={"X-Bypass-Rate-Limit": "crimelens-test"},
        )
        responses.append(resp.status_code)

    assert 429 not in responses
    rate_limiter.reset()


def test_cors_policy_trusted_origins():
    """Verify that CORS origins are explicitly defined and do not contain wildcards."""
    origins = getattr(settings, "BACKEND_CORS_ORIGINS", [])
    assert len(origins) > 0
    assert "*" not in origins, "Wildcard '*' must never be permitted in CORS config."
    assert any("5173" in o for o in origins), "Frontend development origin (5173) should be trusted."
