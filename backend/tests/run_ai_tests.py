"""
backend/tests/run_ai_tests.py
==============================
Standalone async smoke runner for the single CrimeLens AI REST API
(the GRU crime-count forecaster).

Run with:
    python backend/tests/run_ai_tests.py

Forecast assertions are skipped (with a clear message) when the trained
checkpoint is unavailable, so this never reports fabricated output.
"""

import asyncio
import os
import sys
from typing import AsyncGenerator

from httpx import ASGITransport, AsyncClient

# Set test environment variables before importing app
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "testkey")
os.environ.setdefault("JWT_SECRET", "testsecret")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from app.main import app  # noqa: E402
from app.db.session import get_db  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from app.models.base import BaseModel  # noqa: E402

FORECAST_CKPT = os.path.join(PROJECT_ROOT, "ai", "registry", "forecast_v1", "gru_forecaster.pt")


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):  # noqa: ANN001
    return "JSON"


test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


async def run_all_ai_tests() -> None:
    print("=" * 66)
    print("CRIMELENS AI — GRU FORECASTER API SMOKE TESTS")
    print("=" * 66)

    async with test_engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Health
        print("\n---> Test 1: GET /api/v1/ai/health")
        res = await ac.get("/api/v1/ai/health")
        assert res.status_code == 200, res.text
        data = res.json()
        print("    Model:", data["model_name"], "| loaded:", data["loaded"], "| scopes:", data["n_scopes"])

        if not os.path.exists(FORECAST_CKPT):
            print("\nCheckpoint not found — skipping forecast/scopes/models checks.")
            print("Run `python -m ai.forecasting.train` to produce it.")
            return

        # 2. Scopes
        print("\n---> Test 2: GET /api/v1/ai/scopes")
        res = await ac.get("/api/v1/ai/scopes")
        assert res.status_code == 200
        scopes = res.json()
        print("    Scopes:", scopes["count"])

        # 3. Models metadata
        print("\n---> Test 3: GET /api/v1/ai/models")
        res = await ac.get("/api/v1/ai/models")
        assert res.status_code == 200
        meta = res.json()
        print("    Version:", meta["version"], "| test MAE:", meta["test_mae"], "| persistence MAE:", meta["persistence_mae"])

        # 4. Forecast
        print("\n---> Test 4: POST /api/v1/ai/forecast (city:Delhi)")
        res = await ac.post("/api/v1/ai/forecast", json={"scope_type": "city", "scope_value": "Delhi"})
        assert res.status_code == 200, res.text
        forecast = res.json()
        assert len(forecast["forecast"]) == 7
        for day in forecast["forecast"]:
            print(f"    Day +{day['day']}  {day['date']}  {day['predicted_count']:.2f}  "
                  f"[{day['lower_bound_95']:.2f}, {day['upper_bound_95']:.2f}]")

        print("\n    Test metrics:", forecast["test_metrics"]["model"])
        print("    Persistence baseline:", forecast["test_metrics"]["persistence_baseline"])

    print("\n" + "=" * 66)
    print("GRU FORECASTER API SMOKE TESTS PASSED")
    print("=" * 66)


if __name__ == "__main__":
    asyncio.run(run_all_ai_tests())
