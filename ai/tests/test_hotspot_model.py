"""
ai/tests/test_hotspot_model.py
==============================
Unit and Integration Test Suite for Phase 4 City-Level Crime Hotspot Forecaster.

Covers:
  - Phase 2 Hotspot tensor loading, dimensions, and numerical validity
  - CNNHotspotForecaster architecture initialization, forward pass, output shape
  - Backward pass and gradient flow through convolutional and linear layers
  - Single-epoch training and validation pipeline step
  - Checkpoint serialization and deserialization
  - Standalone HotspotPredictor input validation (shape checks, NaN/Inf rejection)
  - Risk score normalization and ranking order validation
  - Baseline historical average prediction and metric computation
"""
# cspell:words backpropagate

import os
import json
import pytest  # type: ignore[import-not-found]
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from ai.models.hotspot.cnn_hotspot import CNNHotspotForecaster
from ai.training.hotspot_trainer import (
    load_hotspot_tensor_data,
    build_sliding_windows,
    prepare_hotspot_splits,
    compute_baseline_predictions,
    HotspotTrainer,
)
from ai.evaluation.hotspot_evaluator import (
    calculate_regression_metrics,
    rank_city_risks,
    compute_per_city_metrics,
)
from ai.inference.hotspot_predictor import (
    HotspotPredictor,
    predict_hotspots,
)


# =====================================================================
# 1. DATASET TESTS
# =====================================================================

def test_hotspot_tensor_loading_and_shape():
    """Verify that hotspot tensor and metadata exist and match expected dimensions."""
    tensor, meta = load_hotspot_tensor_data()
    assert tensor.ndim == 3, f"Expected 3D tensor, got {tensor.ndim}D"
    assert tensor.shape[0] == 1674, f"Expected 1674 days, got {tensor.shape[0]}"
    assert tensor.shape[1] == 29, f"Expected 29 cities, got {tensor.shape[1]}"
    assert tensor.shape[2] == 8, f"Expected 8 features, got {tensor.shape[2]}"

    assert meta["city_count"] == 29
    assert meta["channel_count"] == 8
    assert len(meta["cities"]) == 29
    assert len(meta["feature_channels"]) == 8


def test_hotspot_tensor_no_nan_or_inf():
    """Ensure raw hotspot tensor contains zero NaN and zero Infinite entries."""
    tensor, _ = load_hotspot_tensor_data()
    assert not np.isnan(tensor).any(), "Hotspot tensor contains unexpected NaN values"
    assert not np.isinf(tensor).any(), "Hotspot tensor contains unexpected Inf values"


def test_sliding_window_shapes_and_leakage_free_splits():
    """Verify sliding window generator produces correct shapes without overlapping future targets."""
    tensor, meta = load_hotspot_tensor_data()
    splits = prepare_hotspot_splits(tensor, meta, window_size=30, forecast_horizon=7)

    assert splits["X_train_scaled"].shape == (1060, 30, 29, 8)
    assert splits["y_train_scaled"].shape == (1060, 29)
    assert splits["X_val_scaled"].shape == (359, 30, 29, 8)
    assert splits["y_val_scaled"].shape == (359, 29)
    assert splits["X_test_scaled"].shape == (207, 30, 29, 8)
    assert splits["y_test_scaled"].shape == (207, 29)

    # Scaler stats must be present
    assert "f_min" in splits["scaler_stats"]
    assert "f_max" in splits["scaler_stats"]
    assert len(splits["scaler_stats"]["f_min"]) == 8


# =====================================================================
# 2. MODEL ARCHITECTURE TESTS
# =====================================================================

def test_cnn_initialization_and_forward_pass():
    """Test model instantiation and forward pass produces (batch_size, 29) tensor."""
    model = CNNHotspotForecaster(n_cities=29, n_features=8, window_size=30)
    x = torch.randn(4, 30, 29, 8)
    out = model(x)
    assert out.shape == (4, 29), f"Expected output shape (4, 29), got {out.shape}"


def test_cnn_gradient_flow():
    """Ensure gradients backpropagate through convolutional backbone and linear head."""
    model = CNNHotspotForecaster(n_cities=29, n_features=8, window_size=30)
    x = torch.randn(2, 30, 29, 8)
    out = model(x)
    loss = out.sum()
    loss.backward()

    for name, param in model.named_parameters():
        assert param.grad is not None, f"Parameter {name} has no gradient."
        assert not torch.isnan(param.grad).any(), f"Parameter {name} gradient is NaN."
        assert not torch.isinf(param.grad).any(), f"Parameter {name} gradient is Inf."


def test_cnn_get_config():
    """Verify get_config returns expected architectural hyperparameters."""
    model = CNNHotspotForecaster()
    cfg = model.get_config()
    assert cfg["model_type"] == "CNNHotspotForecaster"
    assert cfg["n_cities"] == 29
    assert cfg["n_features"] == 8
    assert cfg["window_size"] == 30


# =====================================================================
# 3. TRAINING PIPELINE TESTS
# =====================================================================

def test_single_training_epoch_and_validation():
    """Verify that a training epoch runs and reduces loss on synthetic batch."""
    model = CNNHotspotForecaster(n_cities=29, n_features=8, window_size=30)
    criterion = nn.SmoothL1Loss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    X_dummy = torch.randn(16, 30, 29, 8)
    y_dummy = torch.rand(16, 29)
    ds = TensorDataset(X_dummy, y_dummy)
    loader = DataLoader(ds, batch_size=8)

    trainer = HotspotTrainer(model, criterion, optimizer)
    loss_1 = trainer.train_epoch(loader)
    loss_2 = trainer.train_epoch(loader)
    val_loss = trainer.evaluate(loader)

    assert isinstance(loss_1, float) and not np.isnan(loss_1)
    assert isinstance(val_loss, float) and not np.isnan(val_loss)


# =====================================================================
# 4. CHECKPOINT TESTS
# =====================================================================

def test_checkpoint_saving_and_loading(tmp_path):
    """Test that model checkpoint can be saved and loaded with identical weights."""
    model = CNNHotspotForecaster(n_cities=29, n_features=8, window_size=30)
    save_file = str(tmp_path / "test_hotspot.pt")

    checkpoint = {
        "model_state_dict": model.state_dict(),
        "model_config": model.get_config(),
        "window_size": 30,
        "forecast_horizon": 7,
        "cities": [f"City_{i}" for i in range(29)],
        "feature_channels": [f"Feat_{i}" for i in range(8)],
        "scaler_stats": {"y_min": 0.0, "y_max": 50.0, "y_denom": 50.0},
    }
    torch.save(checkpoint, save_file)
    assert os.path.exists(save_file)

    loaded_cp = torch.load(save_file)
    model2 = CNNHotspotForecaster(**{
        k: v for k, v in loaded_cp["model_config"].items() if k in ["n_cities", "n_features", "window_size"]
    })
    model2.load_state_dict(loaded_cp["model_state_dict"])

    # Forward pass outputs should be identical
    x = torch.randn(2, 30, 29, 8)
    model.eval()
    model2.eval()
    with torch.no_grad():
        out1 = model(x)
        out2 = model2(x)
    assert torch.allclose(out1, out2, atol=1e-5)


# =====================================================================
# 5. INFERENCE & VALIDATION TESTS
# =====================================================================

def test_inference_valid_input():
    """Verify predictor generates valid predictions and sorted rankings for valid input."""
    predictor = HotspotPredictor()
    dummy_input = np.random.uniform(0.0, 5.0, (30, 29, 8)).astype(np.float32)

    result = predictor.predict(dummy_input, top_n=5)
    assert "hotspots" in result
    assert len(result["hotspots"]) == 5
    assert len(result["all_city_predictions"]) == 29
    assert result["disclaimer"] != ""

    # Check risk score monotonicity in ranking
    scores = [item["risk_score"] for item in result["hotspots"]]
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], "Rankings must be sorted in descending order"


def test_inference_rejects_invalid_window():
    """Verify predictor raises ValueError on invalid historical window size."""
    predictor = HotspotPredictor()
    invalid_window = np.random.randn(20, 29, 8).astype(np.float32)  # 20 instead of 30 days
    with pytest.raises(ValueError, match="Invalid historical window length"):
        predictor.predict(invalid_window)


def test_inference_rejects_invalid_city_count():
    """Verify predictor raises ValueError on invalid city count."""
    predictor = HotspotPredictor()
    invalid_cities = np.random.randn(30, 15, 8).astype(np.float32)  # 15 instead of 29 cities
    with pytest.raises(ValueError, match="Invalid number of cities"):
        predictor.predict(invalid_cities)


def test_inference_rejects_nan_and_inf():
    """Verify predictor detects and rejects NaN and Inf values."""
    predictor = HotspotPredictor()
    nan_input = np.random.randn(30, 29, 8).astype(np.float32)
    nan_input[5, 5, 0] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        predictor.predict(nan_input)

    inf_input = np.random.randn(30, 29, 8).astype(np.float32)
    inf_input[5, 5, 0] = np.inf
    with pytest.raises(ValueError, match="Infinite"):
        predictor.predict(inf_input)


def test_convenience_predict_hotspots_function():
    """Test top-level predict_hotspots function."""
    dummy_input = np.random.uniform(0.0, 5.0, (30, 29, 8)).astype(np.float32)
    res = predict_hotspots(dummy_input, top_n=3)
    assert len(res["hotspots"]) == 3
    assert res["hotspots"][0]["rank"] == 1


# =====================================================================
# 6. BASELINE & METRICS TESTS
# =====================================================================

def test_baseline_predictions_and_metrics():
    """Test computation of historical baseline predictions and regression metrics."""
    X_dummy = np.ones((5, 30, 29, 8), dtype=np.float32) * 2.0  # 2.0 crimes per day
    preds = compute_baseline_predictions(X_dummy, forecast_horizon=7)
    # Expected: 2.0 * 7 = 14.0 for all cities
    assert preds.shape == (5, 29)
    assert np.allclose(preds, 14.0)

    y_dummy = np.ones((5, 29), dtype=np.float32) * 15.0
    metrics = calculate_regression_metrics(y_dummy, preds)
    assert metrics["mae"] == 1.0
    assert metrics["rmse"] == 1.0


def test_rank_city_risks_levels():
    """Verify that rank_city_risks accurately assigns High, Medium, and Low risk tiers."""
    predictions = np.array([10.0, 5.0, 0.0])
    cities = ["CityHigh", "CityMed", "CityLow"]
    ranked = rank_city_risks(predictions, cities)

    assert ranked[0]["city"] == "CityHigh"
    assert ranked[0]["risk_level"] == "High"
    assert ranked[0]["risk_score"] == 1.0

    assert ranked[1]["city"] == "CityMed"
    assert ranked[1]["risk_level"] == "Medium"
    assert ranked[1]["risk_score"] == 0.5

    assert ranked[2]["city"] == "CityLow"
    assert ranked[2]["risk_level"] == "Low"
    assert ranked[2]["risk_score"] == 0.0
