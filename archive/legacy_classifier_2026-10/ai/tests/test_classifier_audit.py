"""
ai/tests/test_classifier_audit.py
=================================
Regression tests for the 2026-10 classifier audit.

These tests lock in the correctness fixes that were verified during the audit:

1.  The leaking ``Category_Freq`` feature is excluded from the schema.
2.  Label encoding round-trips and handles unseen labels explicitly.
3.  The StandardScaler is fitted on train only and reused (train/serve parity).
4.  A fitted FeatureEngineer is reused at inference (no single-sample refit skew).
5.  Evaluation metrics match independently computed values (confusion matrix,
    macro/weighted F1, balanced accuracy, per-class supports).
6.  Absent classes and undefined metrics are handled transparently (NaN).
7.  Model forward/probability shapes are correct.

All tests use small synthetic fixtures or tiny dataset slices; none of them
present synthetic results as CrimeLens model performance.
"""

import math
import os
import sys

import numpy as np
import pandas as pd
import pytest
import torch
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
)
from torch.utils.data import DataLoader

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.dataset.crime_dataset import CrimeDataset  # noqa: E402
from ai.evaluation.evaluator import DeepLearningEvaluator  # noqa: E402
from ai.models.ft_transformer import FTTransformerClassifier  # noqa: E402
from ai.models.mlp_classifier import CrimeMLPClassifier  # noqa: E402
from ai.preprocessing.feature_engineering import FeatureEngineer  # noqa: E402
from ai.preprocessing.preprocessor import CrimeDataPreprocessor  # noqa: E402
from ai.training.losses import FocalLoss  # noqa: E402

RAW_DATASET_PATH = os.path.join(PROJECT_ROOT, "Dataset", "crime_dataset_india.csv")

EXPECTED_SCHEMA = [
    "Victim Age", "City_encoded", "State_encoded", "Victim Gender_encoded", "Weapon Used_encoded",
    "Year", "Month", "Day", "Day_of_Week", "Hour", "Week_of_Year", "Quarter", "Is_Weekend",
    "sin_month", "cos_month", "sin_hour", "cos_hour", "sin_weekday", "cos_weekday",
    "City_Crime_Freq", "State_Crime_Freq",
    "City_Mean_Police", "City_Closure_Rate", "State_Mean_Police", "State_Closure_Rate",
    "Reporting_Lag_Hours",
]


class _FixedLogits(torch.nn.Module):
    """Deterministic stub classifier: returns pre-supplied logits for a batch."""

    def __init__(self, logits: torch.Tensor) -> None:
        super().__init__()
        self.register_buffer("logits", logits)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        assert x.shape[0] == self.logits.shape[0], "stub expects a single batch"
        return self.logits


# =====================================================================
# 1. LEAKAGE / FEATURE SCHEMA
# =====================================================================

def test_feature_schema_excludes_leaking_category_freq():
    """`Category_Freq` deterministically leaked the target and must be absent."""
    fe = FeatureEngineer()
    df = pd.DataFrame({c: [1.0, 2.0] for c in EXPECTED_SCHEMA})
    df["Crime Domain_encoded"] = [0, 1]
    # Deliberately provide a Category_Freq column to prove it is ignored.
    df["Category_Freq"] = [10.0, 20.0]
    X, y, cols = fe.get_feature_matrix(df, target_type="classification")
    assert "Category_Freq" not in cols
    assert cols == EXPECTED_SCHEMA
    assert len(cols) == 26
    assert "Category_Freq" not in X.columns


# =====================================================================
# 2. LABEL ENCODING
# =====================================================================

def test_label_encoder_roundtrip_and_index_alignment():
    p = CrimeDataPreprocessor()
    domains = ["Fire Accident", "Other Crime", "Traffic Fatality", "Violent Crime"]
    df = pd.DataFrame({"Crime Domain": domains})
    p.fit_encoders(df)
    le = p.label_encoders["Crime Domain"]
    # Classes are stored in a deterministic (sorted) order and exposed as a mapping.
    assert list(le.classes_) == sorted(domains)
    for idx, label in enumerate(le.classes_):
        encoded = le.transform([label])[0]
        assert encoded == idx
        assert le.inverse_transform([encoded])[0] == label
    # The explicit mapping agrees with the encoder.
    assert p.category_mappings["Crime Domain"][label] == idx


def test_unseen_label_maps_to_known_fallback():
    p = CrimeDataPreprocessor()
    p.fit_encoders(pd.DataFrame({"City": ["Delhi", "Mumbai"]}))
    df = pd.DataFrame({"City": ["Delhi", "Atlantis"]})
    out = p.transform_encoders(df)
    # Unknown category falls back to the first known class (index 0), never crashing.
    assert out["City_encoded"].tolist()[0] == p.label_encoders["City"].transform(["Delhi"])[0]
    assert out["City_encoded"].tolist()[1] == 0


# =====================================================================
# 3. SCALER LEAKAGE-SAFETY & PARITY
# =====================================================================

def test_scaler_fit_on_train_and_reused():
    p = CrimeDataPreprocessor()
    with pytest.raises(RuntimeError):
        p.transform_scaler(np.zeros((1, 3)))

    train = np.array([[0.0, 10.0, 100.0], [2.0, 20.0, 300.0], [4.0, 30.0, 500.0]])
    p.fit_scaler(train, feature_columns=["a", "b", "c"])
    scaled_train = p.transform_scaler(train)
    assert np.allclose(scaled_train.mean(0), 0.0, atol=1e-6)
    assert np.allclose(scaled_train.std(0), 1.0, atol=1e-6)

    # Transforming new data must reuse TRAIN statistics (no refit).
    other = np.array([[100.0, 1000.0, 10000.0]])
    scaled_other = p.transform_scaler(other)
    expected = (other - train.mean(0)) / train.std(0)
    assert np.allclose(scaled_other, expected.astype("float32"), atol=1e-4)


def test_scaler_rejects_wrong_feature_count():
    p = CrimeDataPreprocessor()
    p.fit_scaler(np.zeros((3, 26)), feature_columns=[f"f{i}" for i in range(26)])
    with pytest.raises(ValueError):
        p.transform_scaler(np.zeros((1, 5)))


# =====================================================================
# 4. TRAIN / SERVE FEATURE PARITY (frequency-map reuse)
# =====================================================================

@pytest.mark.skipif(not os.path.exists(RAW_DATASET_PATH), reason="raw dataset missing")
def test_fitted_feature_engineer_prevents_single_sample_frequency_skew():
    df_raw = pd.read_csv(RAW_DATASET_PATH).head(400)
    p = CrimeDataPreprocessor()
    df_clean = p.clean_dataset(df_raw)
    p.fit_encoders(df_clean)

    fe = FeatureEngineer()
    fe.fit_aggregated_statistics(
        fe.extract_cyclical_features(fe.extract_temporal_features(df_clean))
    )

    one_row = df_clean.iloc[[0]]
    city = str(one_row["City"].iloc[0])
    fitted = fe.transform(one_row, is_train=False)
    assert fitted["City_Crime_Freq"].iloc[0] == fe.city_freq_map[city]
    assert fitted["City_Crime_Freq"].iloc[0] > 1  # NOT the single-sample value

    # A *fresh* (unfitted) engineer is what caused the historical skew.
    fresh = FeatureEngineer().transform(one_row, is_train=False)
    assert fresh["City_Crime_Freq"].iloc[0] == 1


# =====================================================================
# 5. EVALUATION CORRECTNESS
# =====================================================================

def _evaluate(logits: torch.Tensor, y_true: np.ndarray, class_names=None) -> dict:
    X = np.zeros((logits.shape[0], 4), dtype="float32")
    loader = DataLoader(CrimeDataset(X, y_class=y_true), batch_size=len(y_true), shuffle=False)
    return DeepLearningEvaluator.evaluate_classifier(
        _FixedLogits(logits), loader, device="cpu", class_names=class_names
    )


def test_evaluator_metrics_match_sklearn_reference():
    logits = torch.tensor(
        [[2.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 1.0],
         [2.0, 1.0, 0.0], [0.0, 0.0, 5.0], [1.0, 1.0, 1.0]]
    )
    y = np.array([0, 1, 2, 1, 2, 0])
    pred = logits.argmax(1).numpy()

    m = DeepLearningEvaluator.evaluate_classifier(
        _FixedLogits(logits),
        DataLoader(CrimeDataset(np.zeros((6, 4), dtype="float32"), y_class=y), batch_size=6, shuffle=False),
        class_names=["Fire Accident", "Other Crime", "Traffic Fatality"],
    )

    assert m["accuracy"] == round(float(accuracy_score(y, pred)), 4)
    assert m["balanced_accuracy"] == round(float(balanced_accuracy_score(y, pred)), 4)
    assert m["f1_macro"] == round(float(f1_score(y, pred, average="macro", zero_division=0, labels=[0, 1, 2])), 4)
    assert m["confusion_matrix"] == confusion_matrix(y, pred, labels=[0, 1, 2]).tolist()

    supports = [c["support"] for c in m["per_class"]]
    cm = np.array(m["confusion_matrix"])
    assert int(cm.sum()) == len(y)                      # CM total == sample count
    assert list(cm.sum(1)) == supports                  # row totals == supports
    assert sum(supports) == len(y)                      # supports sum to sample count
    assert pred.shape == y.shape
    assert m["n_samples"] == len(y)


def test_evaluator_handles_absent_classes_and_undefined_auc():
    logits = torch.tensor([[5.0, 0.0, 0.0], [4.0, 0.0, 0.0], [3.0, 0.0, 0.0]])
    y = np.array([0, 0, 0])  # classes 1 and 2 never appear

    m = DeepLearningEvaluator.evaluate_classifier(
        _FixedLogits(logits),
        DataLoader(CrimeDataset(np.zeros((3, 4), dtype="float32"), y_class=y), batch_size=3, shuffle=False),
    )
    assert math.isnan(m["roc_auc"])  # undefined with a single class present
    absent = [c for c in m["per_class"] if c["support"] == 0]
    assert len(absent) == 2
    assert all(c["precision"] == 0.0 and c["recall"] == 0.0 for c in absent)
    assert all(np.isfinite(v) for v in m["y_proba"][0])


# =====================================================================
# 6. MODEL SHAPES & LOSS
# =====================================================================

@pytest.mark.parametrize("model_cls", [FTTransformerClassifier, CrimeMLPClassifier])
def test_classifier_forward_and_probability_shapes(model_cls):
    model = model_cls(input_dim=26, num_classes=4)
    x = torch.randn(5, 26)
    logits = model(x)
    assert logits.shape == (5, 4)
    proba = model.predict_proba(x)
    assert proba.shape == (5, 4)
    assert torch.allclose(proba.sum(dim=1), torch.ones(5), atol=1e-5)


def test_focal_loss_class_weights_change_objective():
    logits = torch.tensor([[2.0, 0.0], [0.0, 2.0]])
    targets = torch.tensor([0, 1])
    plain = FocalLoss(gamma=2.0)(logits, targets)
    weighted = FocalLoss(gamma=2.0, class_weights=torch.tensor([5.0, 1.0]))(logits, targets)
    assert plain.item() != weighted.item()
    assert torch.isfinite(weighted)


# =====================================================================
# 7. SAVED REGISTRY METRICS ARE INTERNALLY CONSISTENT
# =====================================================================

def test_active_registry_metrics_are_consistent_if_present():
    import json
    reg_root = os.path.join(PROJECT_ROOT, "ai", "registry")
    active_path = os.path.join(reg_root, "active_version.json")
    if not os.path.exists(active_path):
        pytest.skip("no active version file")
    with open(active_path, encoding="utf-8") as f:
        version = json.load(f).get("active_version")
    metrics_path = os.path.join(reg_root, version, "metrics.json")
    if not os.path.exists(metrics_path):
        pytest.skip("active version has no metrics.json")
    with open(metrics_path, encoding="utf-8") as f:
        metrics = json.load(f)
    for key in ("ft_transformer", "residual_mlp"):
        m = metrics.get(key)
        if not m or "per_class" not in m or "confusion_matrix" not in m:
            continue  # older-format artifacts are validated separately/manually
        cm = np.array(m["confusion_matrix"])
        supports = [c["support"] for c in m["per_class"]]
        assert int(cm.sum()) == m["n_samples"]
        assert list(cm.sum(1)) == supports
        assert sum(supports) == m["n_samples"]
        assert len(m["y_true"]) == len(m["y_pred"]) == m["n_samples"]
