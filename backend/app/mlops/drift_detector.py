"""
Data and model drift detection using PSI and Jensen-Shannon divergence.
"""

from __future__ import annotations

import json
import logging
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Literal

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.model_loader import DEFAULT_MODELS_DIR, PROJECT_ROOT
from app.models.prediction import Prediction

logger = logging.getLogger("crimelens.mlops")

DriftLevel = Literal["LOW", "MEDIUM", "HIGH"]

TRAINING_STATS_PATH = os.path.join(DEFAULT_MODELS_DIR, "training_statistics.json")

PSI_LOW = 0.1
PSI_MEDIUM = 0.25
JS_LOW = 0.05
JS_MEDIUM = 0.15


def _psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    eps = 1e-6
    expected_pct = np.histogram(expected, bins=buckets, range=(0.0, 1.0))[0].astype(float)
    actual_pct = np.histogram(actual, bins=buckets, range=(0.0, 1.0))[0].astype(float)
    expected_pct = expected_pct / max(expected_pct.sum(), eps)
    actual_pct = actual_pct / max(actual_pct.sum(), eps)
    return float(np.sum((actual_pct - expected_pct) * np.log((actual_pct + eps) / (expected_pct + eps))))


def _js_divergence(p: dict[str, float], q: dict[str, float]) -> float:
    keys = set(p.keys()) | set(q.keys())
    eps = 1e-9
    p_vec = np.array([p.get(k, 0.0) for k in keys], dtype=float)
    q_vec = np.array([q.get(k, 0.0) for k in keys], dtype=float)
    p_vec = p_vec / max(p_vec.sum(), eps)
    q_vec = q_vec / max(q_vec.sum(), eps)
    m_vec = 0.5 * (p_vec + q_vec)
    kl_pm = np.sum(p_vec * np.log((p_vec + eps) / (m_vec + eps)))
    kl_qm = np.sum(q_vec * np.log((q_vec + eps) / (m_vec + eps)))
    return float(0.5 * (kl_pm + kl_qm))


def _level_from_score(score: float, low: float, medium: float) -> DriftLevel:
    if score >= medium:
        return "HIGH"
    if score >= low:
        return "MEDIUM"
    return "LOW"


class DriftDetector:
    """Compare live prediction traffic against training reference statistics."""

    def __init__(self, training_stats_path: str = TRAINING_STATS_PATH) -> None:
        self.training_stats_path = training_stats_path
        self._baseline = self._load_baseline()

    def _load_baseline(self) -> dict[str, Any]:
        path = self.training_stats_path
        if not os.path.isfile(path):
            alt = os.path.join(PROJECT_ROOT, "ai", "registry", "v1.0.0", "training_statistics.json")
            path = alt if os.path.isfile(alt) else path
        if not os.path.isfile(path):
            logger.warning("Training statistics file not found at %s", self.training_stats_path)
            return {}
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    async def _recent_predictions(self, db: AsyncSession, limit: int = 500) -> list[Prediction]:
        stmt = (
            select(Prediction)
            .order_by(Prediction.prediction_time.desc())
            .limit(limit)
        )
        try:
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load predictions for drift analysis: %s", exc)
            return []

    def _extract_numerical_samples(
        self, predictions: list[Prediction], field: str
    ) -> list[float]:
        key_map = {
            "Victim Age": ("victim_age", "Victim Age"),
            "Crime Code": ("crime_code", "Crime Code"),
        }
        keys = key_map.get(field, (field.lower().replace(" ", "_"), field))
        values: list[float] = []
        for pred in predictions:
            payload = pred.raw_output.get("input", {}) if pred.raw_output else {}
            for key in keys:
                if key in payload and payload[key] is not None:
                    try:
                        values.append(float(payload[key]))
                    except (TypeError, ValueError):
                        continue
                    break
        return values

    def _label_distribution(self, predictions: list[Prediction]) -> dict[str, float]:
        if not predictions:
            return {}
        counter = Counter(p.prediction_label for p in predictions)
        total = sum(counter.values())
        return {label: count / total for label, count in counter.items()}

    def _confidence_drift(self, predictions: list[Prediction]) -> tuple[float, DriftLevel]:
        baseline = self._baseline.get("confidence_baseline", {})
        if not predictions or not baseline:
            return 0.0, "LOW"
        scores = np.array([p.confidence_score for p in predictions], dtype=float)
        ref_mean = float(baseline.get("mean", scores.mean()))
        ref_std = max(float(baseline.get("std", 1.0)), 1e-6)
        live_mean = float(scores.mean())
        z_shift = abs(live_mean - ref_mean) / ref_std
        ref_samples = np.clip(
            ref_mean + ref_std * np.linspace(-2.0, 2.0, num=len(scores)),
            0.0,
            1.0,
        )
        psi = _psi(np.clip(scores, 0.0, 1.0), ref_samples)
        score = max(z_shift / 3.0, psi)
        return score, _level_from_score(score, PSI_LOW, PSI_MEDIUM)

    def _feature_drift(self, predictions: list[Prediction]) -> tuple[float, DriftLevel, list[str]]:
        numerical = self._baseline.get("numerical_features", {})
        if not numerical or not predictions:
            return 0.0, "LOW", []

        affected: list[str] = []
        max_score = 0.0
        for feature, stats in numerical.items():
            samples = self._extract_numerical_samples(predictions, feature)
            if len(samples) < 5:
                continue
            arr = np.array(samples, dtype=float)
            ref_mean = float(stats.get("mean", arr.mean()))
            ref_std = max(float(stats.get("std", 1.0)), 1e-6)
            z = abs(float(arr.mean()) - ref_mean) / ref_std
            if z > 0.5:
                affected.append(feature)
            max_score = max(max_score, z / 3.0)

        level = _level_from_score(max_score, PSI_LOW, PSI_MEDIUM)
        return max_score, level, affected

    def _prediction_distribution_drift(
        self, predictions: list[Prediction]
    ) -> tuple[float, DriftLevel]:
        baseline = self._baseline.get("category_frequencies", {}).get("Crime Domain", {})
        live = self._label_distribution(predictions)
        if not baseline or not live:
            return 0.0, "LOW"
        score = _js_divergence(baseline, live)
        return score, _level_from_score(score, JS_LOW, JS_MEDIUM)

    async def evaluate(self, db: AsyncSession) -> dict[str, Any]:
        predictions = await self._recent_predictions(db)
        feature_score, feature_level, affected = self._feature_drift(predictions)
        conf_score, conf_level = self._confidence_drift(predictions)
        dist_score, dist_level = self._prediction_distribution_drift(predictions)

        levels = [feature_level, conf_level, dist_level]
        overall_level: DriftLevel = "HIGH" if "HIGH" in levels else "MEDIUM" if "MEDIUM" in levels else "LOW"
        drift_score = round(max(feature_score, conf_score, dist_score), 4)

        warnings: list[str] = []
        if feature_level != "LOW":
            warnings.append(f"Feature drift detected ({feature_level}) on: {', '.join(affected) or 'numerical inputs'}")
        if conf_level != "LOW":
            warnings.append(f"Confidence drift detected ({conf_level}).")
        if dist_level != "LOW":
            warnings.append(f"Prediction distribution drift detected ({dist_level}).")

        return {
            "drift_score": drift_score,
            "overall_level": overall_level,
            "feature_drift": {
                "score": round(feature_score, 4),
                "level": feature_level,
                "affected_features": affected,
            },
            "confidence_drift": {"score": round(conf_score, 4), "level": conf_level},
            "prediction_distribution_drift": {
                "score": round(dist_score, 4),
                "level": dist_level,
            },
            "sample_size": len(predictions),
            "warnings": warnings,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def report(self, db: AsyncSession) -> dict[str, Any]:
        evaluation = await self.evaluate(db)
        recommendation = "Continue monitoring; drift levels are within acceptable bounds."
        if evaluation["overall_level"] == "MEDIUM":
            recommendation = (
                "Schedule model performance review and validate recent data quality."
            )
        elif evaluation["overall_level"] == "HIGH":
            recommendation = (
                "Consider retraining or rolling back to a prior model version after data audit."
            )

        drift_types = []
        if evaluation["feature_drift"]["level"] != "LOW":
            drift_types.append("Feature Drift")
        if evaluation["confidence_drift"]["level"] != "LOW":
            drift_types.append("Confidence Drift")
        if evaluation["prediction_distribution_drift"]["level"] != "LOW":
            drift_types.append("Prediction Distribution Drift")

        return {
            "drift_score": evaluation["drift_score"],
            "drift_level": evaluation["overall_level"],
            "drift_type": drift_types or ["None"],
            "affected_features": evaluation["feature_drift"]["affected_features"],
            "recommendation": recommendation,
            "warnings": evaluation["warnings"],
            "timestamp": evaluation["timestamp"],
            "details": evaluation,
        }
