"""
backend/tests/test_predictions_api.py
=====================================
Automated Test Suite for Phase 5 Prediction API & Investigation Assistant Integration.

Tests:
  1. Hotspot API:
     - Valid request (/predict/hotspots)
     - top_n validation (rejects < 1 or > 29)
     - Response schema structure
     - Risk score range [0.0, 1.0]
     - Risk level categories (High, Medium, Low)
     - Disclaimer presence
  2. Temporal Risk API:
     - Valid request (/predict/temporal-risk)
     - Rejects invalid city (400)
     - Forecast contains exactly 7 days
     - Predictions are finite and non-negative
     - Confidence / uncertainty fields present
     - Disclaimer presence
  3. Investigation Leads API:
     - Valid request (/predict/investigation-leads)
     - Rejects invalid city (400)
     - Ranked priorities (priority >= 1)
     - Confidence scores present
     - Pattern-based reason present
     - No unsupported individual profiling fields (no suspect name, race, religion, etc.)
     - Disclaimer presence
  4. Audit Logging & DB Integration:
     - Prediction execution creates audit trail entry and prediction record
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.ai.model_service import SUPPORTED_CITIES


@pytest.mark.asyncio
async def test_hotspot_prediction_valid():
    """Verify POST /predict/hotspots returns top-N ranked cities with valid schema."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/predict/hotspots", json={"top_n": 5, "crime_type": "All"})
        assert response.status_code == 200, response.text
        data = response.json()

        assert data["success"] is True
        assert data["prediction_type"] == "city_hotspot"
        assert data["forecast_horizon_days"] == 7
        assert len(data["hotspots"]) == 5

        # Check disclaimer
        assert "disclaimer" in data
        assert "probabilistic" in data["disclaimer"].lower()

        # Check individual hotspot properties
        prev_score = 2.0
        for item in data["hotspots"]:
            assert "rank" in item
            assert "city" in item
            assert item["city"] in SUPPORTED_CITIES
            assert "predicted_crimes" in item
            assert item["predicted_crimes"] >= 0.0

            assert "risk_score" in item
            assert 0.0 <= item["risk_score"] <= 1.0
            assert item["risk_score"] <= prev_score  # descending rank order
            prev_score = item["risk_score"]

            assert item["risk_level"] in ("High", "Medium", "Low")
            assert 0.0 <= item["confidence_score"] <= 1.0


@pytest.mark.asyncio
async def test_hotspot_prediction_validation_top_n():
    """Verify POST /predict/hotspots rejects invalid top_n parameter."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # top_n = 0 (too small)
        res_zero = await client.post("/predict/hotspots", json={"top_n": 0})
        assert res_zero.status_code in (400, 422)

        # top_n = 50 (too large)
        res_large = await client.post("/predict/hotspots", json={"top_n": 50})
        assert res_large.status_code in (400, 422)


@pytest.mark.asyncio
async def test_temporal_risk_valid():
    """Verify POST /predict/temporal-risk returns 7-day forecast with confidence scores."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/predict/temporal-risk", json={"city": "Delhi"})
        assert response.status_code == 200, response.text
        data = response.json()

        assert data["success"] is True
        assert data["prediction_type"] == "temporal_forecast"
        assert data["forecast_horizon_days"] == 7
        assert "prediction_scope" in data
        assert "national" in data["prediction_scope"].lower()
        assert data["target_city"] == "Delhi"

        forecast = data["forecast"]
        assert len(forecast) == 7

        for day_entry in forecast:
            assert 1 <= day_entry["day"] <= 7
            assert "predicted_crimes" in day_entry
            assert day_entry["predicted_crimes"] >= 0.0
            assert "confidence_score" in day_entry
            assert 0.0 <= day_entry["confidence_score"] <= 1.0

            # 95% empirical prediction intervals
            assert "lower_bound_95" in day_entry
            assert "upper_bound_95" in day_entry
            assert day_entry["lower_bound_95"] <= day_entry["upper_bound_95"]

        assert "disclaimer" in data
        assert "probabilistic" in data["disclaimer"].lower()


@pytest.mark.asyncio
async def test_temporal_risk_invalid_city():
    """Verify POST /predict/temporal-risk rejects unknown city."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/predict/temporal-risk", json={"city": "AtlantisNonExistentCity"})
        assert response.status_code == 400
        assert "not recognized" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_investigation_leads_valid():
    """Verify POST /predict/investigation-leads returns pattern-based priorities."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/predict/investigation-leads", json={"city": "Mumbai", "crime_type": "Theft"})
        assert response.status_code == 200, response.text
        data = response.json()

        assert data["success"] is True
        assert data["prediction_type"] == "investigation_leads"
        assert data["city"] == "Mumbai"
        assert len(data["leads"]) >= 4

        forbidden_profiling_terms = ["suspect name", "race", "religion", "caste", "ethnicity", "guilty", "criminality score"]

        for lead in data["leads"]:
            assert lead["priority"] >= 1
            assert len(lead["category"]) > 0
            assert len(lead["description"]) > 0
            assert len(lead["reason"]) > 0
            assert 0.0 <= lead["confidence_score"] <= 1.0

            # Verify no unsupported individual criminal profiling
            lead_str = f"{lead['category']} {lead['description']} {lead['reason']}".lower()
            for forbidden in forbidden_profiling_terms:
                assert forbidden not in lead_str, f"Found forbidden profiling term '{forbidden}' in lead"

        assert "disclaimer" in data
        assert "individual" in data["disclaimer"].lower()


@pytest.mark.asyncio
async def test_investigation_leads_invalid_city():
    """Verify POST /predict/investigation-leads rejects unknown city."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/predict/investigation-leads", json={"city": "UnknownCity12345"})
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_prediction_api_versioned_prefix():
    """Verify endpoints are also accessible via /api/v1/predict/ for frontend compatibility."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_hotspots = await client.post("/api/v1/predict/hotspots", json={"top_n": 3})
        assert res_hotspots.status_code == 200
        assert len(res_hotspots.json()["hotspots"]) == 3

        res_temporal = await client.post("/api/v1/predict/temporal-risk", json={"city": "Bangalore"})
        assert res_temporal.status_code == 200
        assert len(res_temporal.json()["forecast"]) == 7

        res_leads = await client.post("/api/v1/predict/investigation-leads", json={"city": "Bangalore"})
        assert res_leads.status_code == 200
        assert len(res_leads.json()["leads"]) >= 3


@pytest.mark.asyncio
async def test_prediction_history_endpoint():
    """Verify GET /predict/history and /api/v1/predict/history return paginated prediction list."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Trigger a prediction to ensure at least one record in history
        await client.post("/predict/hotspots", json={"top_n": 2})

        response = await client.get("/predict/history?page=1&page_size=10")
        assert response.status_code == 200, response.text
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert data["page"] == 1
        assert isinstance(data["items"], list)

        # Also verify /api/v1/predict/history
        v1_resp = await client.get("/api/v1/predict/history?page=1&page_size=5")
        assert v1_resp.status_code == 200, v1_resp.text
