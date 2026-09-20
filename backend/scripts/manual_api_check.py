"""
Manual API Verification Script for Phase 5 Endpoints.
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("=" * 70)
print("  MANUAL API VERIFICATION: PHASE 5 PREDICTION & INVESTIGATION APIS")
print("=" * 70)

# 1. Hotspot Endpoint
print("\n[1] POST /predict/hotspots")
res_h = client.post("/predict/hotspots", json={"top_n": 5, "crime_type": "All"})
print("Status Code:", res_h.status_code)
assert res_h.status_code == 200
h_data = res_h.json()
print(f"Prediction Type: {h_data.get('prediction_type')}")
print(f"Forecast Horizon: {h_data.get('forecast_horizon_days')} Days")
print("-" * 70)
for item in h_data.get("hotspots", []):
    print(f"Rank {item['rank']:<2} | {item['city']:<14} | Predicted: {item['predicted_crimes']:<6.2f} | Risk Score: {item['risk_score']:<6.4f} ({item['risk_level']:<6}) | Conf: {item['confidence_score']}")
print(f"Disclaimer: {h_data.get('disclaimer')}")

# 2. Temporal Risk Endpoint
print("\n[2] POST /predict/temporal-risk")
res_t = client.post("/predict/temporal-risk", json={"city": "Delhi"})
print("Status Code:", res_t.status_code)
assert res_t.status_code == 200
t_data = res_t.json()
print(f"Prediction Scope: {t_data.get('prediction_scope')}")
print(f"Target City: {t_data.get('target_city')}")
print("-" * 70)
for d in t_data.get("forecast", []):
    print(f"Day +{d['day']:<2} | Pred Crimes: {d['predicted_crimes']:<6.2f} | Conf: {d['confidence_score']:<4.2f} | 95% Bounds: [{d.get('lower_bound_95')} - {d.get('upper_bound_95')}]")
print(f"Disclaimer: {t_data.get('disclaimer')}")

# 3. Investigation Leads Endpoint
print("\n[3] POST /predict/investigation-leads")
res_l = client.post("/predict/investigation-leads", json={"city": "Delhi", "crime_type": "All"})
print("Status Code:", res_l.status_code)
assert res_l.status_code == 200
l_data = res_l.json()
print(f"City: {l_data.get('city')} (Risk Level: {l_data.get('risk_assessment')})")
print("-" * 70)
for lead in l_data.get("leads", []):
    print(f"Priority #{lead['priority']} [{lead['category']}] (Confidence: {lead['confidence_score']:.0%})")
    print(f"  Action: {lead['description']}")
    print(f"  Reason: {lead['reason']}")
print(f"Disclaimer: {l_data.get('disclaimer')}")

print("\n" + "=" * 70)
print("  ALL 3 ENDPOINTS VALIDATED SUCCESSFULLY - 100% OPERATIONAL")
print("=" * 70)
