# CrimeLens AI

CrimeLens AI is an end-to-end Deep Learning & Crime Intelligence Assistant designed for law enforcement pattern analysis, temporal risk forecasting, spatial hotspot detection, and investigative resource allocation.

Built as a robust, production-ready system, CrimeLens AI combines validated PyTorch deep learning models with an asynchronous FastAPI backend and a responsive React 19 / TypeScript frontend.

---

## System Architecture

```
                                  ┌───────────────────────────────┐
                                  │      React 19 + TypeScript    │
                                  │   (Tailwind CSS + Lucide UI)  │
                                  └──────────────┬────────────────┘
                                                 │ REST (Axios / TanStack Query)
                                                 ▼
                                  ┌───────────────────────────────┐
                                  │        FastAPI Backend        │
                                  │ (Async SQLAlchemy + PostgreSQL│
                                  │   / SQLite + JWT Auth + RBAC) │
                                  └──────────────┬────────────────┘
                                                 │
                   ┌─────────────────────────────┼─────────────────────────────┐
                   │                             │                             │
                   ▼                             ▼                             ▼
        ┌─────────────────────┐       ┌─────────────────────┐       ┌─────────────────────┐
        │   Phase 3 Model     │       │    Phase 4 Model    │       │    Registry v1.0.0  │
        │ 2-Layer PyTorch GRU │       │  3-Layer Spatial    │       │  FT-Transformer     │
        │ Temporal Forecaster │       │     PyTorch CNN     │       │  Contrastive Vector │
        │ (95% Pred Interval) │       │ Hotspot Forecaster  │       │  N-BEATS Forecaster │
        └─────────────────────┘       └─────────────────────┘       └─────────────────────┘
```

- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, TanStack Query, Recharts, Lucide Icons.
- **Backend API**: FastAPI (Async), SQLAlchemy 2.0 Async, Pydantic v2, PostgreSQL / SQLite.
- **Deep Learning Engine**: PyTorch, Captum (XAI attribution), scikit-learn, joblib.
- **Testing & Verification**: Pytest (136 passing tests across AI and backend suites), strict TypeScript build verification.

---

## Validated Deep Learning Models

1. **Phase 3 GRU Temporal Forecaster** (`CrimeGRUForecaster`):
   - 2-layer Gated Recurrent Unit evaluating multivariate temporal indicators over a 30-day historical window.
   - Generates 7-day future crime volume projections with empirical 95% uncertainty prediction intervals.
2. **Phase 4 CNN Hotspot Forecaster** (`CNNHotspotForecaster`):
   - 3-layer 1D CNN neural network with spatial MaxPool and Dropout.
   - Evaluates crime incident density across 29 validated cities to rank high-risk geographic areas.
3. **FT-Transformer & MLP Ensemble** (`FTTransformerClassifier` + `CrimeMLPClassifier`):
   - Feature Tokenizer Transformer with multi-head self-attention for tabular incident domain classification.
4. **Contrastive Dense Embedding Network** (`CrimeEmbeddingNetwork`):
   - 64-dimensional L2-normalized dense embeddings (R^64) for semantic similarity analysis with FT-Transformer CLS token fallback.
5. **N-BEATS Forecaster** (`NBEATSForecaster`):
   - Deep neural basis expansion time-series forecaster for 7-day, 30-day, and 90-day incident horizons.

---

## Project Structure

```
CrimeLens-AI/
├── ai/                      # AI workspace, training pipelines, models, tests
│   ├── inference/           # Standalone model inference engines
│   ├── models/              # Model architectures (GRU, CNN, FT-Transformer)
│   ├── preprocessing/       # Pipeline, feature engineering, data cleaners
│   ├── registry/v1.0.0/     # Versioned model artifacts & checkpoints
│   └── tests/               # 47 automated AI pipeline tests
├── backend/                 # Asynchronous FastAPI backend
│   ├── app/
│   │   ├── ai/              # Singleton ModelLoader & ModelService
│   │   ├── api/v1/          # REST routes (predictions, crime, auth, mlops)
│   │   ├── core/            # Config, security, logging, enums
│   │   ├── db/              # SQLAlchemy session & database base
│   │   ├── models/          # Database ORM models (User, Report, AuditLog)
│   │   ├── schemas/         # Pydantic validation schemas
│   │   └── services/        # Business logic & AI orchestration
│   └── tests/               # 89 automated backend integration tests
├── frontend/                # React 19 + TypeScript single-page application
│   ├── src/
│   │   ├── components/      # Reusable UI & AI visualization components
│   │   ├── hooks/           # TanStack Query & state hooks
│   │   ├── pages/           # Dashboard views & authentication
│   │   └── services/        # API client services
└── README.md
```

---

## Test Coverage & Validation

All automated test suites pass with **100% success rate**:

| Test Suite | Total Tests | Passed | Failed |
| :--- | :---: | :---: | :---: |
| **Backend Integration Tests** (`backend/tests/`) | 89 | **89** | 0 |
| **AI Pipeline & Model Tests** (`ai/tests/`) | 47 | **47** | 0 |
| **Total Automated Tests** | **136** | **136** | **0** |
| **Frontend TypeScript Build** (`npm run build`) | — | **0 Errors** | 0 |

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Backend Setup & Test Execution
```powershell
# Run all backend integration tests (89 passed)
backend\.venv\Scripts\python.exe -m pytest backend/tests/ -v

# Run all AI pipeline and model tests (47 passed)
backend\.venv\Scripts\python.exe -m pytest ai/tests/ -v

# Start FastAPI server on http://localhost:8000
cd backend
..\backend\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000
```
Interactive Swagger UI: `http://127.0.0.1:8000/docs`

### 2. Frontend Setup & Build
```powershell
cd frontend
npm install

# Verify TypeScript build
npm run build

# Start local development server on http://localhost:5173
npm run dev
```

---

## Ethical AI & Responsible Use

CrimeLens AI is built strictly as a **decision support tool for resource planning and spatial pattern analysis**.
- **No Individual Profiling:** The system explicitly prohibits and enforces programmatic checks against suspect profiling, demographic indexing, or individual criminality scoring.
- **Probabilistic Assistance:** All outputs are presented with transparent confidence intervals, explainability attribution scores (Captum), and prominent advisories that human verification is mandatory.

---

## License
MIT License
