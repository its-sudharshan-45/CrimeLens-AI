"""
backend/app/services/prediction_log.py
======================================
Shared helper for persisting prediction records and their audit-trail entries.
Used by the forecasting endpoint so that genuine prediction history is recorded.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums.prediction_type import PredictionType
from app.core.logger import logger
from app.models.audit_log import AuditLog
from app.models.prediction import Prediction


async def log_prediction(
    db: Optional[AsyncSession],
    *,
    action: str,
    prediction_type: PredictionType,
    label: str,
    model_name: str,
    model_version: str,
    confidence: float,
    execution_time_ms: int,
    raw_output: Dict[str, Any],
    audit_details: Dict[str, Any],
    user_id: Optional[uuid.UUID] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[uuid.UUID]:
    """Persist a prediction row and a matching audit-log entry. Never raises."""
    if db is None:
        return None
    try:
        pred = Prediction(
            prediction_label=label,
            prediction_type=prediction_type,
            confidence_score=confidence,
            model_name=model_name,
            model_version=model_version,
            execution_time_ms=execution_time_ms,
            raw_output=raw_output,
            user_id=user_id,
        )
        db.add(pred)
        await db.commit()
        await db.refresh(pred)

        db.add(
            AuditLog(
                action=action,
                entity_type="prediction",
                entity_id=pred.id,
                details={
                    **audit_details,
                    "confidence_score": confidence,
                    "execution_time_ms": execution_time_ms,
                    "status": "SUCCESS",
                },
                ip_address=client_ip,
                user_agent=user_agent,
                user_id=user_id,
            )
        )
        await db.commit()
        return pred.id
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to persist prediction/audit log: {exc}")
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None
