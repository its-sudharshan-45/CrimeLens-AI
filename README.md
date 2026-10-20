# CrimeLens AI

CrimeLens AI is a focused, full-stack **district crime risk prediction** application. It uses a
trained PyTorch **GRU** model and a real Indian crime-incident dataset to estimate near-term
incident volume for a selected state and district.

The dashboard intentionally exposes **one workflow**: choose a location, run the model, and read
the resulting risk index. Authentication, the dataset, and the trained model are preserved.

---

## What the application does

1. The user selects a **state / union territory** and then a **district**. Both pickers are
   searchable and the district list contains every officially recognised district.
2. The backend maps that district to the dataset's city scope and runs the trained GRU
   forecaster for a **7-day horizon**. Districts that are one of the 29 dataset cities use
   their own scope; every other district is served by a clearly labelled representative
   (proxy) scope.
3. The UI displays:
   - a relative **crime risk percentage**,
   - a **Low / Medium / High** risk category,
   - a visual risk gauge,
   - predicted daily incidents and the 7-day total,
   - a concise forecast summary with model provenance.

### Dataset coverage

| Item | Value |
|------|-------|
| Source | `Dataset/crime_dataset_india.csv` |
| Incidents | 40,160 raw records |
| Dataset cities (direct model scopes) | 29 |
| States/UTs listed in the dropdowns | 36 (28 States + 8 Union Territories) |
| Districts listed in the dropdowns | 789 (all officially recognised districts) |
| Crime types | 21 |
| Raw date range | 2020-01-01 → 2023-12-31 |

The dataset contains a **City** column, not state/district columns. The authoritative
city → state → district mapping lives in `ai/forecasting/locations.py` (`CITY_GEO`) and is shared
by model serving and dataset normalization. The complete State/UT → district catalogue lives in
`ai/forecasting/india_locations.py`.

Districts with a direct dataset city scope are marked `coverage="dataset"`. All other districts
are still selectable and are marked `coverage="proxy"`; their index is computed from the
representative dataset scope configured in `STATE_PROXY_CITY` (for example, Tamil Nadu districts
without their own scope use the Chennai model scope).

### Risk methodology

The risk value is a **Relative Crime Risk Index**, not a probability of crime:

```
risk_percentage = district predicted average daily incidents
                / highest predicted district average daily incidents
                × 100
```

Categories:

| Category | Index |
|----------|-------|
| High | ≥ 70% |
| Medium | ≥ 40% and < 70% |
| Low | < 40% |

All district averages are produced by the same trained GRU in one ranking pass, so scores are
directly comparable across the 29 districts. The API also returns the 95% prediction interval
and the district rank by predicted daily incident volume.

### Model

- Architecture: pooled **GRU** forecaster (`CrimeGRUForecaster`, PyTorch)
- Registry: `ai/registry/forecast_v1/gru_forecaster.pt`
- Horizon: 7 days, input window: 30 days
- Held-out test results (chronological split, never hard-coded):

| Metric | GRU model | Persistence baseline |
|--------|-----------|----------------------|
| MAE | 0.6933 | 0.9345 |
| RMSE | 0.9656 | 1.3536 |
| WAPE | 0.7221 | 0.9734 |

> The dataset is synthetic and balanced (about 24 incidents/day overall), so city-level daily
> counts are close to white noise. The GRU beats the persistence baseline on MAE, but the
> absolute improvement is modest. The application reports measured metrics only.

---

## Tech stack

| Layer | Technologies |
|-------|----------------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, TanStack Query |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) |
| Database & Auth | Supabase PostgreSQL + Supabase Auth (JWT) |
| AI | PyTorch (GRU forecaster), NumPy, model registry |
| Testing | Pytest, Vitest, TypeScript build |

---

## API endpoints

All routes are under `/api/v1`.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/ai/locations` | Complete State/UT → district catalog with model coverage |
| `POST` | `/ai/risk` | Run a district risk prediction from the trained GRU |
| `GET` | `/ai/health` | Model load status and supported scope count |
| `GET` | `/ai/scopes` | List supported city / crime-type scopes |
| `POST` | `/ai/forecast` | Raw 7-day forecast for a scope |
| `GET` | `/ai/models` | Active model metadata and held-out metrics |

Example request:

```http
POST /api/v1/ai/risk
Content-Type: application/json

{
  "state": "Delhi",
  "district": "New Delhi"
}
```

The response includes `risk_percentage`, `risk_category`, `predicted_daily_average`,
`prediction_interval_95`, `district_rank`, `forecast` (7 days), model test metrics, and a
disclaimer. It also reports `model_coverage` (`dataset` or `proxy`) and, for proxy estimates,
`proxy_city`. Invalid locations return `404`; an unavailable model returns `503`.

Frontend routes:

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/login`, `/signup`, `/forgot-password` | Supabase authentication |
| `/verify-email`, `/reset-password` | Auth callbacks |
| `/dashboard` | Protected risk prediction page |

Removed dashboard paths such as `/dashboard/reports` redirect to `/dashboard`.

---

## Project structure

```
CrimeLens-AI/
├── ai/
│   ├── forecasting/          # GRU model, predictor, State/UT + district catalogues
│   └── registry/forecast_v1/ # Checkpoint, metrics, scope series
├── backend/
│   ├── app/
│   │   ├── ai/forecast_service.py
│   │   ├── api/v1/ai.py
│   │   └── schemas/ai.py
│   └── tests/
├── Dataset/                  # Source CSV
├── frontend/
│   ├── src/pages/dashboard/RiskPredictionPage.tsx
│   ├── src/hooks/useAI.ts
│   └── src/services/aiService.ts
└── README.md
```

---

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Supabase project (PostgreSQL + Auth)

### 1. Environment setup

```powershell
copy .env.example .env
copy backend\.env.example backend\.env
copy frontend\.env.example frontend\.env
```

Fill in the Supabase credentials in both `.env` files. The frontend uses
`VITE_API_URL` (default `http://localhost:8000/api/v1`).

### 2. Model

The trained artifacts should already exist in `ai/registry/forecast_v1/`. If the checkpoint is
missing, retrain reproducibly from the repository root:

```powershell
.venv\Scripts\python.exe -m ai.forecasting.train --epochs 60
```

If the model cannot be loaded, the dashboard shows “Model unavailable” and prediction requests
return a clear `503` error instead of fabricated results.

### 3. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -e .
.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: `http://127.0.0.1:8000/docs`

### 4. Frontend

```powershell
cd frontend
npm install
npm run dev
```

App: `http://localhost:5173`

### 5. Tests

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_risk_prediction.py backend/tests/test_ai_forecasting.py -q
.venv\Scripts\python.exe -m pytest ai/tests/test_forecasting.py -q
cd frontend
npm run build
npm test
```

---

## Responsible use

CrimeLens AI is a **decision-support tool**. The relative risk index summarizes predicted
incident volume for a district; it is **not** a probability that a crime will occur and must
not be used for individual profiling. Human review is required before any operational use.

---

## License

MIT License
