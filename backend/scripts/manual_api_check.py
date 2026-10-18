"""
Manual API verification for the CrimeLens AI forecasting API.

Exercises the live FastAPI app in-process (no server required) and asserts the
public contract of the single-model (GRU) forecasting API.

Run from the repository root with the backend environment active:

    python backend/scripts/manual_api_check.py

Steps 1-6 only need the trained artifacts in ``ai/registry/forecast_v1``.
Steps 7-8 read persisted prediction history, so they need a reachable database;
they report (rather than fail) when no database is available.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

print("=" * 70)
print("  MANUAL API VERIFICATION: SINGLE-MODEL (GRU) FORECASTING API")
print("=" * 70)

# 1. Hotspot Endpoint - DEPRECATED 410 (CNN removed 2026-10-16)
print("\n[1] POST /predict/hotspots (expect 410 Gone)")
res_h = client.post("/predict/hotspots", json={"top_n": 5, "crime_type": "All"})
print("Status Code:", res_h.status_code)
assert res_h.status_code == 410, res_h.text
print(f"Detail: {res_h.json().get('detail', '')[:160]}...")

# 2. Forecasting subsystem health
print("\n[2] GET /api/v1/ai/health")
res_health = client.get("/api/v1/ai/health")
print("Status Code:", res_health.status_code)
print(f"Payload: {res_health.json()}")
assert res_health.status_code == 200, res_health.text
assert res_health.json()["model_name"] == "CrimeGRUForecaster"

# 3. Supported scopes
print("\n[3] GET /api/v1/ai/scopes")
res_scopes = client.get("/api/v1/ai/scopes")
print("Status Code:", res_scopes.status_code)
scopes = res_scopes.json()
assert res_scopes.status_code == 200, res_scopes.text
print(f"Count: {scopes['count']} scopes")
print("First 5:", [s["key"] for s in scopes["scopes"][:5]])

# 4. Active model metadata
print("\n[4] GET /api/v1/ai/models")
res_models = client.get("/api/v1/ai/models")
print("Status Code:", res_models.status_code)
meta = res_models.json()
assert res_models.status_code == 200, res_models.text
print(
    f"Active model: {meta.get('primary_model')} {meta.get('version')} | "
    f"test MAE={meta.get('test_mae')} vs persistence MAE={meta.get('persistence_mae')}"
)

# 5. Seven-day GRU forecast for one city
print('\n[5] POST /api/v1/ai/forecast  {"scope_type": "city", "scope_value": "Delhi"}')
res_forecast = client.post("/api/v1/ai/forecast", json={"scope_type": "city", "scope_value": "Delhi"})
print("Status Code:", res_forecast.status_code)
assert res_forecast.status_code == 200, res_forecast.text
f_data = res_forecast.json()
print(f"Scope: {f_data['scope_display_name']} ({f_data['scope_type']}) | horizon={f_data['forecast_horizon_days']} days")
print("-" * 70)
for day in f_data["forecast"]:
    print(
        f"Day +{day['day']:<2} | {day['date']} | Predicted: {day['predicted_count']:<6.2f} | "
        f"95% Bounds: [{day['lower_bound_95']:.2f} - {day['upper_bound_95']:.2f}]"
    )
print("-" * 70)
metrics = f_data["test_metrics"]
print(f"Test MAE: model={metrics['model']['MAE']} vs persistence={metrics['persistence_baseline']['MAE']}")
print(f"Beats persistence (MAE): {metrics['model_beats_baseline_MAE']}")
print(f"Uncertainty: {f_data.get('uncertainty_method')}")
print(f"Disclaimer: {f_data.get('disclaimer')}")

# 6. Unknown scope -> 404
print('\n[6] POST /api/v1/ai/forecast (unknown scope, expect 404)')
res_bad = client.post("/api/v1/ai/forecast", json={"scope_type": "city", "scope_value": "Atlantis"})
print("Status Code:", res_bad.status_code)
assert res_bad.status_code == 404, res_bad.text

# 7. Prediction history (needs a database)
print("\n[7] GET /predict/history (requires a database)")
try:
    res_history = client.get("/predict/history", params={"page": 1, "page_size": 5})
    print("Status Code:", res_history.status_code)
    if res_history.status_code == 200:
        payload = res_history.json()
        print(f"Persisted predictions: {payload['total']}")
        for item in payload["items"]:
            print(f"  - [{item['prediction_type']}] {item['prediction_label']} (model={item['model_name']})")
    else:
        print("  (database unavailable - skipped)")
except Exception as exc:  # manual script: report instead of failing
    print(f"  (database unavailable: {exc})")

# 8. Prediction observability stats (needs a database)
print("\n[8] GET /predict/stats (requires a database)")
try:
    res_stats = client.get("/predict/stats")
    print("Status Code:", res_stats.status_code)
    if res_stats.status_code == 200:
        print(f"Payload: {res_stats.json()}")
    else:
        print("  (database unavailable - skipped)")
except Exception as exc:  # manual script: report instead of failing
    print(f"  (database unavailable: {exc})")

print("\n" + "=" * 70)
print("  FORECASTING API VALIDATED; DEPRECATED HOTSPOT CORRECTLY RETURNS 410 GONE")
print("=" * 70)
