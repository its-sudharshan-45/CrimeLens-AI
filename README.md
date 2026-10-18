# CrimeLens AI

CrimeLens AI is a full-stack crime intelligence platform for exploring, managing, and analyzing Indian crime incident data. It combines a React dashboard, a FastAPI backend on Supabase PostgreSQL, and a single PyTorch **GRU** model that forecasts daily crime counts.

---

## Implemented Features

### Crime data management
- **Crime reports** — browse, search, filter, and manage incident records (imported from `Dataset/crime_dataset_india.csv`: 40,160 records, 29 cities, 21 crime types)
- **Categories & locations** — maintain crime categories and geographic locations tied to reports
- **Investigations** — create and track investigations linked to reports, with status workflow (`OPEN`, `UNDER_INVESTIGATION`, `WAITING_FOR_EVIDENCE`, `CLOSED`, etc.)
- **Evidence** — upload and manage case evidence files (images, PDF, video) with Supabase storage and audit trails

### Authentication & security
- **Supabase Auth** on the frontend — sign up, login, email verification, forgot/reset password
- **JWT verification** on the backend — ES256/RS256 via Supabase JWKS
- **Protected API routes** — authenticated access to dashboard data and AI endpoints
- **Audit logging** — searchable audit center for system and user actions
- **Security dashboard** — security-focused monitoring views

### AI & predictions
The project ships **one** working deep-learning model: a pooled PyTorch **GRU** that forecasts the
next 7 days of daily crime counts for any supported *scope* (a city or a crime type).

- **7-day crime-count forecast** — `POST /api/v1/ai/forecast` returns a genuine forward forecast,
  the historical series, empirical 95% prediction intervals, an honest held-out backtest
  (actual-vs-predicted), and evaluation metrics compared against a **persistence baseline**.
- **Supported scopes** — `GET /api/v1/ai/scopes` lists all cities and crime types.
- **Model metadata** — `GET /api/v1/ai/models` exposes the active version, dataset hash, architecture
  and held-out metrics; `GET /api/v1/ai/health` reports load status.
- **Prediction history** — every forecast is persisted with full lineage; browse it at
  `GET /predict/history`, with aggregate observability at `GET /predict/stats`.
- **City hotspot ranking (DEPRECATED)** — the Phase 4 2D-CNN was removed 2026-10-16 (the data is
  tabular, not images); `POST /predict/hotspots` now returns **410 Gone** and historical records
  remain queryable via `GET /predict/history`.

#### Honest model-quality note (2026-10)

The bundled dataset is synthetic and balanced (exactly 24 incidents/day), so city- and type-level
daily counts are close to white noise. The GRU is therefore expected to beat the persistence
baseline only modestly, and the reported metrics reflect that.

- Metrics (MAE, RMSE, WAPE, R²) are computed on an **untouched chronological test split**
  (train 2020-01-01→2022-12-31, validation 2023, test 2024-01-01→2024-07-30) and are **never hardcoded**.
- Per-scope normalisation statistics are fitted on the **training window only** — no leakage.
- If the model did not beat the baseline, the API reports that honestly rather than hiding it.
- The dataset dates are stored as **MM-DD-YYYY**; earlier code parsed them day-first, which was a bug.
- Retraining is reproducible: `python -m ai.forecasting.train --epochs 60` records the seed, split
  boundaries, feature schema, dataset hash and full evaluation results.

### MLOps & observability
- **Model registry** — single-version metadata in `ai/registry/forecast_v1/`, active version in `forecast_active.json`
- **Analytics dashboard** — prediction distribution, daily trends, latency metrics
- **Drift detection** — data drift status and reports
- **System health** — API and AI subsystem health checks, model load status
- **Backup & recovery** — create, list, and restore database snapshots

### Frontend dashboard
| Page | Purpose |
|------|---------|
| Dashboard | Overview and quick navigation |
| Crime Reports | Incident list and detail management |
| Categories / Locations | Reference data management |
| Investigations | Case workflow tracking |
| Evidence | File upload and review |
| AI Predictions | 7-day GRU crime-count forecasts, evaluation metrics, prediction history |
| Analytics | MLOps metrics, drift, model versions |
| Audit Center | Audit log search and review |
| Security / System Health / Backups | Operations and admin tooling |

### Data pipeline scripts
- `backend/scripts/dataset_normalizer.py` — normalize CSV into DB-ready records
- `backend/scripts/import_crime_dataset.py` — idempotent import into PostgreSQL
- `backend/scripts/import_investigations_from_dataset.py` — seed open investigations from CSV
- `backend/scripts/verify_dataset_import.py` — integrity checks after import

---

## Tech Stack

| Layer | Technologies |
|-------|----------------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, TanStack Query, Recharts |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic |
| Database & Auth | Supabase PostgreSQL, Supabase Auth, JWT (JWKS) |
| AI | PyTorch (GRU forecaster), NumPy, model registry |
| Testing | Pytest (backend + AI), Vitest, TypeScript build |

---

## Project Structure

```
CrimeLens-AI/
├── ai/                  # GRU forecaster (ai/forecasting/), registry, tests; legacy stack in archive/
├── backend/             # FastAPI app, services, API routes, DB models, scripts
├── Dataset/             # Source CSV (crime_dataset_india.csv)
├── frontend/            # React SPA
├── docker-compose.yml   # Local backend + frontend containers
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase project (PostgreSQL + Auth)

### 1. Environment setup

Copy templates and fill in your Supabase credentials:

```powershell
copy .env.example .env
copy backend\.env.example backend\.env
copy frontend\.env.example frontend\.env
```

### 2. Train the AI model

The GRU forecaster must be trained once before the backend can serve forecasts:

```powershell
# From the repository root
.venv\Scripts\python.exe -m ai.forecasting.train --epochs 60
```

This writes a checkpoint and honest evaluation artifacts to `ai/registry/forecast_v1/`
(metrics, plots, scope series). If you skip this step, the forecast endpoints return a clear
"model not loaded" response instead of fabricating numbers.

### 3. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -e .

# Run migrations, then import dataset (from repo root)
python -m backend.scripts.import_crime_dataset

# Start API server
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

### 5. Run tests

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/ -q
backend\.venv\Scripts\python.exe -m pytest ai/tests/ -q
cd frontend && npm run build && npm run test
```

> **Note:** Trained model weights (`.pt` files) are not committed to git. Regenerate them
> reproducibly from the repository root with `python -m ai.forecasting.train --epochs 60`
> (writes `ai/registry/forecast_v1/`) before starting the backend, or copy a
> `gru_forecaster.pt` checkpoint into `ai/registry/forecast_v1/`.

---

## Responsible Use

CrimeLens AI is a **decision-support tool** for resource planning and spatial/temporal pattern analysis — not individual criminal profiling. All AI outputs include confidence scores and disclaimers; human verification is required before operational use.

---

## License

MIT License
