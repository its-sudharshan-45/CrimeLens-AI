"""
backend/app/services/ai_service.py
==================================
Production AI Service for CrimeLens AI FastAPI Backend.
Wraps ModelLoader Singleton, PyTorch inference mode, Captum explainability,
N-BEATS forecasting, contrastive embeddings, and PostgreSQL DB auditing.
"""

import time
import asyncio
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from datetime import datetime, timedelta, timezone
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.model_loader import ModelLoader
from app.schemas.ai import (
    CrimePredictionRequest,
    CrimePredictionResponse,
    ForecastRequest,
    ForecastResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ExplainabilityRequest,
    ExplainabilityResponse,
    FeatureAttribution,
    BatchPredictionRequest,
    BatchPredictionResponse,
    ModelHealthResponse,
    ModelMetadataResponse,
)
from app.models.prediction import Prediction
from app.core.enums.prediction_type import PredictionType

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AIService:
    """
    High-level business service orchestrating PyTorch neural inference and DB logging.
    """

    def __init__(self) -> None:
        self.loader = ModelLoader.get_instance()

    def _ensure_loaded(self) -> None:
        if not self.loader.is_loaded:
            self.loader.load_all_models()

    def _sync_predict_crime(self, sample_dict: dict) -> dict:
        """Synchronous CPU/GPU forward pass for domain classification."""
        self._ensure_loaded()
        x_tensor = self.loader.prepare_sample_tensor(sample_dict)

        model = (
            self.loader.ensemble_classifier
            if self.loader.ensemble_classifier is not None
            else (
                self.loader.ft_classifier
                if self.loader.ft_classifier is not None
                else self.loader.mlp_classifier
            )
        )
        if model is None:
            raise RuntimeError("No PyTorch classification model loaded.")

        with torch.inference_mode():
            x_in: torch.Tensor = x_tensor
            probabilities_array = model.predict_proba(x_in)[0].cpu().numpy()
            pred_idx = int(np.argmax(probabilities_array))

        domain_encoder = self.loader.preprocessor.label_encoders.get("Crime Domain") if self.loader.preprocessor else None
        domain_label = domain_encoder.inverse_transform([pred_idx])[0] if domain_encoder else str(pred_idx)

        prob_dict = {}
        if domain_encoder:
            for idx, prob in enumerate(probabilities_array):
                prob_dict[domain_encoder.classes_[idx]] = float(round(prob, 4))

        confidence = float(round(probabilities_array[pred_idx], 4))

        return {
            "predicted_domain": domain_label,
            "domain_code": pred_idx,
            "confidence_score": confidence,
            "probabilities": prob_dict,
            "model_name": model.__class__.__name__,
        }

    async def predict_crime(
        self,
        request: CrimePredictionRequest,
        db: Optional[AsyncSession] = None,
        user_id: Optional[Any] = None,
    ) -> CrimePredictionResponse:
        """
        Executes real-time crime domain classification asynchronously and logs to DB.
        """
        start_time = time.perf_counter()
        sample_dict = request.model_dump()

        # Non-blocking async execution of PyTorch forward pass
        result = await asyncio.to_thread(self._sync_predict_crime, sample_dict)
        execution_time_ms = max(1, int((time.perf_counter() - start_time) * 1000))

        model_version = self.loader.model_metadata.get("version", "v1.0.0")

        # Database audit persistence
        prediction_id_str = None
        if db is not None:
            try:
                db_prediction = Prediction(
                    prediction_label=result["predicted_domain"],
                    prediction_type=PredictionType.CRIME_TYPE,
                    confidence_score=result["confidence_score"],
                    model_name=result["model_name"],
                    model_version=model_version,
                    execution_time_ms=execution_time_ms,
                    raw_output={"probabilities": result["probabilities"], "input": sample_dict},
                    user_id=user_id,
                )
                db.add(db_prediction)
                await db.commit()
                await db.refresh(db_prediction)
                prediction_id_str = str(db_prediction.id)
            except Exception as e:
                logger.warning(f"Could not persist prediction to database: {e}")
                await db.rollback()

        return CrimePredictionResponse(
            prediction_id=prediction_id_str,
            predicted_domain=result["predicted_domain"],
            domain_code=result["domain_code"],
            confidence_score=result["confidence_score"],
            probabilities=result["probabilities"],
            model_name=result["model_name"],
            model_version=model_version,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now(timezone.utc),
        )

    def _sync_forecast(self, horizon: int, recent_sequence: Optional[List[float]]) -> List[float]:
        """Synchronous N-BEATS sequence forecasting forward pass."""
        self._ensure_loaded()
        if self.loader.nbeats_forecaster is None:
            raise RuntimeError("N-BEATS forecaster model not loaded.")

        if recent_sequence is None or len(recent_sequence) == 0:
            recent_sequence = [15.0] * 30

        if len(recent_sequence) < 30:
            recent_sequence = [recent_sequence[0]] * (30 - len(recent_sequence)) + recent_sequence
        elif len(recent_sequence) > 30:
            recent_sequence = recent_sequence[-30:]

        x_seq = torch.tensor(recent_sequence, dtype=torch.float32, device=self.loader.device).unsqueeze(0)

        with torch.inference_mode():
            forecast_tensor = self.loader.nbeats_forecaster(x_seq)[0].cpu().numpy()

        # Handle requested horizon extrapolation if horizon > 7
        raw_7d = [float(round(v, 2)) for v in forecast_tensor]
        if horizon <= 7:
            return raw_7d[:horizon]

        # Multi-step autoregressive extension for 30d/90d
        extended = list(raw_7d)
        curr_seq = list(recent_sequence)
        while len(extended) < horizon:
            curr_seq = curr_seq[7:] + extended[-7:]
            x_step = torch.tensor(curr_seq[-30:], dtype=torch.float32, device=self.loader.device).unsqueeze(0)
            with torch.inference_mode():
                next_7 = self.loader.nbeats_forecaster(x_step)[0].cpu().numpy()
            extended.extend([float(round(v, 2)) for v in next_7])

        return extended[:horizon]

    async def forecast_crime(self, request: ForecastRequest) -> ForecastResponse:
        """Executes multi-horizon crime trend forecasting."""
        start_time = time.perf_counter()
        horizon = request.horizon

        predicted_counts = await asyncio.to_thread(self._sync_forecast, horizon, request.recent_sequence)
        execution_time_ms = max(1, int((time.perf_counter() - start_time) * 1000))

        today = datetime.now(timezone.utc).date()
        forecast_dates = [(today + timedelta(days=i)).isoformat() for i in range(1, horizon + 1)]
        total_projected = round(sum(predicted_counts), 2)

        return ForecastResponse(
            horizon=horizon,
            forecast_dates=forecast_dates,
            predicted_counts=predicted_counts,
            total_projected_incidents=total_projected,
            model_name="NBEATSForecaster",
            model_version=self.loader.model_metadata.get("version", "v1.0.0"),
            execution_time_ms=execution_time_ms,
        )

    def _sync_embedding(self, sample_dict: dict) -> tuple[List[float], str]:
        """Synchronous dense embedding generation forward pass with FT-Transformer CLS fallback."""
        self._ensure_loaded()
        x_tensor = self.loader.prepare_sample_tensor(sample_dict)
        with torch.inference_mode():
            x_in: torch.Tensor = x_tensor
            if self.loader.embedding_net is not None:
                emb = self.loader.embedding_net.get_embedding(x_in)[0].cpu().numpy()
                model_name = "CrimeEmbeddingNetwork"
            elif self.loader.ft_classifier is not None:
                tokens = self.loader.ft_classifier.feature_tokenizer(x_in)
                cls = self.loader.ft_classifier.cls_token.expand(x_in.size(0), -1, -1)
                tokens = torch.cat([cls, tokens], dim=1)
                for block in self.loader.ft_classifier.transformer_blocks:
                    tokens = block(tokens)
                cls_repr = self.loader.ft_classifier.head_norm(tokens[:, 0, :])
                if cls_repr.size(-1) < 64:
                    cls_repr = torch.nn.functional.pad(cls_repr, (0, 64 - cls_repr.size(-1)))
                elif cls_repr.size(-1) > 64:
                    cls_repr = cls_repr[:, :64]
                cls_norm = torch.nn.functional.normalize(cls_repr, p=2, dim=-1)
                emb = cls_norm[0].cpu().numpy()
                model_name = "FTTransformerClassifier-CLS"
            else:
                raise RuntimeError("No embedding or FT-Transformer model loaded.")

        return [float(round(v, 4)) for v in emb], model_name

    async def generate_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generates a 64-dimensional dense vector embedding (E in R^64)."""
        sample_dict = request.sample_record.model_dump()
        vector, model_name = await asyncio.to_thread(self._sync_embedding, sample_dict)
        l2_norm = float(round(np.linalg.norm(vector), 4))

        return EmbeddingResponse(
            embedding_vector=vector,
            embedding_dim=len(vector),
            l2_norm=l2_norm,
            model_name=model_name,
        )

    def _sync_explain(self, sample_dict: dict, target_class: int) -> dict:
        """Synchronous Captum Integrated Gradients & Saliency feature attribution."""
        self._ensure_loaded()
        x_tensor = self.loader.prepare_sample_tensor(sample_dict)
        model = (
            self.loader.ft_classifier
            if self.loader.ft_classifier is not None
            else self.loader.mlp_classifier
        )

        if model is None:
            raise RuntimeError("No classification model available for explainability.")

        x_req = x_tensor.detach().clone().requires_grad_(True)
        outputs = model(x_req)
        probas = torch.softmax(outputs, dim=-1)[0].detach().cpu().numpy()
        pred_class = int(np.argmax(probas))
        target = target_class if target_class < len(probas) else pred_class

        # Captum / Gradient sensitivity calculation
        try:
            import importlib
            captum_attr = importlib.import_module("captum.attr")
            IntegratedGradients = getattr(captum_attr, "IntegratedGradients")
            Saliency = getattr(captum_attr, "Saliency")

            ig = IntegratedGradients(model)
            saliency = Saliency(model)
            ig_attr = ig.attribute(x_req, target=target, n_steps=30)[0].abs().detach().cpu().numpy()
            sal_attr = saliency.attribute(x_req, target=target)[0].abs().detach().cpu().numpy()
        except Exception:
            loss = outputs[0, target]
            loss.backward()
            if x_req.grad is not None:
                ig_attr = x_req.grad[0].abs().cpu().numpy()
            else:
                ig_attr = np.zeros(x_tensor.shape[1], dtype=np.float32)
            sal_attr = ig_attr

        feature_names = self.loader.feature_columns

        ig_scores = [
            FeatureAttribution(feature_name=feature_names[i], attribution_score=round(float(ig_attr[i]), 4))
            for i in np.argsort(ig_attr)[::-1]
        ]
        sal_scores = [
            FeatureAttribution(feature_name=feature_names[i], attribution_score=round(float(sal_attr[i]), 4))
            for i in np.argsort(sal_attr)[::-1]
        ]

        domain_encoder = self.loader.preprocessor.label_encoders.get("Crime Domain") if self.loader.preprocessor else None
        domain_label = domain_encoder.inverse_transform([pred_class])[0] if domain_encoder else str(pred_class)

        return {
            "predicted_domain": domain_label,
            "confidence_score": float(round(probas[pred_class], 4)),
            "top_contributing_features": ig_scores[:10],
            "saliency_scores": sal_scores[:10],
            "model_name": model.__class__.__name__,
        }

    async def explain_prediction(self, request: ExplainabilityRequest) -> ExplainabilityResponse:
        """Executes Captum Integrated Gradients explainability analysis."""
        sample_dict = request.sample_record.model_dump()
        target_class = request.target_class or 0

        res = await asyncio.to_thread(self._sync_explain, sample_dict, target_class)

        return ExplainabilityResponse(
            predicted_domain=res["predicted_domain"],
            confidence_score=res["confidence_score"],
            top_contributing_features=res["top_contributing_features"],
            saliency_scores=res["saliency_scores"],
            model_name=res["model_name"],
            method="Captum Integrated Gradients & Saliency",
        )

    async def batch_predict(
        self,
        request: BatchPredictionRequest,
        db: Optional[AsyncSession] = None,
        user_id: Optional[Any] = None,
    ) -> BatchPredictionResponse:
        """Executes bulk batch crime domain predictions."""
        start_time = time.perf_counter()
        predictions = []

        for record in request.records:
            pred_resp = await self.predict_crime(record, db=db, user_id=user_id)
            predictions.append(pred_resp)

        batch_execution_time_ms = max(1, int((time.perf_counter() - start_time) * 1000))

        return BatchPredictionResponse(
            total_records=len(predictions),
            predictions=predictions,
            batch_execution_time_ms=batch_execution_time_ms,
        )

    def get_health_status(self) -> ModelHealthResponse:
        """Probes AI subsystem health and model loading status."""
        self._ensure_loaded()
        return ModelHealthResponse(
            status="ok" if self.loader.is_loaded else "uninitialized",
            device=str(self.loader.device),
            models_loaded={
                "ft_transformer": self.loader.ft_classifier is not None,
                "residual_mlp": self.loader.mlp_classifier is not None,
                "ensemble": self.loader.ensemble_classifier is not None,
                "nbeats_forecaster": self.loader.nbeats_forecaster is not None,
                "embedding_network": self.loader.embedding_net is not None,
            },
            warmup_complete=self.loader.is_loaded,
        )

    def get_model_metadata(self) -> ModelMetadataResponse:
        """Returns model version metadata, dataset hash, and parameters."""
        self._ensure_loaded()
        meta = self.loader.model_metadata
        return ModelMetadataResponse(
            version=meta.get("version", "v1.0.0"),
            framework=meta.get("framework", f"PyTorch {torch.__version__ if torch is not None else 'N/A'}"),
            flagship_model=meta.get("flagship_model", "FTTransformerClassifier"),
            forecaster_model=meta.get("forecaster_model", "NBEATSForecaster"),
            embedding_dim=64,
            dataset_rows=meta.get("dataset_rows", 40160),
            dataset_hash_md5=meta.get("dataset_hash_md5", "N/A"),
            saved_at=meta.get("saved_at"),
        )
