"""
backend/tests/test_prediction_integration.py
============================================
Phase 8 AI Prediction Integration Test Suite.

Validates:
  1. Phase 4 CNN City Hotspot Forecasting:
     - 29 validated cities
     - 0 <= risk_score <= 1
     - Rank monotonicity and bounds
     - Invalid top_n rejection
  2. Phase 3 GRU 7-Day Temporal Forecasting:
     - 7 daily forecasts
     - Empirical 95% prediction intervals (lower_bound_95 <= upper_bound_95)
     - Validated city support & invalid city rejection
     - National temporal scope disclosure
  3. Pattern-Based Investigation Assistant:
     - Ranked priorities with actionable reasons
     - Strict anti-profiling invariants (no individual criminal profiling)
  4. Prediction Audit History & Pagination:
     - GET /predict/history and GET /api/v1/predict/history
  5. Mandatory Ethical & Probabilistic Disclaimers.
"""

import math
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_hotspot_forecasting_numerical_validity(client: AsyncClient):
    """Verify Phase 4 CNN hotspot forecasting outputs valid numerical distributions."""
    resp = await client.post("/predict/hotspots", json={"top_n": 10, "crime_type": "All"})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["success"] is True
    assert data["forecast_horizon_days"] == 7
    assert len(data["hotspots"]) == 10

    previous_risk = 1.05
    for item in data["hotspots"]:
        # Numerical invariants
        assert 1 <= item["rank"] <= 29
        assert not math.isnan(item["risk_score"])
        assert not math.isinf(item["risk_score"])
        assert 0.0 <= item["risk_score"] <= 1.0
        assert item["predicted_crimes"] >= 0.0
        assert 0.0 <= item["confidence_score"] <= 1.0
        assert item["risk_level"] in ["High", "Medium", "Low"]

        # Monotonicity check: rankings are sorted descending by risk_score
        assert item["risk_score"] <= previous_risk + 1e-5
        previous_risk = item["risk_score"]

    # Global disclaimer check
    assert "disclaimer" in data
    assert "probabilistic" in data["disclaimer"].lower()


@pytest.mark.asyncio
async def test_hotspot_invalid_bounds_rejected(client: AsyncClient):
    """Verify top_n < 1 and top_n > 29 are rejected with 400 Bad Request."""
    resp_zero = await client.post("/predict/hotspots", json={"top_n": 0})
    assert resp_zero.status_code in [400, 422]

    resp_excessive = await client.post("/predict/hotspots", json={"top_n": 50})
    assert resp_excessive.status_code in [400, 422]


@pytest.mark.asyncio
async def test_temporal_risk_interval_and_scope(client: AsyncClient):
    """Verify Phase 3 GRU temporal forecasting produces 7-day projections with 95% intervals."""
    resp = await client.post("/predict/temporal-risk", json={"city": "Delhi"})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["success"] is True
    assert data["forecast_horizon_days"] == 7
    assert "national" in data["prediction_scope"].lower()

    forecast = data["forecast"]
    assert len(forecast) == 7

    for day in forecast:
        assert 1 <= day["day"] <= 7
        assert day["predicted_crimes"] >= 0.0
        assert "lower_bound_95" in day and "upper_bound_95" in day
        assert day["lower_bound_95"] <= day["upper_bound_95"]
        assert 0.0 <= day["confidence_score"] <= 1.0

    # Unknown city rejection
    invalid_city_resp = await client.post("/predict/temporal-risk", json={"city": "InvalidCityXYZ"})
    assert invalid_city_resp.status_code == 400


@pytest.mark.asyncio
async def test_investigation_leads_anti_profiling_invariant(client: AsyncClient):
    """Verify that investigation leads provide operational priorities with zero individual profiling."""
    resp = await client.post("/predict/investigation-leads", json={"city": "Bangalore", "crime_type": "Theft"})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["success"] is True
    assert len(data["leads"]) >= 3

    forbidden_terms = [
        "suspect name", "criminal history of individual", "race", "religion",
        "caste", "ethnicity", "guilty", "criminality score", "dangerous person",
    ]

    for lead in data["leads"]:
        assert lead["priority"] >= 1
        assert len(lead["category"]) > 0
        assert len(lead["description"]) > 0
        assert len(lead["reason"]) > 0
        assert 0.0 <= lead["confidence_score"] <= 1.0

        full_text = f"{lead['category']} {lead['description']} {lead['reason']}".lower()
        for term in forbidden_terms:
            assert term not in full_text, f"Anti-profiling violation: found '{term}' in lead"

    # Disclaimer check
    assert "disclaimer" in data
    assert "individual" in data["disclaimer"].lower()


@pytest.mark.asyncio
async def test_prediction_history_audit_persistence(client: AsyncClient):
    """Verify that predictions are logged and retrieved through the history endpoint."""
    # Trigger a prediction
    await client.post("/predict/hotspots", json={"top_n": 3})

    # Query history
    history_resp = await client.get("/predict/history?page=1&page_size=10")
    assert history_resp.status_code == 200, history_resp.text
    data = history_resp.json()

    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert data["page"] == 1

    first_item = data["items"][0]
    assert "model_name" in first_item
    assert "model_version" in first_item
    assert "prediction_type" in first_item
    assert "confidence_score" in first_item
    assert "execution_time_ms" in first_item
    assert "created_at" in first_item
