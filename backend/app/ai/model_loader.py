"""
backend/app/ai/model_loader.py
==============================
Singleton PyTorch Model Loading & Warmup Service for CrimeLens AI FastAPI Backend.

Responsibilities:
  - Thread-safe Singleton model loading at FastAPI startup lifespan
  - Loads PyTorch models from ai/registry/v1.0.0 (FTTransformer, MLP, Ensemble, N-BEATS, Embedding)
  - Loads preprocessing artifacts: preprocessor.pkl, feature_columns.json
  - Automatic model warm-up via dummy forward passes
  - Device selection (CPU/GPU) with torch.inference_mode()

Fix (Phase 7):
  - Corrected checkpoint loading from raw-dict checkpoint.pt to proper state_dict loading.
  - Models are now instantiated from their class definitions and loaded via load_state_dict(),
    following the same verified pattern used in ai/inference/predict.py.
  - Embedding network (CrimeEmbeddingNetwork) is now loaded from registry/v1.0.0/embedding_model.pt.
"""

import os
import sys
import json
import importlib.util
import joblib
import logging
import threading
from typing import Dict, Any, Optional, List

import pandas as pd
import numpy as np

# Ensure project root is in sys.path so ai package imports resolve
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import torch
import torch.nn.functional as F
TORCH_AVAILABLE = True

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Registry paths — single source of truth
REGISTRY_DIR = os.path.join(PROJECT_ROOT, "ai", "registry", "v1.0.0")
DEFAULT_MODELS_DIR = os.path.join(PROJECT_ROOT, "ai", "models")


def _load_class_from_file(file_path: str, class_name: str) -> Any:
    """Dynamically load a class from an arbitrary .py file (avoids dotted-package issues with v1.0.0)."""
    spec = importlib.util.spec_from_file_location(class_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module spec for {file_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, class_name)


class ModelLoader:
    """
    Singleton class managing loaded PyTorch neural networks and preprocessing artifacts.

    All production model weights are loaded from ai/registry/v1.0.0/, which contains
    verified, version-pinned checkpoints. The loading pattern mirrors ai/inference/predict.py.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, models_dir: str = DEFAULT_MODELS_DIR) -> None:
        if ModelLoader._instance is not None:
            raise RuntimeError("ModelLoader is a Singleton. Use ModelLoader.get_instance() instead.")

        self.models_dir = models_dir
        self.registry_dir = REGISTRY_DIR
        self.device = (
            torch.device("cuda" if torch.cuda.is_available() else "cpu")
            if (TORCH_AVAILABLE and torch is not None and hasattr(torch, "cuda"))
            else "cpu"
        )
        self.is_loaded = False

        self.preprocessor = None
        self.feature_columns: List[str] = []
        self.training_config: Dict[str, Any] = {}
        self.model_metadata: Dict[str, Any] = {}

        # Model references — all populated during load_all_models()
        self.ft_classifier: Optional[Any] = None      # FTTransformerClassifier
        self.mlp_classifier: Optional[Any] = None     # CrimeMLPClassifier
        self.ensemble_classifier: Optional[Any] = None  # EnsembleClassifier
        self.nbeats_forecaster: Optional[Any] = None  # NBEATSForecaster
        self.embedding_net: Optional[Any] = None      # CrimeEmbeddingNetwork

    @classmethod
    def get_instance(cls, models_dir: str = DEFAULT_MODELS_DIR) -> "ModelLoader":
        """Thread-safe Singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(models_dir=models_dir)
        return cls._instance

    def load_all_models(self) -> bool:
        """
        Loads all PyTorch models and preprocessing artifacts.

        Uses ai/registry/v1.0.0/ for all model class definitions and checkpoints.
        Each model is properly instantiated from its class and loaded via load_state_dict()
        rather than torch.load() on a raw checkpoint dict.
        """
        with self._lock:
            if self.is_loaded:
                return True

            if not TORCH_AVAILABLE or torch is None:
                logger.warning("ModelLoader: PyTorch unavailable. Neural model loading skipped.")
                return False

            logger.info(f"ModelLoader: Loading models from registry {self.registry_dir} on device {self.device}...")

            # ── 1. Preprocessor & Schema ──────────────────────────────────────
            # Prefer registry preprocessor (matches training input_dim exactly)
            reg_prep_path = os.path.join(self.registry_dir, "preprocessor.pkl")
            fallback_prep_path = os.path.join(self.models_dir, "preprocessor.pkl")
            for prep_path in [reg_prep_path, fallback_prep_path]:
                if os.path.exists(prep_path):
                    self.preprocessor = joblib.load(prep_path)
                    if not hasattr(self.preprocessor, "cleaning_stats") or self.preprocessor.cleaning_stats is None:
                        self.preprocessor.cleaning_stats = {}
                    if not hasattr(self.preprocessor, "city_stats") or self.preprocessor.city_stats is None:
                        self.preprocessor.city_stats = {}
                    if not hasattr(self.preprocessor, "state_stats") or self.preprocessor.state_stats is None:
                        self.preprocessor.state_stats = {}
                    logger.info(f"Loaded preprocessor from {prep_path}")
                    break

            reg_schema_path = os.path.join(self.registry_dir, "feature_columns.json")
            fallback_schema_path = os.path.join(self.models_dir, "feature_columns.json")
            for schema_path in [reg_schema_path, fallback_schema_path]:
                if os.path.exists(schema_path):
                    with open(schema_path, "r", encoding="utf-8") as f:
                        self.feature_columns = json.load(f).get("feature_columns", [])
                    logger.info(f"Loaded feature columns ({len(self.feature_columns)}) from {schema_path}")
                    break

            # Fallback hardcoded schema if no file found
            if not self.feature_columns:
                self.feature_columns = [
                    "Victim Age", "City_encoded", "State_encoded", "Victim Gender_encoded", "Weapon Used_encoded",
                    "Year", "Month", "Day", "Weekday", "Hour", "Is_Weekend", "Quarter",
                    "sin_month", "cos_month", "sin_hour", "cos_hour", "sin_weekday", "cos_weekday",
                    "City_Crime_Freq", "State_Crime_Freq", "Category_Freq",
                    "City_Mean_Police", "City_Closure_Rate", "State_Mean_Police", "State_Closure_Rate",
                    "Reporting_Lag_Hours",
                ]
                logger.warning("ModelLoader: Feature columns file not found; using hardcoded defaults.")

            config_path = os.path.join(self.models_dir, "training_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    self.training_config = json.load(f)

            meta_path = os.path.join(self.models_dir, "model_metadata.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    self.model_metadata = json.load(f)

            input_dim = len(self.feature_columns)
            num_classes = (
                len(self.preprocessor.label_encoders["Crime Domain"].classes_)
                if self.preprocessor and "Crime Domain" in self.preprocessor.label_encoders
                else 4
            )

            # ── 2. Load FT-Transformer Classifier ─────────────────────────────
            ft_class_path = os.path.join(self.registry_dir, "ft_transformer.py")
            ft_ckpt_path = os.path.join(self.registry_dir, "ft_transformer.pt")
            if os.path.exists(ft_class_path) and os.path.exists(ft_ckpt_path):
                try:
                    FTTransformerClassifier = _load_class_from_file(ft_class_path, "FTTransformerClassifier")
                    self.ft_classifier = FTTransformerClassifier(input_dim=input_dim, num_classes=num_classes)
                    self.ft_classifier.load_state_dict(
                        torch.load(ft_ckpt_path, map_location=self.device, weights_only=True)
                    )
                    self.ft_classifier.to(self.device)
                    self.ft_classifier.eval()
                    logger.info("Loaded FTTransformerClassifier from registry.")
                except Exception as e:
                    logger.warning(f"Failed to load FT-Transformer: {e}")
                    self.ft_classifier = None

            # ── 3. Load Enhanced MLP Classifier ──────────────────────────────
            mlp_class_path = os.path.join(self.registry_dir, "mlp_classifier.py")
            mlp_ckpt_path = os.path.join(self.registry_dir, "crime_classifier.pt")
            if os.path.exists(mlp_class_path) and os.path.exists(mlp_ckpt_path):
                try:
                    CrimeMLPClassifier = _load_class_from_file(mlp_class_path, "CrimeMLPClassifier")
                    self.mlp_classifier = CrimeMLPClassifier(input_dim=input_dim, num_classes=num_classes)
                    self.mlp_classifier.load_state_dict(
                        torch.load(mlp_ckpt_path, map_location=self.device, weights_only=True)
                    )
                    self.mlp_classifier.to(self.device)
                    self.mlp_classifier.eval()
                    logger.info("Loaded CrimeMLPClassifier from registry.")
                except Exception as e:
                    logger.warning(f"Failed to load MLP Classifier: {e}")
                    self.mlp_classifier = None

            # ── 4. Build Ensemble Classifier ──────────────────────────────────
            if self.ft_classifier is not None and self.mlp_classifier is not None:
                try:
                    ens_class_path = os.path.join(self.registry_dir, "ensemble_classifier.py")
                    EnsembleClassifier = _load_class_from_file(ens_class_path, "EnsembleClassifier")
                    self.ensemble_classifier = EnsembleClassifier(
                        [self.ft_classifier, self.mlp_classifier], weights=[0.6, 0.4]
                    )
                    self.ensemble_classifier.to(self.device)
                    self.ensemble_classifier.eval()
                    logger.info("Built EnsembleClassifier (FT-Transformer 60% + MLP 40%).")
                except Exception as e:
                    logger.warning(f"Failed to build Ensemble: {e}")
                    self.ensemble_classifier = None
            elif self.ft_classifier is not None:
                # Fallback: use FT-Transformer directly as the single classifier
                self.ensemble_classifier = self.ft_classifier
            elif self.mlp_classifier is not None:
                self.ensemble_classifier = self.mlp_classifier

            # ── 5. Load Contrastive Embedding Network ─────────────────────────
            emb_class_path = os.path.join(self.registry_dir, "embedding_network.py")
            emb_ckpt_path = os.path.join(self.registry_dir, "embedding_model.pt")
            if os.path.exists(emb_class_path) and os.path.exists(emb_ckpt_path):
                try:
                    CrimeEmbeddingNetwork = _load_class_from_file(emb_class_path, "CrimeEmbeddingNetwork")
                    self.embedding_net = CrimeEmbeddingNetwork(input_dim=input_dim, embedding_dim=64)
                    self.embedding_net.load_state_dict(
                        torch.load(emb_ckpt_path, map_location=self.device, weights_only=True)
                    )
                    self.embedding_net.to(self.device)
                    self.embedding_net.eval()
                    logger.info("Loaded CrimeEmbeddingNetwork from registry.")
                except Exception as e:
                    logger.warning(f"Failed to load Embedding Network: {e}")
                    self.embedding_net = None

            # ── 6. Load N-BEATS Forecaster ────────────────────────────────────
            # Try registry first, then models dir
            nbeats_class_path = os.path.join(self.registry_dir, "nbeats_forecaster.py")
            nbeats_ckpt_path = os.path.join(self.models_dir, "forecast_model.pt")
            if os.path.exists(nbeats_class_path) and os.path.exists(nbeats_ckpt_path):
                try:
                    NBEATSForecaster = _load_class_from_file(nbeats_class_path, "NBEATSForecaster")
                    self.nbeats_forecaster = NBEATSForecaster(input_size=30, forecast_horizon=7)
                    self.nbeats_forecaster.load_state_dict(
                        torch.load(nbeats_ckpt_path, map_location=self.device, weights_only=True)
                    )
                    self.nbeats_forecaster.to(self.device)
                    self.nbeats_forecaster.eval()
                    logger.info("Loaded N-BEATS Forecaster from checkpoint.")
                except Exception as e:
                    logger.warning(f"Failed to load N-BEATS Forecaster: {e}")
                    self.nbeats_forecaster = None

            # ── 7. Warm-Up ────────────────────────────────────────────────────
            self._warmup(input_dim)
            self.is_loaded = True
            logger.info(
                "ModelLoader: All models loaded successfully. "
                f"FT={self.ft_classifier is not None}, MLP={self.mlp_classifier is not None}, "
                f"Ensemble={self.ensemble_classifier is not None}, "
                f"Embedding={self.embedding_net is not None}, "
                f"N-BEATS={self.nbeats_forecaster is not None}"
            )
            return True

    def reload_models(self, models_dir: Optional[str] = None) -> bool:
        """Unload and reload models from disk without restarting FastAPI."""
        with self._lock:
            self.is_loaded = False
            self.preprocessor = None
            self.feature_columns = []
            self.training_config = {}
            self.model_metadata = {}
            self.ft_classifier = None
            self.mlp_classifier = None
            self.ensemble_classifier = None
            self.nbeats_forecaster = None
            self.embedding_net = None
            if models_dir is not None:
                self.models_dir = models_dir
        return self.load_all_models()

    def _warmup(self, input_dim: int) -> None:
        """Executes 1 dummy forward pass on all loaded models to prime PyTorch computation graphs."""
        if not TORCH_AVAILABLE or torch is None:
            return

        with torch.inference_mode():
            dummy_input = torch.zeros(1, input_dim, dtype=torch.float32, device=self.device)
            dummy_seq = torch.zeros(1, 30, dtype=torch.float32, device=self.device)

            if self.ensemble_classifier is not None:
                try:
                    _ = self.ensemble_classifier(dummy_input)
                except Exception as e:
                    logger.warning(f"Warmup failed for ensemble: {e}")

            if self.ft_classifier is not None and self.ft_classifier is not self.ensemble_classifier:
                try:
                    _ = self.ft_classifier(dummy_input)
                except Exception as e:
                    logger.warning(f"Warmup failed for FT-Transformer: {e}")

            if self.embedding_net is not None:
                try:
                    _ = self.embedding_net.get_embedding(dummy_input)
                except Exception as e:
                    logger.warning(f"Warmup failed for Embedding Network: {e}")

            if self.nbeats_forecaster is not None:
                try:
                    _ = self.nbeats_forecaster(dummy_seq)
                except Exception as e:
                    logger.warning(f"Warmup failed for N-BEATS: {e}")

    def prepare_sample_tensor(self, sample: dict) -> Any:
        """Preprocesses a raw incident dictionary payload into a normalized PyTorch tensor."""
        field_mapping = {
            "city": "City",
            "crime_description": "Crime Description",
            "victim_age": "Victim Age",
            "victim_gender": "Victim Gender",
            "weapon_used": "Weapon Used",
            "date_of_occurrence": "Date of Occurrence",
            "time_of_occurrence": "Time of Occurrence",
            "date_reported": "Date Reported",
            "case_closed": "Case Closed",
            "crime_code": "Crime Code",
            "state": "State",
            "latitude": "Latitude",
            "longitude": "Longitude",
        }
        normalized_sample = {field_mapping.get(k, k): v for k, v in sample.items()}
        df_raw = pd.DataFrame([normalized_sample])
        if self.preprocessor is not None:
            if not hasattr(self.preprocessor, "cleaning_stats") or self.preprocessor.cleaning_stats is None:
                self.preprocessor.cleaning_stats = {}
            df_processed = self.preprocessor.transform(df_raw)
        else:
            df_processed = df_raw

        from ai.preprocessing.feature_engineering import FeatureEngineer
        fe = FeatureEngineer()
        fe.city_stats = getattr(self.preprocessor, "city_stats", {})
        fe.state_stats = getattr(self.preprocessor, "state_stats", {})

        df_feats = fe.transform(df_processed, is_train=False)
        X, _, _ = fe.get_feature_matrix(df_feats, target_type="classification")

        if isinstance(X, pd.DataFrame):
            for col in self.feature_columns:
                if col not in X.columns:
                    X[col] = 0.0
            X = X[self.feature_columns]
            x_array = X.to_numpy()
        else:
            x_array = np.array(X)

        return torch.tensor(x_array, dtype=torch.float32, device=self.device)
