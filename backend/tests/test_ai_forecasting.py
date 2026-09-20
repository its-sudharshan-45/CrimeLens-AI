"""
backend/tests/test_ai_forecasting.py
====================================
Pytest Suite for Phase 6.2 N-BEATS Time Series Forecasting API.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_forecast_7_days():
    payload = {"horizon": 7}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/ai/forecast", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["horizon"] == 7
    assert len(data["forecast_dates"]) == 7
    assert len(data["predicted_counts"]) == 7
    assert data["model_name"] == "NBEATSForecaster"


@pytest.mark.asyncio
async def test_forecast_30_days():
    payload = {"horizon": 30, "recent_sequence": [20.0] * 30}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/ai/forecast", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["horizon"] == 30
    assert len(data["predicted_counts"]) == 30


@pytest.mark.asyncio
async def test_forecast_90_days():
    payload = {"horizon": 90}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/ai/forecast", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["horizon"] == 90
    assert len(data["predicted_counts"]) == 90
