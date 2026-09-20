# CrimeLens AI

CrimeLens AI is a full-stack crime intelligence platform for exploring, managing, and analyzing Indian crime incident data. It combines a React dashboard, a FastAPI backend on Supabase PostgreSQL, and PyTorch models for classification, forecasting, hotspot detection, and explainability.

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
- **Crime domain classification** — FT-Transformer + MLP ensemble (`POST /api/v1/ai/predict`)
- **Multi-horizon forecasting** — N-BEATS 7 / 30 / 90-day trend projections (`POST /api/v1/ai/forecast`)
- **City hotspot ranking** — CNN model ranks high-risk cities (`POST /api/v1/predict/hotspots`)
- **Temporal risk forecast** — GRU 7-day crime volume forecast with uncertainty intervals (`POST /api/v1/predict/temporal-risk`)
- **Investigation leads** — pattern-based investigative priorities without individual profiling (`POST /api/v1/predict/investigation-leads`)
- **Embeddings** — 64-dimensional dense vectors for similarity analysis (`POST /api/v1/ai/embedding`)
- **Explainability** — Captum integrated gradients and saliency attribution (`POST /api/v1/ai/explain`)
- **Batch inference** — bulk CSV/JSON prediction (`POST /api/v1/ai/batch-predict`)
- **Prediction history** — paginated log of past predictions from the database

### MLOps & observability
- **Model registry** — versioned model metadata (`ai/registry/v1.0.0`)
- **Model switching** — activate or roll back registered model versions
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
| AI Predictions | Hotspots, temporal risk, leads, live inference, forecasts, XAI |
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
| AI | PyTorch, scikit-learn, Captum, model registry |
| Testing | Pytest (116 backend + 47 AI tests), Vitest, TypeScript build |

---

## Project Structure

```
CrimeLens-AI/
├── ai/                  # Model architectures, training, inference, registry, tests
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

### 2. Backend

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

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

App: `http://localhost:5173`

### 4. Run tests

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/ -q
backend\.venv\Scripts\python.exe -m pytest ai/tests/ -q
cd frontend && npm run build && npm run test
```

> **Note:** Trained model weights (`.pt` files) are not committed to git. Train locally with `ai/training/` or copy weights into `ai/models/` and `ai/registry/v1.0.0/` before running inference endpoints.

---

## Responsible Use

CrimeLens AI is a **decision-support tool** for resource planning and spatial/temporal pattern analysis — not individual criminal profiling. All AI outputs include confidence scores and disclaimers; human verification is required before operational use.

---

## License

MIT License
