"""
backend/tests/test_ai_explainability.py
========================================
Pytest Suite for Phase 6.2 Captum Explainable AI (XAI) Endpoint.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def sample_record():
    return {
        "city": "Bangalore",
        "crime_description": "KIDNAPPING",
        "victim_age": 34,
        "victim_gender": "F",
        "weapon_used": "Blunt Object",
        "date_of_occurrence": "14-07-2023 08:30",
        "time_of_occurrence": "14-07-2023 08:30",
        "case_closed": "No",
    }


@pytest.mark.asyncio
async def test_explainability_captum_attribution(sample_record):
    payload = {"sample_record": sample_record, "target_class": 0}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/ai/explain", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "top_contributing_features" in data
    assert "saliency_scores" in data
    assert len(data["top_contributing_features"]) > 0
    assert "feature_name" in data["top_contributing_features"][0]
    assert "attribution_score" in data["top_contributing_features"][0]
