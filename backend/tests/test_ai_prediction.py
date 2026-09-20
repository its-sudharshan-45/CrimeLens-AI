"""
backend/tests/test_ai_prediction.py
====================================
Pytest Suite for Phase 6.2 Crime Domain Prediction API & Batch Inference.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def sample_payload():
    return {
        "city": "Mumbai",
        "crime_description": "ROBBERY",
        "victim_age": 35,
        "victim_gender": "M",
        "weapon_used": "Firearm",
        "date_of_occurrence": "15-09-2023 04:30",
        "time_of_occurrence": "15-09-2023 04:30",
        "date_reported": "15-09-2023 14:00",
        "case_closed": "No",
        "crime_code": 110,
    }


@pytest.mark.asyncio
async def test_realtime_prediction_success(sample_payload):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/ai/predict", json=sample_payload)

    assert response.status_code == 200
    data = response.json()
    assert "predicted_domain" in data
    assert "confidence_score" in data
    assert "probabilities" in data
    assert "execution_time_ms" in data
    assert data["model_version"] == "v1.0.0"


@pytest.mark.asyncio
async def test_prediction_invalid_payload():
    invalid_payload = {"city": "Mumbai"}  # Missing required fields
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/ai/predict", json=invalid_payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_batch_prediction_success(sample_payload):
    batch_payload = {"records": [sample_payload, sample_payload]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/ai/batch-predict", json=batch_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 2
    assert len(data["predictions"]) == 2


@pytest.mark.asyncio
async def test_model_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/ai/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "models_loaded" in data


@pytest.mark.asyncio
async def test_model_metadata_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/ai/models")

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "v1.0.0"
    assert data["embedding_dim"] == 64
