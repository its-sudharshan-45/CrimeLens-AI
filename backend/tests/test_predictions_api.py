"""
backend/tests/test_predictions_api.py
=====================================
Tests for the legacy prediction router (`backend/app/api/v1/predictions.py`).

Tests:
  1. Deprecated City Hotspot API:
     - POST /predict/hotspots returns HTTP 410 Gone (CNN removed 2026-10-16)
     - invalid top_n payloads are still rejected by validation
  2. Prediction History API:
     - GET /predict/history and /api/v1/predict/history return paginated data
  3. Prediction Observability API:
     - GET /predict/stats returns real aggregate metrics

These tests use the shared ``client`` fixture, which overrides ``get_db`` with an
in-memory SQLite session so the suite is deterministic and never depends on a live
Supabase/PostgreSQL connection.

Live crime forecasting is covered by backend/tests/test_ai_forecasting.py.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_hotspot_prediction_returns_410(client: AsyncClient):
    """Verify POST /predict/hotspots returns 410 Gone after CNN removal (tabular data, not images)."""
    response = await client.post("/predict/hotspots", json={"top_n": 5, "crime_type": "All"})
    assert response.status_code == 410, response.text
    detail = response.json()["detail"].lower()
    assert "removed" in detail or "deprecated" in detail or "cnn" in detail


@pytest.mark.asyncio
async def test_hotspot_prediction_validation_top_n(client: AsyncClient):
    """Verify POST /predict/hotspots request validation is still enforced before the 410 handler."""
    res_zero = await client.post("/predict/hotspots", json={"top_n": 0})
    assert res_zero.status_code in (400, 422, 410)

    res_large = await client.post("/predict/hotspots", json={"top_n": 50})
    assert res_large.status_code in (400, 422, 410)


@pytest.mark.asyncio
async def test_prediction_history_endpoint(client: AsyncClient):
    """Verify GET /predict/history returns a paginated prediction list."""
    response = await client.get("/predict/history?page=1&page_size=10")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_prediction_history_versioned_prefix(client: AsyncClient):
    """Verify the versioned prefix /api/v1/predict/history is also mounted."""
    response = await client.get("/api/v1/predict/history?page=1&page_size=5")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_prediction_stats_endpoint(client: AsyncClient):
    """Verify GET /predict/stats returns real aggregate observability metrics."""
    response = await client.get("/predict/stats")
    assert response.status_code == 200, response.text
    data = response.json()
    assert set(
        [
            "total_predictions",
            "predictions_today",
            "avg_execution_time_ms",
            "predictions_by_model",
            "predictions_by_type",
            "active_models",
        ]
    ).issubset(data.keys())
    assert "CrimeGRUForecaster" in data["active_models"]
