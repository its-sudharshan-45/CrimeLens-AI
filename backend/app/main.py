from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    API_PREFIX,
    API_VERSION,
    APP_NAME,
    MSG_APP_RUNNING,
    MSG_DB_CONNECTED,
    MSG_HEALTH_OK,
)
from app.core.logger import logger
from app.db.session import AsyncSessionLocal, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    logger.info(f"Starting up {APP_NAME}...")
    try:
        from app.ai.model_service import ModelService
        ModelService.get_instance().load_models()
    except Exception as e:
        logger.warning(f"Could not load Phase 3/4 models in ModelService during startup: {e}")

    try:
        from app.ai.model_loader import ModelLoader
        ModelLoader.get_instance().load_all_models()
    except Exception as e:
        logger.warning(f"Could not load PyTorch models during startup: {e}")

    try:
        from app.services.mlops_service import MLOpsService

        mlops_service = MLOpsService()
        async with AsyncSessionLocal() as session:
            validation = await mlops_service.startup_validation(session)
        if not validation["ok"]:
            logger.warning(
                "Startup validation reported issues: %s",
                "; ".join(validation["errors"]),
            )
        else:
            logger.info("Startup validation completed successfully.")
    except Exception as e:
        logger.warning(f"Startup validation could not complete: {e}")

    yield
    logger.info(f"Shutting down {APP_NAME}...")


# Initialize FastAPI application (Step 6 & 9)
app = FastAPI(
    title=APP_NAME,
    description=(
        "CrimeLens AI Backend – Crime Pattern "
        "Prediction & Investigation Assistant"
    ),
    version=API_VERSION,
    openapi_url=f"{API_PREFIX}/openapi.json",
    docs_url="/docs",  # Automatically exposes Swagger UI
    redoc_url="/redoc",  # Automatically exposes ReDoc
    lifespan=lifespan
)

from app.core.config import settings
from app.core.security_middleware import SecurityHeadersAndObservabilityMiddleware

# Security Headers, Rate Limiting & Observability Middleware
app.add_middleware(SecurityHeadersAndObservabilityMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.v1 import auth, predictions, audit_logs, system_health, backup
from app.api.v1.api import api_router

app.include_router(auth.router, prefix=f"{API_PREFIX}/auth", tags=["Auth"])
app.include_router(predictions.router, prefix="/predict", tags=["Predictions & Forecasting"])
app.include_router(audit_logs.router, prefix="/admin/audit-logs", tags=["Audit Logs"])
app.include_router(system_health.router, prefix="/admin/system-health", tags=["System Health"])
app.include_router(backup.router, prefix="/admin/backup", tags=["Backup & Recovery"])
app.include_router(api_router, prefix=API_PREFIX)



@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint verifying the application is running.
    """
    return {"message": MSG_APP_RUNNING}


@app.get("/health", tags=["Health"])
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Production health check with dependency status, hardware resources, and AI models.
    """
    from app.mlops.deployment import DeploymentValidator, SystemMonitor
    from app.api.v1.system_health import get_system_metrics, get_ai_models_health

    validator = DeploymentValidator()
    registry_ok, _ = validator.validate_registry()
    models_ok, model_errors = validator.validate_models()
    db_ok, db_detail = await validator.validate_database(db)
    supabase_ok, supabase_detail = validator.validate_supabase()
    monitor = SystemMonitor()

    status_value = MSG_HEALTH_OK if registry_ok and models_ok and db_ok else "degraded"
    payload: dict[str, Any] = {
        "status": status_value,
        "database": {"ok": db_ok, "detail": db_detail},
        "supabase": {"ok": supabase_ok, "detail": supabase_detail},
        "registry": {"ok": registry_ok},
        "models": {"ok": models_ok, "errors": model_errors},
        "ai_models": get_ai_models_health(),
        "system": get_system_metrics(),
        "uptime_seconds": monitor.uptime_seconds(),
    }
    return payload


@app.get("/db", tags=["Health"])
async def db_health_check(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Step 8 - Database connectivity endpoint
    Executes a simple SELECT 1 to verify database connectivity via SQLAlchemy.
    """
    try:
        # Execute a simple query to verify connection
        await db.execute(text("SELECT 1"))
        return {"status": MSG_DB_CONNECTED}
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(
            status_code=500, detail="Database Connection Failed"
        ) from e
