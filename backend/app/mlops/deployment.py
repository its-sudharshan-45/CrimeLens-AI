"""
Production deployment validation, health probes, and system monitoring.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.model_loader import ModelLoader, PROJECT_ROOT
from app.core.config import settings
from app.mlops.model_manager import ModelVersionManager

logger = logging.getLogger("crimelens.mlops")

_START_TIME = time.time()


@dataclass
class ValidationResult:
    ok: bool
    checks: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class DeploymentValidator:
    """Run startup checks for models, registry, database, and Supabase."""

    def __init__(self) -> None:
        self.model_manager = ModelVersionManager()

    def validate_registry(self) -> tuple[bool, str]:
        index_path = self.model_manager.registry_index_path
        active_path = self.model_manager.active_version_path
        if not os.path.isfile(index_path):
            return False, f"Registry index missing: {index_path}"
        if not os.path.isfile(active_path):
            return False, f"Active version file missing: {active_path}"
        return True, "ok"

    def validate_models(self) -> tuple[bool, list[str]]:
        ok, errors = self.model_manager.validate_model_artifacts(
            self.model_manager.default_models_dir
        )
        return ok, errors

    def validate_preprocessor_artifacts(self) -> tuple[bool, list[str]]:
        errors: list[str] = []
        models_dir = self.model_manager.default_models_dir
        prep = os.path.join(models_dir, "preprocessor.pkl")
        features = os.path.join(models_dir, "feature_columns.json")
        label_encoder_ok = False
        if not os.path.isfile(prep):
            errors.append("preprocessor.pkl missing")
        else:
            try:
                import joblib

                artifact = joblib.load(prep)
                label_encoder_ok = hasattr(artifact, "label_encoders") and bool(
                    artifact.label_encoders
                )
                if not label_encoder_ok:
                    errors.append("label encoder missing inside preprocessor")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"preprocessor load failed: {exc}")
        if not os.path.isfile(features):
            errors.append("feature_columns.json missing")
        return len(errors) == 0, errors

    async def validate_database(self, db: Optional[AsyncSession] = None) -> tuple[bool, str]:
        if not settings.DATABASE_URL:
            return False, "DATABASE_URL is not configured"
        if db is None:
            return True, "skipped (no session)"
        try:
            await db.execute(text("SELECT 1"))
            return True, "connected"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def validate_supabase(self) -> tuple[bool, str]:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            return False, "Supabase credentials not configured"
        try:
            from app.db.supabase import supabase_client

            _ = supabase_client
            return True, "client initialized"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    async def run_startup_validation(self, db: Optional[AsyncSession] = None) -> ValidationResult:
        result = ValidationResult(ok=True)
        registry_ok, registry_msg = self.validate_registry()
        result.checks["registry"] = {"ok": registry_ok, "detail": registry_msg}
        if not registry_ok:
            result.errors.append(registry_msg)
            result.ok = False

        models_ok, model_errors = self.validate_models()
        result.checks["models"] = {"ok": models_ok, "errors": model_errors}
        if not models_ok:
            result.errors.extend(model_errors)
            result.ok = False

        prep_ok, prep_errors = self.validate_preprocessor_artifacts()
        result.checks["preprocessor"] = {"ok": prep_ok, "errors": prep_errors}
        if not prep_ok:
            result.errors.extend(prep_errors)
            result.ok = False

        db_ok, db_msg = await self.validate_database(db)
        result.checks["database"] = {"ok": db_ok, "detail": db_msg}
        if not db_ok:
            result.errors.append(f"database: {db_msg}")
            result.ok = False

        supabase_ok, supabase_msg = self.validate_supabase()
        result.checks["supabase"] = {"ok": supabase_ok, "detail": supabase_msg}
        if not supabase_ok:
            result.errors.append(f"supabase: {supabase_msg}")
            result.ok = False

        loader = ModelLoader.get_instance()
        result.checks["model_loader"] = {
            "ok": loader.is_loaded,
            "models_dir": loader.models_dir,
            "feature_columns": len(loader.feature_columns),
        }
        if not loader.is_loaded:
            result.errors.append("ModelLoader did not finish loading models")
            result.ok = False

        if result.ok:
            logger.info("Startup validation passed.")
        else:
            logger.error("Startup validation failed: %s", "; ".join(result.errors))
        return result


class SystemMonitor:
    """Collect runtime health metrics for production monitoring endpoints."""

    @staticmethod
    def uptime_seconds() -> float:
        return round(time.time() - _START_TIME, 2)

    @staticmethod
    def memory_usage_mb() -> Optional[float]:
        try:
            import psutil

            process = psutil.Process(os.getpid())
            return round(process.memory_info().rss / (1024 * 1024), 2)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def cpu_usage_percent() -> Optional[float]:
        try:
            import psutil

            return round(psutil.cpu_percent(interval=0.1), 2)
        except Exception:  # noqa: BLE001
            return None

    async def system_status(self, db: Optional[AsyncSession] = None) -> dict[str, Any]:
        validator = DeploymentValidator()
        registry_ok, registry_msg = validator.validate_registry()
        models_ok, model_errors = validator.validate_models()
        db_ok, db_msg = await validator.validate_database(db)
        supabase_ok, supabase_msg = validator.validate_supabase()
        loader = ModelLoader.get_instance()

        return {
            "api_status": "ok",
            "database_status": "ok" if db_ok else "error",
            "database_detail": db_msg,
            "supabase_status": "ok" if supabase_ok else "error",
            "supabase_detail": supabase_msg,
            "model_status": "loaded" if loader.is_loaded else "not_loaded",
            "model_errors": model_errors,
            "registry_status": "ok" if registry_ok else "error",
            "registry_detail": registry_msg,
            "active_version": ModelVersionManager().get_current_model().get("version"),
            "memory_usage_mb": self.memory_usage_mb(),
            "cpu_usage_percent": self.cpu_usage_percent(),
            "uptime_seconds": self.uptime_seconds(),
            "project_root": PROJECT_ROOT,
        }
