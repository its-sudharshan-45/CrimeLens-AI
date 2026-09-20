"""
backend/tests/test_system_health.py
===================================
Phase 9 System Health, Hardware Resource Metrics & Model Inspection Test Suite.

Validates:
  1. GET /health status, database connectivity, and hardware metrics.
  2. GET /admin/system-health real metrics via psutil.
  3. AI model health reporting for all 5 validated deep learning models with real parameter counts.
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
    """Verify all 5 validated PyTorch models are reported with real non-zero parameter counts."""
    resp = await client.get("/admin/system-health")
    assert resp.status_code == 200

    data = resp.json()
    models = data["ai_models"]
    assert len(models) == 5

    model_names = [m["model_name"] for m in models]
    expected_models = [
        "CrimeGRUForecaster",
        "CityHotspotCNN",
        "FTTransformerClassifier",
        "NBEATSForecaster",
        "CrimeEmbeddingNetwork",
    ]
    for expected in expected_models:
        assert expected in model_names, f"Model {expected} missing from health response: {model_names}"

    # Verify each model has real positive parameter count and inference available
    for m in models:
        assert m["parameter_count"] > 0, f"Model {m['model_name']} has invalid param count: {m['parameter_count']}"
        assert m["inference_available"] is True
        assert m["version"] == "v1.0.0"

    # Total parameters across models exceeds 2 million
    total_params = data["total_model_parameters"]
    assert total_params > 2_000_000, f"Expected >2M total parameters, got: {total_params}"
