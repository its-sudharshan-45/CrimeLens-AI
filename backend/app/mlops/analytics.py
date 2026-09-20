"""
Prediction analytics computed from the predictions table.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction import Prediction

LOW_CONFIDENCE_THRESHOLD = 0.45


class PredictionAnalytics:
    """Build dashboard-ready aggregates from stored inference records."""

    @staticmethod
    def _active_predictions_filter():
        return Prediction.is_deleted.is_(False)

    async def build_dashboard(self, db: AsyncSession) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        thirty_days_ago = now - timedelta(days=30)
        twelve_months_ago = now - timedelta(days=365)

        active = self._active_predictions_filter()
        total = await self._scalar(
            db, select(func.count()).select_from(Prediction).where(active)
        )
        today = await self._scalar(
            db,
            select(func.count())
            .select_from(Prediction)
            .where(active, Prediction.prediction_time >= start_of_day),
        )
        month = await self._scalar(
            db,
            select(func.count())
            .select_from(Prediction)
            .where(active, Prediction.prediction_time >= start_of_month),
        )
        avg_confidence = await self._scalar(
            db,
            select(func.avg(Prediction.confidence_score))
            .select_from(Prediction)
            .where(active),
        )
        avg_latency = await self._scalar(
            db,
            select(func.avg(Prediction.execution_time_ms))
            .select_from(Prediction)
            .where(active),
        )

        domain_rows = await db.execute(
            select(Prediction.prediction_label, func.count())
            .where(active)
            .group_by(Prediction.prediction_label)
            .order_by(func.count().desc())
        )
        domain_counts = {row[0]: row[1] for row in domain_rows.all()}
        most_predicted_domain = next(iter(domain_counts), None)

        model_rows = await db.execute(
            select(
                Prediction.model_name,
                Prediction.model_version,
                func.count(),
                func.avg(Prediction.confidence_score),
            )
            .where(active)
            .group_by(Prediction.model_name, Prediction.model_version)
        )
        model_usage = [
            {
                "model_name": row[0],
                "model_version": row[1],
                "prediction_count": row[2],
                "average_confidence": round(float(row[3] or 0.0), 4),
            }
            for row in model_rows.all()
        ]

        low_confidence_count = await self._scalar(
            db,
            select(func.count())
            .select_from(Prediction)
            .where(active, Prediction.confidence_score < LOW_CONFIDENCE_THRESHOLD),
        )
        human_review_count = await self._scalar(
            db,
            select(func.count())
            .select_from(Prediction)
            .where(active, Prediction.explanation.isnot(None)),
        )

        top_confidence_rows = await db.execute(
            select(
                Prediction.id,
                Prediction.prediction_label,
                Prediction.confidence_score,
                Prediction.prediction_time,
            )
            .where(active)
            .order_by(Prediction.confidence_score.desc())
            .limit(10)
        )
        low_confidence_rows = await db.execute(
            select(
                Prediction.id,
                Prediction.prediction_label,
                Prediction.confidence_score,
                Prediction.prediction_time,
            )
            .where(active, Prediction.confidence_score < LOW_CONFIDENCE_THRESHOLD)
            .order_by(Prediction.confidence_score.asc())
            .limit(10)
        )

        daily_trend = await self._time_series(
            db,
            func.date_trunc("day", Prediction.prediction_time),
            thirty_days_ago,
        )
        monthly_trend = await self._time_series(
            db,
            func.date_trunc("month", Prediction.prediction_time),
            twelve_months_ago,
        )

        return {
            "summary": {
                "total_predictions": total or 0,
                "predictions_today": today or 0,
                "predictions_this_month": month or 0,
                "average_confidence": round(float(avg_confidence or 0.0), 4),
                "average_inference_latency_ms": round(float(avg_latency or 0.0), 2),
                "most_predicted_crime_domain": most_predicted_domain,
                "human_review_count": human_review_count or 0,
                "low_confidence_count": low_confidence_count or 0,
            },
            "prediction_distribution": domain_counts,
            "model_usage": model_usage,
            "top_confidence_predictions": [
                {
                    "prediction_id": str(row[0]),
                    "label": row[1],
                    "confidence": round(float(row[2]), 4),
                    "timestamp": row[3].isoformat() if row[3] else None,
                }
                for row in top_confidence_rows.all()
            ],
            "low_confidence_predictions": [
                {
                    "prediction_id": str(row[0]),
                    "label": row[1],
                    "confidence": round(float(row[2]), 4),
                    "timestamp": row[3].isoformat() if row[3] else None,
                }
                for row in low_confidence_rows.all()
            ],
            "daily_prediction_trend": daily_trend,
            "monthly_prediction_trend": monthly_trend,
            "charts": {
                "domain_pie": [
                    {"label": label, "value": count}
                    for label, count in domain_counts.items()
                ],
                "daily_line": daily_trend,
                "monthly_line": monthly_trend,
            },
        }

    async def _scalar(self, db: AsyncSession, stmt: Select[Any]) -> Optional[Any]:
        result = await db.execute(stmt)
        return result.scalar()

    async def _time_series(
        self,
        db: AsyncSession,
        bucket_expr: Any,
        since: datetime,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(bucket_expr.label("bucket"), func.count())
            .where(
                Prediction.is_deleted.is_(False),
                Prediction.prediction_time >= since,
            )
            .group_by("bucket")
            .order_by("bucket")
        )
        rows = await db.execute(stmt)
        series: list[dict[str, Any]] = []
        for bucket, count in rows.all():
            label = bucket.date().isoformat() if hasattr(bucket, "date") else str(bucket)
            series.append({"date": label, "count": int(count)})
        return series
