"""
backend/tests/test_ai_forecasting.py
====================================
Tests for the single-model CrimeLens AI REST API (`backend/app/api/v1/ai.py`).

Endpoints:
  POST /api/v1/ai/forecast — 7-day GRU crime-count forecast for a scope
  GET  /api/v1/ai/scopes   — list supported forecasting scopes
  GET  /api/v1/ai/models   — active model version & metadata
  GET  /api/v1/ai/health   — forecasting subsystem health

These tests use the shared ``client`` fixture (in-memory SQLite overriding ``get_db``)
so they never touch a live database. Forecast/scopes/metadata assertions run only when
the trained checkpoint is present; they are skipped otherwise so the suite never
fabricates results.
"""

import os

import pytest
from httpx import AsyncClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FORECAST_CKPT = os.path.join(PROJECT_ROOT, "ai", "registry", "forecast_v1", "gru_forecaster.pt")
requires_forecaster = pytest.mark.skipif(
    not os.path.exists(FORECAST_CKPT),
    reason="trained GRU forecaster checkpoint not present",
)


@pytest.mark.asyncio
async def test_health_endpoint_reports_single_model(client: AsyncClient):
    """Verify GET /api/v1/ai/health reports the GRU forecaster (never crashes)."""
    response = await client.get("/api/v1/ai/health")
    assert response.status_code == 200
    data = response.json()
    assert data["model_name"] == "CrimeGRUForecaster"
    assert data["status"] in {"ok", "unavailable"}
    assert isinstance(data["loaded"], bool)
    assert data["n_scopes"] >= 0


@requires_forecaster
@pytest.mark.asyncio
async def test_scopes_endpoint_lists_cities_and_crime_types(client: AsyncClient):
    """Verify GET /api/v1/ai/scopes returns both scope types."""
    response = await client.get("/api/v1/ai/scopes")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 40
    types = {s["scope_type"] for s in data["scopes"]}
    assert types == {"city", "crime_type"}


@requires_forecaster
@pytest.mark.asyncio
async def test_scopes_endpoint_type_filter(client: AsyncClient):
    """Verify GET /api/v1/ai/scopes?scope_type=crime_type filters correctly."""
    response = await client.get("/api/v1/ai/scopes?scope_type=crime_type")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert all(s["scope_type"] == "crime_type" for s in data["scopes"])


@requires_forecaster
@pytest.mark.asyncio
async def test_forecast_endpoint_returns_seven_days(client: AsyncClient):
    """Verify POST /api/v1/ai/forecast returns a genuine 7-day forecast."""
    payload = {"scope_type": "city", "scope_value": "Delhi"}
    response = await client.post("/api/v1/ai/forecast", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["success"] is True
    assert data["scope_key"] == "city:Delhi"
    assert data["model_name"] == "CrimeGRUForecaster"
    assert data["forecast_horizon_days"] == 7
    assert len(data["forecast"]) == 7
    assert len(data["historical"]) > 0
    for day in data["forecast"]:
        assert day["day"] >= 1
        assert day["predicted_count"] >= 0.0
        assert day["lower_bound_95"] <= day["upper_bound_95"]


@requires_forecaster
@pytest.mark.asyncio
async def test_forecast_endpoint_case_insensitive_scope(client: AsyncClient):
    """Verify scope values resolve case-insensitively."""
    payload = {"scope_type": "city", "scope_value": "delhi"}
    response = await client.post("/api/v1/ai/forecast", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["scope_display_name"].lower() == "delhi"


@pytest.mark.asyncio
async def test_forecast_endpoint_invalid_payload_rejected(client: AsyncClient):
    """Verify missing required fields produce a 422 validation error."""
    response = await client.post("/api/v1/ai/forecast", json={"scope_type": "city"})
    assert response.status_code == 422


@requires_forecaster
@pytest.mark.asyncio
async def test_forecast_endpoint_unknown_scope_404(client: AsyncClient):
    """Verify an unsupported scope returns HTTP 404."""
    payload = {"scope_type": "city", "scope_value": "NowhereCity999"}
    response = await client.post("/api/v1/ai/forecast", json=payload)
    assert response.status_code == 404


@requires_forecaster
@pytest.mark.asyncio
async def test_models_endpoint_reports_honest_metrics(client: AsyncClient):
    """Verify GET /api/v1/ai/models exposes the GRU metadata and real test metrics."""
    response = await client.get("/api/v1/ai/models")
    assert response.status_code == 200
    data = response.json()
    assert data["primary_model"] == "CrimeGRUForecaster"
    assert data["version"] == "forecast_v1"
    assert data["seq_len"] == 30
    assert data["forecast_horizon"] == 7
    assert data["n_scopes"] >= 40
    assert data["test_mae"] is not None and data["test_mae"] > 0
    assert data["persistence_mae"] is not None and data["persistence_mae"] > 0
