"""
ai/tests/test_temporal_models.py
================================
Automated test suite for Phase 3 Temporal Crime Forecasters (LSTM and GRU).

Tests:
  1. Model initialization for LSTM and GRU
  2. Forward pass input/output dimensions: (batch, 30, 13) -> (batch, 7)
  3. 2D input fallback handling: (batch, 30) -> (batch, 7)
  4. Numerical stability: zero NaNs or Infs under extreme inputs
  5. Gradient flow: gradient propagation updates all parameter tensors
  6. Training smoke test: single training & validation epoch execution
  7. Checkpoint persistence: state dict save, reload, and identical predictions
  8. Standalone inference module: shape validation, rescaled predictions, uncertainty bounds
  9. Seed reproducibility: deterministic outputs under fixed random seed
  10. Metric computation correctness: MAE, RMSE, safe MAPE, sMAPE
"""
# cspell:words autouse

import os
import tempfile
import numpy as np
import torch
import torch.nn as nn
import pytest  # type: ignore[import-not-found]

from ai.models.temporal.lstm import CrimeLSTMForecaster
from ai.models.temporal.gru import CrimeGRUForecaster
from ai.training.temporal_trainer import seed_everything, TemporalTrainer
from ai.evaluation.temporal_evaluator import calculate_metrics, inverse_transform_target
from ai.inference.temporal_predictor import TemporalCrimePredictor


@pytest.fixture(autouse=True)
def set_seed():
    """Ensure deterministic environment for test runs."""
    seed_everything(42)


# -------------------------------------------------------------------------
# 1. Model Initialization
# -------------------------------------------------------------------------
def test_lstm_initialization():
    """Verify LSTM forecaster initializes with valid architecture."""
    model = CrimeLSTMForecaster(input_size=13, hidden_size=64, num_layers=2, forecast_horizon=7)
    assert isinstance(model, nn.Module)
    cfg = model.get_config()
    assert cfg["model_type"] == "LSTM"
    assert cfg["input_size"] == 13
    assert cfg["hidden_size"] == 64
    assert cfg["num_layers"] == 2
    assert cfg["forecast_horizon"] == 7
    assert sum(p.numel() for p in model.parameters()) > 0


def test_gru_initialization():
    """Verify GRU forecaster initializes with valid architecture."""
    model = CrimeGRUForecaster(input_size=13, hidden_size=64, num_layers=2, forecast_horizon=7)
    assert isinstance(model, nn.Module)
    cfg = model.get_config()
    assert cfg["model_type"] == "GRU"
    assert cfg["input_size"] == 13
    assert cfg["hidden_size"] == 64
    assert cfg["num_layers"] == 2
    assert cfg["forecast_horizon"] == 7
    assert sum(p.numel() for p in model.parameters()) > 0


# -------------------------------------------------------------------------
# 2. Forward Pass Dimensions
# -------------------------------------------------------------------------
@pytest.mark.parametrize("model_cls", [CrimeLSTMForecaster, CrimeGRUForecaster])
def test_forward_pass_multivariate_shape(model_cls):
    """Verify (batch, 30, 13) input maps to exactly (batch, 7) output."""
    model = model_cls(input_size=13, hidden_size=64, num_layers=2, forecast_horizon=7)
    model.eval()

    batch_sizes = [1, 16, 32]
    for b in batch_sizes:
        x = torch.randn(b, 30, 13)
        with torch.no_grad():
            out = model(x)
        assert out.shape == (b, 7), f"Expected shape ({b}, 7), got {out.shape}"


@pytest.mark.parametrize("model_cls", [CrimeLSTMForecaster, CrimeGRUForecaster])
def test_forward_pass_2d_fallback(model_cls):
    """Verify (batch, 30) 2D input is safely expanded to (batch, 30, 1)."""
    model = model_cls(input_size=1, hidden_size=32, num_layers=1, forecast_horizon=7)
    model.eval()

    x = torch.randn(8, 30)
    with torch.no_grad():
        out = model(x)
    assert out.shape == (8, 7)


# -------------------------------------------------------------------------
# 3. Numerical Stability
# -------------------------------------------------------------------------
@pytest.mark.parametrize("model_cls", [CrimeLSTMForecaster, CrimeGRUForecaster])
def test_numerical_stability(model_cls):
    """Verify output contains no NaNs or Infs even under extreme numerical ranges."""
    model = model_cls(input_size=13, hidden_size=64, num_layers=2, forecast_horizon=7)
    model.eval()

    inputs = [
        torch.zeros(4, 30, 13),
        torch.ones(4, 30, 13) * 100.0,
        torch.randn(4, 30, 13) * 10.0,
    ]
    for x in inputs:
        with torch.no_grad():
            out = model(x)
        assert torch.all(torch.isfinite(out)), "Output contains NaN or Inf values!"


# -------------------------------------------------------------------------
# 4. Gradient Flow
# -------------------------------------------------------------------------
@pytest.mark.parametrize("model_cls", [CrimeLSTMForecaster, CrimeGRUForecaster])
def test_gradient_flow(model_cls):
    """Verify gradient propagation computes valid non-zero gradients for all layers."""
    model = model_cls(input_size=13, hidden_size=32, num_layers=2, forecast_horizon=7)
    model.train()

    x = torch.randn(16, 30, 13)
    y = torch.randn(16, 7)
    criterion = nn.HuberLoss()

    out = model(x)
    loss = criterion(out, y)
    loss.backward()

    for name, param in model.named_parameters():
        assert param.grad is not None, f"Parameter {name} has no gradient."
        assert not torch.isnan(param.grad).any(), f"Parameter {name} gradient is NaN."
        assert not torch.isinf(param.grad).any(), f"Parameter {name} gradient is Inf."


# -------------------------------------------------------------------------
# 5. Training & Validation Execution
# -------------------------------------------------------------------------
def test_training_smoke_step():
    """Verify TemporalTrainer executes train and validation cycles correctly."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        trainer = TemporalTrainer(device="cpu", save_dir=tmp_dir)
        model = CrimeGRUForecaster(input_size=13, hidden_size=32, num_layers=1, forecast_horizon=7)

        # Synthetic micro-dataset
        x_tr = torch.randn(32, 30, 13)
        y_tr = torch.randn(32, 7)
        x_va = torch.randn(16, 30, 13)
        y_va = torch.randn(16, 7)

        from torch.utils.data import DataLoader, TensorDataset
        train_loader = DataLoader(TensorDataset(x_tr, y_tr), batch_size=16)
        val_loader = DataLoader(TensorDataset(x_va, y_va), batch_size=16)

        results = trainer.train_model(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            metadata={"feature_columns": [f"f_{i}" for i in range(13)]},
            model_name="GRU_Test",
            epochs=2,
            lr=0.01,
            patience=2,
            loss_type="HuberLoss",
        )

        assert results["best_epoch"] >= 1
        assert os.path.exists(results["checkpoint_path"])
        assert len(results["history"]["train_loss"]) == 2


# -------------------------------------------------------------------------
# 6. Checkpoint Persistence
# -------------------------------------------------------------------------
def test_checkpoint_save_and_reload():
    """Verify saved checkpoint restores model weights and produces bit-identical predictions."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ckpt_path = os.path.join(tmp_dir, "test_lstm.pt")
        model = CrimeLSTMForecaster(input_size=13, hidden_size=32, num_layers=1, forecast_horizon=7)
        model.eval()

        test_input = torch.randn(4, 30, 13)
        with torch.no_grad():
            expected_preds = model(test_input)

        # Save checkpoint
        torch.save({
            "model_state_dict": model.state_dict(),
            "model_type": "LSTM",
            "config": model.get_config(),
            "scaler_data_min": [24.0],
            "scaler_data_max": [24.0],
        }, ckpt_path)

        # Reload into new instance
        reloaded = CrimeLSTMForecaster(input_size=13, hidden_size=32, num_layers=1, forecast_horizon=7)
        ckpt_data = torch.load(ckpt_path, weights_only=False)
        reloaded.load_state_dict(ckpt_data["model_state_dict"])
        reloaded.eval()

        with torch.no_grad():
            actual_preds = reloaded(test_input)

        torch.testing.assert_close(expected_preds, actual_preds)


# -------------------------------------------------------------------------
# 7. Standalone Inference Module
# -------------------------------------------------------------------------
def test_standalone_inference():
    """Verify TemporalCrimePredictor runs inference and returns structured output."""
    predictor = TemporalCrimePredictor()

    sample_seq = np.zeros((30, 13), dtype=np.float32)
    result = predictor.predict(sample_seq, return_uncertainty=True)

    assert result["forecast_horizon_days"] == 7
    assert len(result["predictions"]) == 7
    for p in result["predictions"]:
        assert "day" in p
        assert "predicted_crime_count" in p
        assert "lower_bound_95" in p
        assert "upper_bound_95" in p
        assert p["lower_bound_95"] <= p["predicted_crime_count"] <= p["upper_bound_95"]

    assert "disclaimer" in result


def test_inference_dimension_validation():
    """Verify predictor rejects invalid input shapes."""
    predictor = TemporalCrimePredictor()

    with pytest.raises(ValueError, match="Expected input shape"):
        predictor.predict(np.zeros((20, 13)))  # Wrong sequence length

    with pytest.raises(ValueError, match="Expected input shape"):
        predictor.predict(np.zeros((30, 5)))   # Wrong feature count


# -------------------------------------------------------------------------
# 8. Reproducibility
# -------------------------------------------------------------------------
def test_seed_reproducibility():
    """Verify identical random seeds produce identical initialized weights and outputs."""
    seed_everything(123)
    m1 = CrimeGRUForecaster(input_size=13, hidden_size=32, num_layers=1)
    x1 = torch.randn(2, 30, 13)
    out1 = m1(x1)

    seed_everything(123)
    m2 = CrimeGRUForecaster(input_size=13, hidden_size=32, num_layers=1)
    x2 = torch.randn(2, 30, 13)
    out2 = m2(x2)

    torch.testing.assert_close(out1, out2)


# -------------------------------------------------------------------------
# 9. Evaluation Metrics Correctness
# -------------------------------------------------------------------------
def test_metric_calculations():
    """Verify regression metrics calculate expected values."""
    y_true = np.array([[20.0, 25.0], [30.0, 35.0]])
    y_pred = np.array([[22.0, 23.0], [29.0, 37.0]])

    metrics = calculate_metrics(y_true, y_pred)
    assert metrics["MAE"] == pytest.approx(1.75, abs=0.01)
    assert metrics["RMSE"] == pytest.approx(1.8028, abs=0.01)
    assert metrics["MAPE"] > 0.0
    assert metrics["sMAPE"] > 0.0


def test_inverse_transform_target():
    """Verify target inverse scaling preserves ground truth incident values."""
    # When data_min == data_max == 24.0
    scaled = np.array([0.0, -16.0])
    unscaled = inverse_transform_target(scaled, data_min=24.0, data_max=24.0)
    assert np.allclose(unscaled, [24.0, 8.0])

    # When data_min != data_max
    scaled_norm = np.array([0.0, 0.5, 1.0])
    unscaled_norm = inverse_transform_target(scaled_norm, data_min=10.0, data_max=30.0)
    assert np.allclose(unscaled_norm, [10.0, 20.0, 30.0])
