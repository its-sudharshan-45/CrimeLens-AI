"""
backend/tests/test_system_health.py
===================================
Phase 9 System Health, Hardware Resource Metrics & Model Inspection Test Suite.

Validates:
  1. GET /health status, database connectivity, and hardware metrics.
  2. GET /admin/system-health real metrics via psutil.
  3. AI model health reporting for the single active GRU forecaster with real parameter counts.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_health_endpoint_contract(client: AsyncClient):
    """Verify GET /health returns operational status, dependency checks, and hardware metrics."""
    resp = await client.get("/health")
    assert resp.status_code == 200

    data = resp.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded", "OK"]
    assert "database" in data
    assert data["database"]["ok"] is True
    assert "system" in data
    assert "cpu_percent" in data["system"]
    assert "memory_percent" in data["system"]
    assert "disk_percent" in data["system"]
    assert data["uptime_seconds"] >= 0.0


@pytest.mark.asyncio
async def test_admin_system_health_real_hardware_metrics(client: AsyncClient):
    """Verify GET /admin/system-health reports real hardware utilization via psutil."""
    resp = await client.get("/admin/system-health")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["api_status"] == "ok"
    assert data["database"]["status"] == "healthy"

    system = data["system"]
    assert 0.0 <= system["cpu_percent"] <= 100.0
    assert 0.0 <= system["memory_percent"] <= 100.0
    assert 0.0 <= system["disk_percent"] <= 100.0
    assert system["memory_used_mb"] > 0
    assert system["uptime_seconds"] >= 0.0


@pytest.mark.asyncio
async def test_ai_models_health_inspection_parameter_counts(client: AsyncClient):
    """Verify the single GRU forecaster is reported with real parameter counts when loaded."""
    resp = await client.get("/admin/system-health")
    assert resp.status_code == 200

    data = resp.json()
    models = data["ai_models"]
    assert len(models) == 1

    model = models[0]
    assert model["model_name"] == "CrimeGRUForecaster"
    model_names = [m["model_name"] for m in models]
    assert "CityHotspotCNN" not in model_names
    # Legacy classifiers/forecasters were removed with the single-model simplification.
    for removed in ("FTTransformerClassifier", "NBEATSForecaster", "CrimeEmbeddingNetwork", "EnsembleClassifier"):
        assert removed not in model_names

    from app.core.paths import read_active_forecast_version

    active_version = read_active_forecast_version()
    assert model["version"] == active_version

    if model["inference_available"]:
        assert model["parameter_count"] > 0
        assert model["loaded"] is True
        assert data["total_model_parameters"] == model["parameter_count"]
    else:
        # No trained checkpoint present in this environment — reported honestly.
        pytest.skip("GRU forecaster checkpoint not loaded; parameter counts unavailable")
