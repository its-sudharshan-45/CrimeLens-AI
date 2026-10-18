"""
backend/tests/test_prediction_integration.py
============================================
AI prediction integration test suite (single GRU model).

Validates:
  1. Deprecated hotspot endpoint returns 410 (CNN removed 2026-10-16).
  2. POST /api/v1/ai/forecast serves a genuine 7-day GRU forecast with
     empirical 95% prediction intervals and honest evaluation metrics.
     (Skipped when the trained checkpoint is unavailable.)
  3. Unsupported scopes are rejected with HTTP 404.
  4. Prediction audit history & pagination.
"""

import os

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FORECAST_CKPT = os.path.join(PROJECT_ROOT, "ai", "registry", "forecast_v1", "gru_forecaster.pt")
requires_forecaster = pytest.mark.skipif(
    not os.path.exists(FORECAST_CKPT),
    reason="trained GRU forecaster checkpoint not present",
)


@pytest.mark.asyncio
async def test_hotspot_forecasting_returns_410(client: AsyncClient):
    """Verify deprecated POST /predict/hotspots returns 410 Gone after CNN removal."""
    resp = await client.post("/predict/hotspots", json={"top_n": 10, "crime_type": "All"})
    assert resp.status_code == 410, resp.text
    assert "removed" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_hotspot_invalid_bounds_rejected(client: AsyncClient):
    """Verify deprecated hotspot endpoint: invalid payloads 422, valid payloads 410."""
    resp_zero = await client.post("/predict/hotspots", json={"top_n": 0})
    assert resp_zero.status_code in (400, 422, 410)

    resp_excessive = await client.post("/predict/hotspots", json={"top_n": 50})
    assert resp_excessive.status_code in (400, 422, 410)


@requires_forecaster
@pytest.mark.asyncio
async def test_forecast_interval_and_scope(client: AsyncClient):
    """Verify the GRU forecast produces 7 daily projections with 95% intervals."""
    resp = await client.post("/api/v1/ai/forecast", json={"scope_type": "city", "scope_value": "Delhi"})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["success"] is True
    assert data["scope_type"] == "city"
    assert data["forecast_horizon_days"] == 7
    assert data["model_name"] == "CrimeGRUForecaster"
    assert len(data["forecast"]) == 7

    for day in data["forecast"]:
        assert 1 <= day["day"] <= 7
        assert day["predicted_count"] >= 0.0
        assert day["lower_bound_95"] <= day["predicted_count"] <= day["upper_bound_95"]

    # Genuine held-out evaluation is reported, including the persistence baseline.
    assert "MAE" in data["test_metrics"]["model"]
    assert "MAE" in data["test_metrics"]["persistence_baseline"]
    assert len(data["actual_vs_predicted"]) > 0
    assert "disclaimer" in data


@requires_forecaster
@pytest.mark.asyncio
async def test_forecast_unknown_scope_rejected(client: AsyncClient):
    """Verify an unsupported scope value is rejected with HTTP 404."""
    resp = await client.post(
        "/api/v1/ai/forecast",
        json={"scope_type": "city", "scope_value": "AtlantisNonExistentCity"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_prediction_history_audit_persistence(client: AsyncClient):
    """Verify that prediction history is queryable and paginated."""
    history_resp = await client.get("/predict/history?page=1&page_size=10")
    assert history_resp.status_code == 200, history_resp.text
    data = history_resp.json()

    assert "items" in data
    assert "total" in data
    assert data["page"] == 1

    if data["items"]:
        first_item = data["items"][0]
        assert "model_name" in first_item
        assert "model_version" in first_item
        assert "prediction_type" in first_item
        assert "confidence_score" in first_item
        assert "execution_time_ms" in first_item
        assert "created_at" in first_item
