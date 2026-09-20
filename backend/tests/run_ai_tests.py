"""
backend/tests/run_ai_tests.py
==============================
Standalone Async Test Runner for Phase 6.2 AI Model Serving REST Endpoints.
"""

import sys
import os
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport

# Set test environment variables before importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_KEY"] = "testkey"
os.environ["JWT_SECRET"] = "testsecret"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from app.main import app
from app.db.session import get_db
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import BaseModel

@compiles(JSONB, 'sqlite')
def compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"

# Create test sqlite in-memory engine
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

# Override FastAPI get_db dependency
app.dependency_overrides[get_db] = override_get_db


async def run_all_ai_tests():
    print("=" * 66)
    print("STARTING PHASE 6.2 FASTAPI AI ENDPOINTS INTEGRATION TESTS")
    print("=" * 66)

    # Initialize in-memory SQLite tables
    async with test_engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    sample_record = {
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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:

        # 1. Test GET /api/v1/ai/health
        print("\n---> Test 1: GET /api/v1/ai/health")
        res = await ac.get("/api/v1/ai/health")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        print("    Status:", data["status"])
        print("    Models Loaded:", data["models_loaded"])
        print("    PASSED!")

        # 2. Test GET /api/v1/ai/models
        print("\n---> Test 2: GET /api/v1/ai/models")
        res = await ac.get("/api/v1/ai/models")
        assert res.status_code == 200
        data = res.json()
        print("    Version:", data["version"])
        print("    Framework:", data["framework"])
        print("    Flagship Model:", data["flagship_model"])
        print("    PASSED!")

        # 3. Test POST /api/v1/ai/predict
        print("\n---> Test 3: POST /api/v1/ai/predict")
        res = await ac.post("/api/v1/ai/predict", json=sample_record)
        assert res.status_code == 200, f"Expected 200, got {res.status_code} ({res.text})"
        data = res.json()
        print("    Predicted Domain:", data["predicted_domain"])
        print("    Confidence Score:", data["confidence_score"])
        print("    Execution Time:", data["execution_time_ms"], "ms")
        print("    Prediction ID (Logged in DB):", data["prediction_id"])
        print("    PASSED!")

        # 4. Test POST /api/v1/ai/forecast (7d, 30d, 90d)
        print("\n---> Test 4: POST /api/v1/ai/forecast (7d, 30d, 90d)")
        for h in [7, 30, 90]:
            res = await ac.post("/api/v1/ai/forecast", json={"horizon": h})
            assert res.status_code == 200
            data = res.json()
            assert len(data["predicted_counts"]) == h
            print(f"    Horizon {h}d: Projected Total {data['total_projected_incidents']} incidents ({data['execution_time_ms']} ms)")
        print("    PASSED!")

        # 5. Test POST /api/v1/ai/embedding
        print("\n---> Test 5: POST /api/v1/ai/embedding")
        res = await ac.post("/api/v1/ai/embedding", json={"sample_record": sample_record})
        assert res.status_code == 200
        data = res.json()
        print("    Embedding Dim:", data["embedding_dim"])
        print("    L2 Norm:", data["l2_norm"])
        print("    First 5 elements:", data["embedding_vector"][:5])
        print("    PASSED!")

        # 6. Test POST /api/v1/ai/explain
        print("\n---> Test 6: POST /api/v1/ai/explain")
        res = await ac.post("/api/v1/ai/explain", json={"sample_record": sample_record, "target_class": 0})
        assert res.status_code == 200
        data = res.json()
        print("    Target Domain:", data["predicted_domain"])
        print("    Method:", data["method"])
        print("    Top Feature:", data["top_contributing_features"][0]["feature_name"], "=", data["top_contributing_features"][0]["attribution_score"])
        print("    PASSED!")

        # 7. Test POST /api/v1/ai/batch-predict
        print("\n---> Test 7: POST /api/v1/ai/batch-predict")
        batch_payload = {"records": [sample_record, sample_record, sample_record]}
        res = await ac.post("/api/v1/ai/batch-predict", json=batch_payload)
        assert res.status_code == 200
        data = res.json()
        print("    Total Records Processed:", data["total_records"])
        print("    Batch Execution Time:", data["batch_execution_time_ms"], "ms")
        print("    PASSED!")

    print("\n" + "=" * 66)
    print("ALL PHASE 6.2 FASTAPI AI REST ENDPOINTS VERIFIED PERFECTLY!")
    print("=" * 66)

if __name__ == "__main__":
    asyncio.run(run_all_ai_tests())
