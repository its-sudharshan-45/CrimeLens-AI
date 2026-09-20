"""
backend/tests/test_observability.py
===================================
Phase 9 Observability, Request Correlation & Latency Metrics Test Suite.

Validates:
  1. X-Request-ID generation and propagation across endpoints.
  2. Server-Timing latency response headers.
  3. Real aggregate statistics calculation via GET /predict/stats.
"""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_request_id_generated_when_omitted(client: AsyncClient):
    """Verify that requests without X-Request-ID receive a generated UUID in response."""
    resp = await client.get("/")
    assert resp.status_code == 200

    req_id = resp.headers.get("X-Request-ID")
    assert req_id is not None
    # Validate it's a valid UUID string
    parsed = uuid.UUID(req_id)
    assert str(parsed) == req_id


@pytest.mark.asyncio
async def test_request_id_propagated_when_supplied(client: AsyncClient):
    """Verify that client-supplied X-Request-ID is preserved and returned."""
    custom_id = f"client-corr-{uuid.uuid4().hex[:12]}"
    resp = await client.get("/", headers={"X-Request-ID": custom_id})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == custom_id


@pytest.mark.asyncio
async def test_server_timing_latency_header_present(client: AsyncClient):
    """Verify that Server-Timing header measures request execution duration."""
    resp = await client.get("/")
    assert resp.status_code == 200

    timing = resp.headers.get("Server-Timing")
    assert timing is not None
    assert timing.startswith("app;dur=")
    dur_str = timing.replace("app;dur=", "")
    assert float(dur_str) >= 0.0


@pytest.mark.asyncio
async def test_prediction_observability_stats_endpoint(client: AsyncClient):
    """Verify that GET /predict/stats returns real aggregate prediction counts and metrics."""
    resp = await client.get("/predict/stats")
    assert resp.status_code == 200

    data = resp.json()
    assert "total_predictions" in data
    assert isinstance(data["total_predictions"], int)
    assert "predictions_today" in data
    assert isinstance(data["predictions_today"], int)
    assert "avg_execution_time_ms" in data
    assert isinstance(data["avg_execution_time_ms"], (int, float))
    assert "predictions_by_model" in data
    assert isinstance(data["predictions_by_model"], dict)
    assert "predictions_by_type" in data
    assert isinstance(data["predictions_by_type"], dict)
    assert "active_models" in data
    assert len(data["active_models"]) == 5
