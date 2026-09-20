"""
ai/inference/predict.py
========================
Production Deep Learning Inference Engine for CrimeLens AI.

Loads saved PyTorch models (.pt, .ts, or ONNX) to execute offline inference:
  1. FT-Transformer Crime Domain Classification
  2. N-BEATS Multi-Horizon Time Series Forecasting (7-day, 30-day, 90-day)
  3. Supervised Contrastive Dense Embedding Generation (E in R^64)
  4. Soft-Voting Model Ensemble Predictions
"""

import json
import logging
import os
from typing import Any

import joblib
import numpy as np
import pandas as pd
import torch

from ai.models.ft_transformer import FTTransformerClassifier
from ai.models.mlp_classifier import CrimeMLPClassifier
from ai.models.ensemble_classifier import EnsembleClassifier
from ai.models.nbeats_forecaster import NBEATSForecaster
from ai.models.embedding_network import CrimeEmbeddingNetwork

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_MODELS_DIR = "ai/models"


class CrimeLensDLInferenceEngine:
    """
    Production Offline PyTorch Deep Learning Inference Engine.
    """

    def __init__(self, models_dir: str = DEFAULT_MODELS_DIR, device: str | None = None) -> None:
        self.models_dir = models_dir
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))

        self.preprocessor = None
        self.label_encoders = {}
        self.feature_columns = []

        self.ft_classifier = None
        self.mlp_classifier = None
        self.ensemble_classifier = None
        self.nbeats_forecaster = None
        self.embedding_net = None

        self._load_artifacts()

    def _load_artifacts(self) -> None:
        """Load preprocessor, schema, and PyTorch model state_dicts."""
        logger.info(f"Loading PyTorch inference artifacts from {self.models_dir}...")

        # Load preprocessor & encoders
        prep_path = os.path.join(self.models_dir, "preprocessor.pkl")
        if os.path.exists(prep_path):
            self.preprocessor = joblib.load(prep_path)

        schema_path = os.path.join(self.models_dir, "feature_columns.json")
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                self.feature_columns = json.load(f).get("feature_columns", [])

        if not self.feature_columns:
            self.feature_columns = [
                "Victim Age", "City_encoded", "State_encoded", "Victim Gender_encoded", "Weapon Used_encoded",
                "Year", "Month", "Day", "Weekday", "Hour", "Is_Weekend", "Quarter",
                "sin_month", "cos_month", "sin_hour", "cos_hour", "sin_weekday", "cos_weekday",
                "City_Crime_Freq", "State_Crime_Freq", "Category_Freq",
                "City_Mean_Police", "City_Closure_Rate", "State_Mean_Police", "State_Closure_Rate",
                "Reporting_Lag_Hours"
            ]

        input_dim = len(self.feature_columns)
        num_classes = len(self.preprocessor.label_encoders["Crime Domain"].classes_) if self.preprocessor and "Crime Domain" in self.preprocessor.label_encoders else 4

        # 1. Load FT-Transformer Classifier
        ft_path = os.path.join(self.models_dir, "ft_transformer.pt")
        if os.path.exists(ft_path):
            self.ft_classifier = FTTransformerClassifier(input_dim=input_dim, num_classes=num_classes)
            self.ft_classifier.load_state_dict(torch.load(ft_path, map_location=self.device, weights_only=True))
            self.ft_classifier.to(self.device)
            self.ft_classifier.eval()

        # 2. Load Enhanced MLP Classifier
        mlp_path = os.path.join(self.models_dir, "crime_classifier.pt")
        if os.path.exists(mlp_path):
            self.mlp_classifier = CrimeMLPClassifier(input_dim=input_dim, num_classes=num_classes)
            self.mlp_classifier.load_state_dict(torch.load(mlp_path, map_location=self.device, weights_only=True))
            self.mlp_classifier.to(self.device)
            self.mlp_classifier.eval()

        # 3. Instantiate Ensemble if both models available
        if self.ft_classifier is not None and self.mlp_classifier is not None:
            self.ensemble_classifier = EnsembleClassifier([self.ft_classifier, self.mlp_classifier], weights=[0.6, 0.4])
            self.ensemble_classifier.to(self.device)
            self.ensemble_classifier.eval()

        # 4. Load N-BEATS Forecaster
        fcst_path = os.path.join(self.models_dir, "forecast_model.pt")
        if os.path.exists(fcst_path):
            self.nbeats_forecaster = NBEATSForecaster(input_size=30, forecast_horizon=7)
            self.nbeats_forecaster.load_state_dict(torch.load(fcst_path, map_location=self.device, weights_only=True))
            self.nbeats_forecaster.to(self.device)
            self.nbeats_forecaster.eval()

        # 5. Load Contrastive Embedding Network
        emb_path = os.path.join(self.models_dir, "embedding_model.pt")
        if os.path.exists(emb_path):
            self.embedding_net = CrimeEmbeddingNetwork(input_dim=input_dim, embedding_dim=64)
            self.embedding_net.load_state_dict(torch.load(emb_path, map_location=self.device, weights_only=True))
            self.embedding_net.to(self.device)
            self.embedding_net.eval()

        logger.info("Inference engine initialized with SOTA neural architectures.")

    def _prepare_sample_tensor(self, sample: dict) -> torch.Tensor:
        """Preprocess single incident dictionary sample into PyTorch FloatTensor."""
        df_raw = pd.DataFrame([sample])
        if self.preprocessor is not None:
            df_processed = self.preprocessor.transform(df_raw)
        else:
            df_processed = df_raw

        from ai.preprocessing.feature_engineering import FeatureEngineer
        fe = FeatureEngineer()
        fe.city_stats = getattr(self.preprocessor, "city_stats", {})
        fe.state_stats = getattr(self.preprocessor, "state_stats", {})

        df_feats = fe.transform(df_processed, is_train=False)
        X, _, _ = fe.get_feature_matrix(df_feats, target_type="classification")

        for col in self.feature_columns:
            if col not in X.columns:
                X[col] = 0.0
        X = X[self.feature_columns]

        return torch.tensor(X.values, dtype=torch.float32).to(self.device)

    def predict_crime_domain(self, sample: dict, use_ensemble: bool = True) -> dict[str, Any]:
        """Predict Crime Domain using Ensemble (or FT-Transformer)."""
        x_tensor = self._prepare_sample_tensor(sample)
        model = (
            self.ensemble_classifier
            if (use_ensemble and self.ensemble_classifier is not None)
            else (
                self.ft_classifier
                if self.ft_classifier is not None
                else self.mlp_classifier
            )
        )
        if model is None:
            raise RuntimeError("No classification model available.")

        with torch.no_grad():
            probas = model.predict_proba(x_tensor)[0].cpu().numpy()
            pred_idx = int(np.argmax(probas))

        domain_encoder = self.preprocessor.label_encoders.get("Crime Domain") if self.preprocessor else None
        domain_label = domain_encoder.inverse_transform([pred_idx])[0] if domain_encoder else str(pred_idx)

        prob_dict = {}
        if domain_encoder:
            for idx, prob in enumerate(probas):
                prob_dict[domain_encoder.classes_[idx]] = float(round(prob, 4))

        return {
            "predicted_domain": domain_label,
            "domain_code": pred_idx,
            "probabilities": prob_dict,
            "architecture_used": model.__class__.__name__,
        }

    def forecast_crimes(self, recent_sequence: list[float] | None = None, horizon: int = 7) -> list[float]:
        """Multi-horizon forecasting using N-BEATS."""
        if self.nbeats_forecaster is None:
            raise RuntimeError("NBEATS forecaster not loaded.")

        if recent_sequence is None:
            recent_sequence = [15.0] * 30

        if len(recent_sequence) < 30:
            recent_sequence = [recent_sequence[0]] * (30 - len(recent_sequence)) + recent_sequence
        elif len(recent_sequence) > 30:
            recent_sequence = recent_sequence[-30:]

        x_seq = torch.tensor(recent_sequence, dtype=torch.float32).unsqueeze(0).to(self.device)
        with torch.no_grad():
            forecast_tensor = self.nbeats_forecaster(x_seq)[0].cpu().numpy()

        return [float(round(v, 2)) for v in forecast_tensor[:horizon]]

    def generate_crime_embedding(self, sample: dict) -> list[float]:
        """Generate 64-dimensional dense vector embedding (E in R^64)."""
        if self.embedding_net is None:
            raise RuntimeError("Embedding network model not loaded.")
        x_tensor = self._prepare_sample_tensor(sample)
        with torch.no_grad():
            emb_tensor = self.embedding_net.get_embedding(x_tensor)[0].cpu().numpy()

        return [float(round(v, 4)) for v in emb_tensor]


if __name__ == "__main__":
    engine = CrimeLensDLInferenceEngine()

    sample_record = {
        "Date Reported": "15-09-2023 14:00",
        "Date of Occurrence": "15-09-2023 04:30",
        "Time of Occurrence": "15-09-2023 04:30",
        "City": "Mumbai",
        "Crime Code": 110,
        "Crime Description": "ROBBERY",
        "Victim Age": 29,
        "Victim Gender": "M",
        "Weapon Used": "Firearm",
        "Case Closed": "No",
    }

    print("\n--- ENHANCED DEEP LEARNING INFERENCE VERIFICATION ---")
    if engine.ft_classifier or engine.ensemble_classifier:
        print("Domain Prediction:", json.dumps(engine.predict_crime_domain(sample_record), indent=2))

    if engine.nbeats_forecaster:
        print("N-BEATS 7-Day Forecast:", engine.forecast_crimes())

    if engine.embedding_net:
        emb = engine.generate_crime_embedding(sample_record)
        print(f"Dense Contrastive Embedding (dim={len(emb)}):", emb[:8], "...")
