"""
ai/training/train_classifier.py
===============================
Reproducible Crime Domain classifier training & evaluation pipeline.

Created during the 2026-10 classifier audit to close a critical reproducibility
gap: the previously deployed artifacts (``ai/registry/v1.0.0``) had **no**
training script, **no** saved split indices, and **no** recorded seed, so the
reported metrics could not be reproduced from the repository. The deployed
models also collapsed to the majority class because features were never scaled.

This module trains the FT-Transformer and the Residual MLP on a leakage-safe,
standardized feature set and evaluates them on a held-out stratified test split.

Leakage & correctness controls
------------------------------
* ``Category_Freq`` (a deterministic leak of the ``Crime Domain`` target through
  ``Crime Description``) is **not** part of the feature schema.
* Feature-engineering statistics, label encoders and the ``StandardScaler`` are
  fitted on the **training split only**.
* The test split is never used for model selection (validation is used).
* The random seed, split indices, feature schema, class mapping and dataset hash
  are persisted alongside the checkpoints.

Usage
-----
    python -m ai.training.train_classifier --version v1.1.0 --epochs 25

The default target version is a *new* directory; existing versions are never
overwritten unless ``--allow-overwrite`` is passed.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
import torch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.dataset.crime_dataset import CrimeDataModule  # noqa: E402
from ai.evaluation.evaluator import DeepLearningEvaluator  # noqa: E402
from ai.models.ft_transformer import FTTransformerClassifier  # noqa: E402
from ai.models.mlp_classifier import CrimeMLPClassifier  # noqa: E402
from ai.preprocessing.feature_engineering import FeatureEngineer  # noqa: E402
from ai.preprocessing.preprocessor import CrimeDataPreprocessor  # noqa: E402
from ai.registry.model_registry import compute_file_hash  # noqa: E402
from ai.training.trainer import DeepLearningTrainer  # noqa: E402

DATASET_PATH = os.path.join(PROJECT_ROOT, "Dataset", "crime_dataset_india.csv")
REGISTRY_DIR = os.path.join(PROJECT_ROOT, "ai", "registry")
MODELS_DIR = os.path.join(PROJECT_ROOT, "ai", "models")

DEFAULT_SEED = 42
TEST_FRACTION = 0.10
VAL_FRACTION = 0.10  # of the full dataset

# Class-definition files copied into the version directory so the backend can
# dynamically import them (mirrors how v1.0.0 was assembled).
MODEL_CLASS_FILES = [
    "ft_transformer.py",
    "mlp_classifier.py",
    "ensemble_classifier.py",
    "nbeats_forecaster.py",
    "embedding_network.py",
    "lstm_forecaster.py",
]


def set_seed(seed: int) -> None:
    """Make training as deterministic as PyTorch/sklearn allow on CPU."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():  # pragma: no cover - CPU-only in CI
        torch.cuda.manual_seed_all(seed)


def stratified_split(
    y: np.ndarray, seed: int, test_fraction: float, val_fraction: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return deterministic stratified train/val/test index arrays.

    Incidents in this dataset are independent records (no repeated entity), so a
    stratified random split is statistically appropriate; grouping is not needed.
    Indices are returned (not data) so the exact split can be persisted/replayed.
    """
    from sklearn.model_selection import train_test_split

    idx = np.arange(len(y))
    train_val_idx, test_idx = train_test_split(
        idx, test_size=test_fraction, stratify=y, random_state=seed
    )
    val_relative = val_fraction / (1.0 - test_fraction)
    train_idx, val_idx = train_test_split(
        train_val_idx, test_size=val_relative, stratify=y[train_val_idx], random_state=seed
    )
    return np.sort(train_idx), np.sort(val_idx), np.sort(test_idx)


def build_features(
    df_raw: pd.DataFrame, train_idx: np.ndarray, seed: int
) -> Tuple[pd.DataFrame, np.ndarray, List[str], CrimeDataPreprocessor, FeatureEngineer, np.ndarray]:
    """Build the leakage-safe, standardized feature matrix.

    Returns ``(X_scaled, y, feature_columns, preprocessor, feature_engineer, y_all)``.
    """
    preprocessor = CrimeDataPreprocessor()
    df_clean = preprocessor.clean_dataset(df_raw)
    df_train = df_clean.iloc[train_idx]

    # 1. Fit encoders on the training split only.
    preprocessor.fit_encoders(df_train)

    # 2. Fit feature-engineering statistics on the training split only.
    feature_engineer = FeatureEngineer()
    feature_engineer.fit_aggregated_statistics(
        feature_engineer.extract_cyclical_features(feature_engineer.extract_temporal_features(df_train))
    )

    # 3. Apply to the full dataset (no refit).
    df_feats = feature_engineer.transform(df_clean, is_train=False)
    df_encoded = preprocessor.transform_encoders(df_feats)

    X, y, feature_cols = feature_engineer.get_feature_matrix(df_encoded, target_type="classification")
    if y is None:
        raise RuntimeError("Classification target 'Crime Domain_encoded' not found.")
    X = X[feature_cols]  # enforce canonical order

    # 4. Fit the scaler on the TRAINING rows only, then transform everything.
    X_train_raw = X.iloc[train_idx].to_numpy(dtype="float64")
    preprocessor.fit_scaler(X_train_raw, feature_columns=feature_cols)
    X_scaled = preprocessor.transform_scaler(X.to_numpy(dtype="float64"))

    preprocessor.feature_columns = list(feature_cols)
    return X_scaled, np.asarray(y), feature_cols, preprocessor, feature_engineer, np.asarray(y)


def class_weights_tensor(y_train: np.ndarray, num_classes: int) -> torch.Tensor:
    """Inverse-frequency class weights for imbalanced classification."""
    from sklearn.utils.class_weight import compute_class_weight

    weights = compute_class_weight(
        class_weight="balanced", classes=np.arange(num_classes), y=y_train
    )
    return torch.tensor(weights, dtype=torch.float32)


def _load_registry_index() -> Dict[str, Any]:
    path = os.path.join(REGISTRY_DIR, "registry_index.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"versions": []}


def _slim(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Drop large per-sample arrays before storing metrics in the registry index."""
    heavy = {"y_true", "y_pred", "y_proba"}
    out: Dict[str, Any] = {}
    for name, m in metrics.items():
        if isinstance(m, dict):
            out[name] = {k: v for k, v in m.items() if k not in heavy}
        else:
            out[name] = m
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Train CrimeLens Crime Domain classifiers.")
    parser.add_argument("--version", default="v1.1.0", help="New registry version directory.")
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--allow-overwrite", action="store_true")
    parser.add_argument(
        "--class-weights",
        action="store_true",
        help=(
            "Use inverse-frequency class weights. NOTE: with the leakage-free "
            "feature set there is no measurable signal, so weighting trades accuracy "
            "for minority recall without adding real skill; it is disabled by default."
        ),
    )
    args = parser.parse_args()

    set_seed(args.seed)
    version_dir = os.path.join(REGISTRY_DIR, args.version)
    if os.path.exists(version_dir) and not args.allow_overwrite:
        print(f"ERROR: {version_dir} already exists. Pass --allow-overwrite to replace.")
        return 2
    os.makedirs(version_dir, exist_ok=True)

    print(f"[pipeline] Loading dataset from {DATASET_PATH}")
    df_raw = pd.read_csv(DATASET_PATH)
    print(f"[pipeline] Raw shape: {df_raw.shape}")

    # Provisional split needs y only -> reuse a first pass to obtain labels.
    tmp_pre = CrimeDataPreprocessor()
    df_clean = tmp_pre.clean_dataset(df_raw)
    y_provisional = (
        pd.factorize(df_clean["Crime Domain"])[0]
    )  # stable split stratification (order irrelevant for counts)
    train_idx, val_idx, test_idx = stratified_split(
        y_provisional, args.seed, TEST_FRACTION, VAL_FRACTION
    )
    print(
        f"[pipeline] Split: train={len(train_idx)} val={len(val_idx)} test={len(test_idx)} "
        f"(seed={args.seed}, stratified)"
    )

    X, y, feature_cols, preprocessor, feature_engineer, _ = build_features(df_raw, train_idx, args.seed)
    num_classes = len(preprocessor.label_encoders["Crime Domain"].classes_)
    class_names = [str(c) for c in preprocessor.label_encoders["Crime Domain"].classes_]
    print(f"[pipeline] Features ({len(feature_cols)}): {feature_cols}")
    print(f"[pipeline] Classes ({num_classes}): {class_names}")

    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    X_test, y_test = X[test_idx], y[test_idx]

    dm = CrimeDataModule(batch_size=args.batch_size)
    train_loader, val_loader, test_loader = dm.get_dataloaders(
        X_train, y_train, X_val, y_val, X_test, y_test
    )

    weights = class_weights_tensor(y_train, num_classes) if args.class_weights else None
    print(f"[pipeline] Class weights: {weights.tolist() if weights is not None else 'disabled (unweighted)'}")

    trainer = DeepLearningTrainer(tensorboard_dir=os.path.join(PROJECT_ROOT, "ai", "tensorboard"))
    evaluator = DeepLearningEvaluator()

    histories: Dict[str, Any] = {}
    metrics: Dict[str, Any] = {}
    models: Dict[str, torch.nn.Module] = {}

    # ── FT-Transformer ────────────────────────────────────────────────────
    print("\n[pipeline] Training FTTransformerClassifier ...")
    set_seed(args.seed)
    ft_model = FTTransformerClassifier(input_dim=len(feature_cols), num_classes=num_classes)
    histories["ft_transformer"] = trainer.train_classifier(
        ft_model, train_loader, val_loader,
        epochs=args.epochs, lr=args.lr, use_focal_loss=True,
        patience=args.patience, model_name="FTTransformerClassifier",
        class_weights=weights,
    )
    metrics["ft_transformer"] = evaluator.evaluate_classifier(
        ft_model, test_loader, class_names=class_names, model_name="FTTransformerClassifier"
    )
    models["ft_transformer"] = ft_model

    # ── Residual MLP ──────────────────────────────────────────────────────
    print("\n[pipeline] Training CrimeMLPClassifier ...")
    set_seed(args.seed)
    mlp_model = CrimeMLPClassifier(input_dim=len(feature_cols), num_classes=num_classes)
    histories["residual_mlp"] = trainer.train_classifier(
        mlp_model, train_loader, val_loader,
        epochs=args.epochs, lr=args.lr, use_focal_loss=True,
        patience=args.patience, model_name="ResidualMLPClassifier",
        class_weights=weights,
    )
    metrics["residual_mlp"] = evaluator.evaluate_classifier(
        mlp_model, test_loader, class_names=class_names, model_name="ResidualMLPClassifier"
    )
    models["residual_mlp"] = mlp_model
    trainer.close()

    # ── Baseline reference (majority-class predictor) ─────────────────────
    majority = int(np.bincount(y_train, minlength=num_classes).argmax())
    majority_acc = float(np.mean(y_test == majority))
    metrics["majority_baseline"] = {
        "model_name": "MajorityClassBaseline",
        "majority_class_index": majority,
        "majority_class_name": class_names[majority],
        "accuracy": round(majority_acc, 4),
        "n_samples": int(len(y_test)),
    }
    print(
        f"\n[pipeline] Majority-class baseline: {class_names[majority]} "
        f"-> accuracy {majority_acc:.4f}"
    )
    print(
        "[pipeline] NOTE: if a model's accuracy does not exceed this baseline, "
        "the target is not demonstrably predictable from the feature set."
    )

    # ── Persist artifacts ─────────────────────────────────────────────────
    print(f"\n[pipeline] Saving artifacts to {version_dir}")
    for fname in MODEL_CLASS_FILES:
        src = os.path.join(MODELS_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(version_dir, fname))

    torch.save(ft_model.state_dict(), os.path.join(version_dir, "ft_transformer.pt"))
    torch.save(mlp_model.state_dict(), os.path.join(version_dir, "crime_classifier.pt"))
    torch.save(
        {
            "ft_transformer_state": ft_model.state_dict(),
            "mlp_state": mlp_model.state_dict(),
        },
        os.path.join(version_dir, "checkpoint.pt"),
    )

    # Preserve unchanged forecaster / embedding artifacts.
    for src, dst in [
        (os.path.join(MODELS_DIR, "forecast_model.pt"), "forecast_model.pt"),
        (os.path.join(REGISTRY_DIR, "v1.0.0", "embedding_model.pt"), "embedding_model.pt"),
    ]:
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(version_dir, dst))

    joblib.dump(preprocessor, os.path.join(version_dir, "preprocessor.pkl"))
    joblib.dump(feature_engineer, os.path.join(version_dir, "feature_engineer.pkl"))

    split_payload = {
        "seed": args.seed,
        "test_fraction": TEST_FRACTION,
        "val_fraction": VAL_FRACTION,
        "stratified": True,
        "train_idx": train_idx.tolist(),
        "val_idx": val_idx.tolist(),
        "test_idx": test_idx.tolist(),
    }
    with open(os.path.join(version_dir, "split_indices.json"), "w", encoding="utf-8") as f:
        json.dump(split_payload, f)

    schema = {
        "feature_columns": feature_cols,
        "input_dim": len(feature_cols),
        "target_column": "Crime Domain_encoded",
        "domain_classes": class_names,
        "description_classes": [str(c) for c in preprocessor.label_encoders["Crime Description"].classes_],
        "scaler": "StandardScaler (fitted on training split only)",
        "leakage_note": (
            "Category_Freq removed: Crime Description deterministically maps to "
            "Crime Domain, so its frequency leaked the target."
        ),
    }
    with open(os.path.join(version_dir, "feature_columns.json"), "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=4)

    training_config = {
        "input_dim": len(feature_cols),
        "num_classes": num_classes,
        "d_token": 32,
        "n_heads": 4,
        "n_layers": 2,
        "batch_size": args.batch_size,
        "optimizer": "AdamW",
        "scheduler": "CosineAnnealingLR",
        "loss_function": (
            "FocalLoss(gamma=2.0, class_weights=balanced)"
            if args.class_weights
            else "FocalLoss(gamma=2.0)"
        ),
        "class_weighting": bool(args.class_weights),
        "epochs": args.epochs,
        "patience": args.patience,
        "learning_rate": args.lr,
        "seed": args.seed,
        "split": "stratified 80/10/10 (train/val/test), seed-fixed, indices persisted",
        "feature_scaling": "StandardScaler fitted on training split only",
    }
    with open(os.path.join(version_dir, "training_config.json"), "w", encoding="utf-8") as f:
        json.dump(training_config, f, indent=4)

    with open(os.path.join(version_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4)

    with open(os.path.join(version_dir, "training_statistics.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "model_version": args.version,
                "dataset_hash_md5": compute_file_hash(DATASET_PATH),
                "generated_at": datetime.now(tz=timezone.utc).isoformat(),
                "feature_statistics": {
                    col: {
                        "mean": float(np.mean(X[:, i])),
                        "std": float(np.std(X[:, i])),
                        "min": float(np.min(X[:, i])),
                        "max": float(np.max(X[:, i])),
                    }
                    for i, col in enumerate(feature_cols)
                },
                "class_distribution": {
                    class_names[c]: int((y == c).sum()) for c in range(num_classes)
                },
            },
            f,
            indent=4,
        )

    metadata = {
        "version": args.version,
        "flagship_model": "FTTransformerClassifier",
        "forecaster_model": "NBEATSForecaster",
        "dataset_rows": int(len(df_raw)),
        "saved_at": datetime.now(tz=timezone.utc).isoformat(),
        "dataset_hash_md5": compute_file_hash(DATASET_PATH),
        "framework": f"PyTorch {torch.__version__}",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "seed": args.seed,
        "audit_note": (
            "Retrained 2026-10 classifier audit: leakage-free features, fitted "
            "StandardScaler, reproducible stratified split, comprehensive metrics."
        ),
    }
    with open(os.path.join(version_dir, "model_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)

    # ── Registry index + active version ───────────────────────────────────
    index = _load_registry_index()
    entry = {
        "model_version": args.version,
        "framework": f"PyTorch {torch.__version__}",
        "training_date": metadata["saved_at"],
        "dataset_version": metadata["dataset_hash_md5"],
        "metrics": _slim(metrics),
        "artifact_path": os.path.relpath(version_dir, PROJECT_ROOT),
    }
    index["versions"] = [v for v in index.get("versions", []) if v.get("model_version") != args.version]
    index["versions"].append(entry)
    with open(os.path.join(REGISTRY_DIR, "registry_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=4)

    with open(os.path.join(REGISTRY_DIR, "active_version.json"), "w", encoding="utf-8") as f:
        json.dump(
            {"active_version": args.version, "updated_at": datetime.now(tz=timezone.utc).isoformat()},
            f,
            indent=4,
        )
    print(f"[pipeline] Active version set to {args.version}")

    print("\n================ FINAL TEST METRICS ================")
    for key in ("ft_transformer", "residual_mlp"):
        m = metrics[key]
        print(
            f"{m['model_name']:22s} acc={m['accuracy']:.4f} bal_acc={m['balanced_accuracy']:.4f} "
            f"f1_w={m['f1_score']:.4f} f1_macro={m['f1_macro']:.4f} roc_auc={m['roc_auc']:.4f}"
        )
    print(f"majority baseline     acc={majority_acc:.4f}")
    print("====================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
