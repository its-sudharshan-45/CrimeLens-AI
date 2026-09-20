"""
ai/inference/hotspot_predictor.py
=================================
Standalone Inference Engine for City-Level Crime Hotspot Prediction (Phase 4).

Provides:
  - HotspotPredictor class for loading checkpoints and making city risk forecasts
  - Strict input validation (dimensions, NaN/Inf checks, city/channel counts)
  - Automatic feature scaling and target inverse transformation
  - Normalized risk scores [0.0, 1.0] and risk tiers (Low, Medium, High)
  - Reusable predict_hotspots(recent_hotspot_data, top_n=5) function
  - Ethical notice and limitation disclaimers
  - Standalone runnable: python -m ai.inference.hotspot_predictor
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional, Union

import numpy as np
import torch

from ai.models.hotspot.cnn_hotspot import CNNHotspotForecaster

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("HotspotPredictor")

DEFAULT_CHECKPOINT_PATH = "ai/models/hotspot/cnn_hotspot_best.pt"
ETHICAL_DISCLAIMER = (
    "This is a probabilistic, city-level risk estimate based on historical patterns. "
    "It is not a prediction that a crime will definitely occur, nor is it an individual "
    "suspect/victim profiling tool."
)


class HotspotPredictor:
    """
    Production-ready standalone predictor for city-level crime hotspots.

    Args:
        checkpoint_path: Path to the trained PyTorch checkpoint (.pt)
        device: 'cpu' or 'cuda' (defaults to best available)
    """

    def __init__(
        self,
        checkpoint_path: str = DEFAULT_CHECKPOINT_PATH,
        device: Optional[str] = None,
    ) -> None:
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Hotspot checkpoint not found at: {checkpoint_path}")

        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.checkpoint = torch.load(checkpoint_path, map_location=self.device)

        # Model configuration
        self.config = self.checkpoint.get("model_config", {})
        self.window_size = self.checkpoint.get("window_size", 30)
        self.forecast_horizon = self.checkpoint.get("forecast_horizon", 7)
        self.cities: List[str] = self.checkpoint.get("cities", [])
        self.feature_channels: List[str] = self.checkpoint.get("feature_channels", [])
        self.n_cities = len(self.cities)
        self.n_features = len(self.feature_channels)

        # Scaler statistics
        self.scaler_stats = self.checkpoint.get("scaler_stats", {})
        self.f_min = np.array(self.scaler_stats.get("f_min", [0.0] * self.n_features), dtype=np.float32)
        self.f_max = np.array(self.scaler_stats.get("f_max", [1.0] * self.n_features), dtype=np.float32)
        self.f_denom = np.array(self.scaler_stats.get("f_denom", [1.0] * self.n_features), dtype=np.float32)
        self.y_min = float(self.scaler_stats.get("y_min", 0.0))
        self.y_max = float(self.scaler_stats.get("y_max", 1.0))
        self.y_denom = float(self.scaler_stats.get("y_denom", 1.0))

        # Instantiate model
        self.model = CNNHotspotForecaster(
            n_cities=self.n_cities,
            n_features=self.n_features,
            window_size=self.window_size,
            conv_filters_1=self.config.get("conv_filters_1", 32),
            conv_filters_2=self.config.get("conv_filters_2", 64),
            fc_hidden=self.config.get("fc_hidden", 128),
            dropout=self.config.get("dropout", 0.2),
        )
        self.model.load_state_dict(self.checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

        logger.info(
            f"HotspotPredictor initialized: {self.n_cities} cities, "
            f"{self.n_features} features, window={self.window_size}d, "
            f"device={self.device}"
        )

    def validate_input(self, data: Union[np.ndarray, torch.Tensor]) -> np.ndarray:
        """
        Validate input dimensions and values.

        Expected shape: (30, 29, 8) or (batch_size, 30, 29, 8)
        """
        if isinstance(data, torch.Tensor):
            arr = data.detach().cpu().numpy()
        elif isinstance(data, np.ndarray):
            arr = data.copy()
        else:
            raise TypeError(f"Input must be np.ndarray or torch.Tensor, got {type(data)}")

        if arr.dtype != np.float32 and arr.dtype != np.float64:
            arr = arr.astype(np.float32)

        # Check for NaN / Inf
        if np.isnan(arr).any():
            raise ValueError("Input data contains NaN values.")
        if np.isinf(arr).any():
            raise ValueError("Input data contains Infinite (Inf) values.")

        # If single window (30, 29, 8), add batch dimension -> (1, 30, 29, 8)
        if arr.ndim == 3:
            arr = np.expand_dims(arr, axis=0)

        if arr.ndim != 4:
            raise ValueError(
                f"Input tensor must have 3 dimensions (window, cities, features) or "
                f"4 dimensions (batch, window, cities, features). Got {arr.ndim} dimensions."
            )

        b, w, c, f = arr.shape
        if w != self.window_size:
            raise ValueError(
                f"Invalid historical window length: expected {self.window_size} days, got {w} days."
            )
        if c != self.n_cities:
            raise ValueError(
                f"Invalid number of cities: expected {self.n_cities}, got {c}."
            )
        if f != self.n_features:
            raise ValueError(
                f"Invalid number of features: expected {self.n_features}, got {f}."
            )

        return arr

    def scale_input(self, arr: np.ndarray) -> np.ndarray:
        """Apply feature-wise min-max normalization fit on training slice."""
        return (arr - self.f_min) / self.f_denom

    @torch.no_grad()
    def predict(
        self,
        recent_data: Union[np.ndarray, torch.Tensor],
        top_n: int = 5,
        low_risk_threshold: float = 0.33,
        med_risk_threshold: float = 0.66,
    ) -> Dict[str, Any]:
        """
        Run inference on recent spatio-temporal observations.

        Args:
            recent_data: Array of shape (30, 29, 8) or (B, 30, 29, 8)
            top_n: Number of top risk cities to return (default: 5)
            low_risk_threshold: Boundary for Low risk level (default: 0.33)
            med_risk_threshold: Boundary for Medium risk level (default: 0.66)

        Returns:
            Dict with ranked hotspots, full city predictions, and ethical disclaimer.
        """
        arr = self.validate_input(recent_data)
        scaled_arr = self.scale_input(arr)

        tensor_in = torch.tensor(scaled_arr, dtype=torch.float32, device=self.device)
        preds_scaled = self.model(tensor_in).cpu().numpy()  # (B, 29)

        # Invert target scaling back to original incident count
        preds_unscaled = np.clip(preds_scaled * self.y_denom + self.y_min, a_min=0.0, a_max=None)

        # For single sample inference (or latest sample in batch)
        latest_pred = preds_unscaled[-1]

        p_min = float(latest_pred.min())
        p_max = float(latest_pred.max())
        p_range = (p_max - p_min) if (p_max - p_min) > 1e-7 else 1.0

        risk_scores = (latest_pred - p_min) / p_range

        all_cities_list = []
        for idx, city in enumerate(self.cities):
            score = float(risk_scores[idx])
            val = float(latest_pred[idx])

            if score >= med_risk_threshold:
                level = "High"
            elif score >= low_risk_threshold:
                level = "Medium"
            else:
                level = "Low"

            all_cities_list.append({
                "city": city,
                "predicted_crime": round(val, 2),
                "risk_score": round(score, 4),
                "risk_level": level,
            })

        # Sort descending by risk score
        all_cities_list.sort(key=lambda x: x["risk_score"], reverse=True)

        for rank_idx, item in enumerate(all_cities_list, 1):
            item["rank"] = rank_idx

        top_n_hotspots = all_cities_list[: min(top_n, len(all_cities_list))]

        return {
            "model_name": "CNNHotspotForecaster",
            "forecast_horizon_days": self.forecast_horizon,
            "lookback_window_days": self.window_size,
            "total_cities_evaluated": self.n_cities,
            "hotspots": top_n_hotspots,
            "all_city_predictions": all_cities_list,
            "uncertainty_estimation": "not_available (relative risk scores provided)",
            "disclaimer": ETHICAL_DISCLAIMER,
        }


def predict_hotspots(
    recent_hotspot_data: Union[np.ndarray, torch.Tensor],
    top_n: int = 5,
    checkpoint_path: str = DEFAULT_CHECKPOINT_PATH,
) -> Dict[str, Any]:
    """
    Reusable convenience function for hotspot forecasting.
    """
    predictor = HotspotPredictor(checkpoint_path=checkpoint_path)
    return predictor.predict(recent_hotspot_data, top_n=top_n)


if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  CrimeLens AI — Standalone Hotspot Predictor (Phase 4 Demo)")
    print("=" * 65)

    tensor_path = "datasets/processed/hotspot_tensor.npz"
    if not os.path.exists(tensor_path):
        print(f"Error: Could not locate tensor at {tensor_path}")
        sys.exit(1)

    # Load last 30 days from tensor as a sample test window
    npz = np.load(tensor_path)
    full_tensor = npz["hotspot_tensor"]
    sample_window = full_tensor[-30:]  # (30, 29, 8)

    predictor = HotspotPredictor()
    result = predictor.predict(sample_window, top_n=5)

    print(f"\nModel: {result['model_name']}")
    print(f"Forecast Horizon: Next {result['forecast_horizon_days']} Days")
    print(f"Lookback Window:  Previous {result['lookback_window_days']} Days\n")

    print(f"  {'Rank':<5} | {'City':<16} | {'Pred 7d Crime':<15} | {'Risk Score':<12} | {'Risk Level'}")
    print(f"  {'-'*5}-+-{'-'*16}-+-{'-'*15}-+-{'-'*12}-+-{'-'*10}")
    for item in result["hotspots"]:
        print(f"  {item['rank']:<5} | {item['city']:<16} | {item['predicted_crime']:<15.2f} | {item['risk_score']:<12.4f} | {item['risk_level']}")

    print("\n[ETHICAL DISCLAIMER]")
    print(f"  {result['disclaimer']}")
    print("=" * 65 + "\n")
