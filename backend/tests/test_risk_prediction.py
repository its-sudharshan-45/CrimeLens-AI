"""
backend/tests/test_risk_prediction.py
=====================================
Tests for the simplified district risk API:

  GET  /api/v1/ai/locations — state/district catalog backed by model scopes
  POST /api/v1/ai/risk      — district risk from the trained GRU forecast

All numeric assertions are derived from the genuine model output; no expected
risk percentages are hard-coded beyond the documented relative-index formula.
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


@requires_forecaster
@pytest.mark.asyncio
async def test_locations_match_dataset_and_model(client: AsyncClient):
    response = await client.get("/api/v1/ai/locations")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["state_count"] == 15
    assert data["district_count"] == 29
    assert len(data["states"]) == 15

    delhi = next(state for state in data["states"] if state["state"] == "Delhi")
    assert delhi["districts"] == [
        {"district": "New Delhi", "city": "Delhi", "scope_key": "city:Delhi"}
    ]

    # Every catalog scope must exist in the model's scope list.
    scopes = await client.get("/api/v1/ai/scopes?scope_type=city")
    model_keys = {scope["key"] for scope in scopes.json()["scopes"]}
    catalog_keys = {
        district["scope_key"]
        for state in data["states"]
        for district in state["districts"]
    }
    assert catalog_keys == model_keys


@requires_forecaster
@pytest.mark.asyncio
async def test_risk_is_derived_from_model_forecast(client: AsyncClient):
    response = await client.post(
        "/api/v1/ai/risk",
        json={"state": "Delhi", "district": "New Delhi"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["state"] == "Delhi"
    assert data["district"] == "New Delhi"
    assert data["city"] == "Delhi"
    assert data["scope_key"] == "city:Delhi"
    assert data["model_name"] == "CrimeGRUForecaster"
    assert data["model_version"] == "forecast_v1"
    assert len(data["forecast"]) == 7
    assert data["risk_category"] in {"Low", "Medium", "High"}
    assert 0.0 <= data["risk_percentage"] <= 100.0
    assert data["district_count"] == 29
    assert data["district_rank"] == 1
    assert data["historical_incidents"] > 0
    assert data["model_test_metrics"]["MAE"] > 0

    # The risk percentage must equal the documented formula applied to the
    # forecast returned in the same response.
    average = sum(day["predicted_count"] for day in data["forecast"]) / len(data["forecast"])
    expected = min(100.0, 100.0 * average / data["peak_predicted_daily_average"])
    assert data["risk_percentage"] == pytest.approx(expected, abs=0.2)
    assert data["predicted_daily_average"] == pytest.approx(average, abs=0.01)
    assert data["predicted_7_day_total"] == pytest.approx(
        sum(day["predicted_count"] for day in data["forecast"]), abs=0.05
    )

    for day in data["forecast"]:
        assert day["lower_bound_95"] <= day["predicted_count"] <= day["upper_bound_95"]


@requires_forecaster
@pytest.mark.asyncio
async def test_risk_differs_across_districts(client: AsyncClient):
    delhi = await client.post(
        "/api/v1/ai/risk", json={"state": "Delhi", "district": "New Delhi"}
    )
    rajkot = await client.post(
        "/api/v1/ai/risk", json={"state": "Gujarat", "district": "Rajkot"}
    )
    assert delhi.status_code == 200, delhi.text
    assert rajkot.status_code == 200, rajkot.text

    high = delhi.json()
    low = rajkot.json()
    assert high["risk_percentage"] > low["risk_percentage"]
    assert high["district_rank"] < low["district_rank"]
    assert high["predicted_daily_average"] != low["predicted_daily_average"]


@requires_forecaster
@pytest.mark.asyncio
async def test_risk_accepts_case_insensitive_location(client: AsyncClient):
    response = await client.post(
        "/api/v1/ai/risk",
        json={"state": "delhi", "district": "new delhi"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["state"] == "Delhi"
    assert data["district"] == "New Delhi"


@pytest.mark.asyncio
async def test_risk_unknown_state_and_district_return_404(client: AsyncClient):
    bad_state = await client.post(
        "/api/v1/ai/risk", json={"state": "Atlantis", "district": "New Delhi"}
    )
    assert bad_state.status_code == 404

    bad_district = await client.post(
        "/api/v1/ai/risk", json={"state": "Delhi", "district": "Mumbai"}
    )
    assert bad_district.status_code == 404


@pytest.mark.asyncio
async def test_risk_rejects_blank_or_missing_fields(client: AsyncClient):
    blank = await client.post("/api/v1/ai/risk", json={"state": "  ", "district": "New Delhi"})
    assert blank.status_code == 422

    missing = await client.post("/api/v1/ai/risk", json={"state": "Delhi"})
    assert missing.status_code == 422
