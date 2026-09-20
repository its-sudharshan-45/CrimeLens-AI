"""
backend/tests/test_ai_embedding.py
===================================
Pytest Suite for Phase 6.2 Contrastive Dense Vector Embedding API.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def sample_record():
    return {
        "city": "Delhi",
        "crime_description": "CYBER CRIME",
        "victim_age": 28,
        "victim_gender": "F",
        "weapon_used": "Unknown",
        "date_of_occurrence": "20-10-2023 10:15",
        "time_of_occurrence": "20-10-2023 10:15",
        "case_closed": "No",
    }


@pytest.mark.asyncio
async def test_generate_embedding_success(sample_record):
    payload = {"sample_record": sample_record}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/ai/embedding", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "embedding_vector" in data
    assert data["embedding_dim"] == 64
    assert len(data["embedding_vector"]) == 64
    assert data["model_name"] == "CrimeEmbeddingNetwork"
