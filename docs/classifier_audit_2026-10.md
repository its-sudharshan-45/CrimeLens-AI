# CrimeLens AI — Classifier Audit (2026-10)

> **Status (historical record).** This document preserves the 2026-10 audit of the legacy
> crime-domain *classification* pipeline. That pipeline (FT-Transformer, residual MLP, ensemble,
> N-BEATS, LSTM, CNN-hotspot and embedding models) was subsequently **removed from the active
> codebase and archived** under `archive/legacy_classifier_2026-10/`. CrimeLens AI now ships a
> **single** working model — a GRU crime-count forecaster (`ai/forecasting/`). The analysis below
> is retained as evidence of why the classification capability was retired and is **not** a
> description of the current system.

**Scope:** `FTTransformerClassifier` + `CrimeMLPClassifier` crime-domain classification pipeline
(raw data → preprocessing → features → label encoding → training → checkpoint → loading →
inference → evaluation → API → frontend).

**Outcome:** the pipeline is now leakage-free, reproducible and honestly evaluated. The central
finding is that **the `Crime Domain` target is not demonstrably predictable from the available
features**, so the correct, defensible result is accuracy equal to the majority-class baseline.
No metric in this report is fabricated; every number is produced from code in this repository or
from an explicit, reproducible probe.

---

## 1. Target and data (verified, unchanged)

| Property | Value |
|---|---|
| Dataset | `Dataset/crime_dataset_india.csv` — 40,160 rows × 14 columns |
| Task | 4-class multiclass (`Crime Domain_encoded`) |
| Classes (encoder order) | `['Fire Accident', 'Other Crime', 'Traffic Fatality', 'Violent Crime']` → 0..3 |
| Class counts | Fire Accident 3,825 · Other Crime 22,948 · Traffic Fatality 1,915 · Violent Crime 11,472 |
| Majority class | Other Crime (57.15%) |
| Features | 26 (see §4) |

`Crime Description` (21 values) maps **deterministically** to `Crime Domain` (4 values): 0 of 21
descriptions map to more than one domain.

---

## 2. Baseline reproduction (the deployed `v1.0.0`)

Independently rebuilding the feature matrix and loading the **registry checkpoints**:

- Both `FTTransformerClassifier` and `CrimeMLPClassifier` predicted **class 1 for all 40,160 rows**.
- Confusion matrix exactly `[[0,383,0,0],[0,2295,0,0],[0,191,0,0],[0,1147,0,0]]` → accuracy 0.5715.
- ROC-AUC 0.4963 (≈ random), Cohen κ 0.0, MCC 0.0.
- `ai/artifacts/reports/cross_validation_report.json`: 5 folds all **0.5714 ± 0.0001** (systematic).
- `ai/registry/training_logs/experiment_history.json`: train/val accuracy **flat at 0.5714 from epoch 1**.

> **Reproducibility caveat:** there was **no training script, no saved split and no recorded seed**,
> so the exact 4,016 test indices are not recoverable (brute-forced `train_test_split`/`StratifiedKFold`
> across 20,000 seeds — no match). Because prediction was *constant*, any stratified 10% split
> reproduces the reported metric and matrix exactly. This gap is now closed (§5).

---

## 3. Root causes

### R1 — Target leakage via `Category_Freq` (the only source of > majority accuracy)
`Category_Freq` was the frequency of `Crime Description` fitted on the training set. Because
description → domain is deterministic and near-injective, the frequency leaked the target.

| Evidence | Value |
|---|---|
| Mutual information (`Category_Freq` → domain) | **0.9833** |
| Mutual information (every other feature → domain) | **≤ 0.0079** |
| `Category_Freq` alone, held-out accuracy | **0.9547** (macro-F1 0.9689) |
| Any other single feature | 0.5715 (majority) |

The only way to exceed the majority baseline on this target is through the leak.

### R2 — No feature scaling (confounder of the historical collapse)
`preprocessor.scaler` was never fitted or applied. Feature magnitudes reached ~6,139
(`State_Crime_Freq`), ~3,523 (`City_Crime_Freq`), ~2,021 (`Year`) versus ±1 for cyclical features.
Controlled experiment (identical split, seed 0, Residual MLP):

| Features | Accuracy | Macro-F1 | Predicted distribution |
|---|---|---|---|
| raw (as historically trained) | **0.5715** | 0.1818 | `[0, 4016, 0, 0]` (collapse) |
| standardized | 0.8010 | 0.7304 | `[457, 2252, 124, 1183]` (learns) |

Missing scaling was a genuine training bug; it is fixed (scaler fitted on train only).

### R3 — No reproducible training
`DeepLearningTrainer.train_classifier` had **no caller** anywhere in the repo; no seed, split or
config matched the checkpoint.

### R4 — Feature-schema drift
Code emitted 27 features (`Day_of_Week`, `Week_of_Year`, `Category_Freq`); `ai/models/feature_columns.json`
said 27; the deployed registry schema/checkpoints expected 26 (`Weekday`). `ai/models/ft_transformer.pt`
was a **byte-identical copy of the MLP** (mislabeled).

### R5 — Train/serve skew at inference
`model_loader.prepare_sample_tensor` created a **fresh** `FeatureEngineer`, so `transform(is_train=False)`
re-fitted the frequency maps on the single incoming row → `City_Crime_Freq = State_Crime_Freq = 1`
versus hundreds/thousands at training time. The deployed model received out-of-distribution inputs.

### R6 — Inconsistent metadata / artifacts
`training_config.json` (d_token 64 / 8 heads / 3 layers) disagreed with the actual checkpoint
(32 / 4 / 2); `training_statistics.json` listed non-existent domains ("Property/Cyber/White Collar
Crime") and features; `metrics.json` and `ft_transformer.pt` were duplicated.

### R7 — Fabricated frontend metrics
`frontend/src/services/evaluationService.ts` hardcoded accuracy **0.942**, a 6-class confusion matrix
(`Theft/Assault/…`, not in the dataset) and `Math.random()` training curves; `AuthLayout.tsx`
advertised "94.7% accuracy". The cluster (`evaluationService.ts` + `useEvaluation.ts` +
`types/evaluation.ts`) was **dead code** (no consumers).

---

## 4. Is the target learnable? (leak-free, cross-validated probe)

`HistGradientBoostingClassifier`, 3-fold CV, 12,000-row subsample, leak-free 26 features:

| Target | Majority baseline | Model accuracy | Balanced accuracy | Macro-F1 |
|---|---|---|---|---|
| **Crime Domain** (current) | 0.5665 | **0.5293 ± 0.0034** | **0.2496 ≈ chance (0.25)** | 0.2169 |
| **Case Closed** (alternative) | 0.5067 | **0.5062 ± 0.0069** | **0.5060 ≈ chance (0.50)** | 0.5058 |

**Both available targets are unlearnable from the feature set.** The classification component cannot
be presented as a predictive capability on this dataset without a different label or richer features.

---

## 5. Corrections implemented

1. **Leakage removed.** `Category_Freq` (and `category_freq_map`) deleted from the feature schema and
   from `FeatureEngineer`. The canonical 26-feature schema is unchanged otherwise.
2. **Scaling fixed.** `CrimeDataPreprocessor.fit_scaler` / `transform_scaler`; the `StandardScaler` is
   fitted on the **training split only** and applied identically at inference (train/serve parity).
3. **Train/serve skew fixed.** A fitted `FeatureEngineer` is persisted (`feature_engineer.pkl`) and
   loaded at inference, so training-time frequency maps are reused (verified: `City_Crime_Freq = 3523`,
   not 1). `model_loader` and `ai/inference/predict.py` both use it.
4. **Schema unified.** Registry `feature_columns.json`, loader fallback and `ai/models` now agree on 26.
5. **Reproducible training + evaluation.** New `ai/training/train_classifier.py`:
   deterministic seed, **stratified 80/10/10** split (incidents are independent records) with saved
   indices, train-only fitting of encoders/statistics/scaler, early stopping on validation, and a
   persisted `split_indices.json` + dataset hash + class mapping.
6. **Honest evaluation.** `DeepLearningEvaluator.evaluate_classifier` now reports balanced accuracy,
   macro & weighted precision/recall/F1, per-class metrics with support, log-loss, explicit class
   order and a confusion matrix — all computed from raw predictions; undefined metrics (e.g. ROC-AUC
   when a class is absent) are returned as `NaN` rather than silently coerced.
7. **Majority baseline reported.** Every run emits the majority-class baseline for direct comparison.
8. **Class weighting is opt-in.** Inverse-frequency weights (via `FocalLoss(class_weights=...)`) are
   available but **off by default**: with no measurable signal, weighting only trades accuracy for
   minority recall without adding skill (observed: accuracy fell to ~0.09).
9. **Dynamic registry versioning.** The backend now resolves the active version from
   `active_version.json` (previously hardcoded to `v1.0.0`); `System Health` reports the real active
   version; `switch_version` writes the active version before reloading and passes the target dir.
10. **Fabricated frontend data removed.** Deleted the dead `evaluationService.ts` / `useEvaluation.ts`
    / `types/evaluation.ts` cluster and corrected the "94.7% accuracy" claim.
11. **Metadata fixed.** New `v1.0.1` metadata is consistent (architecture, schema, seed, split, hash);
    the mislabeled `ai/models/ft_transformer.pt` duplicate was replaced; the bloated
    `registry_index.json` was slimmed (~96k lines → 12 KB).

---

## 6. Retrained `v1.0.1` — honest held-out metrics

Leakage-free 26 features · `StandardScaler` (train-only) · stratified 80/10/10 · seed 42 ·
test n = 4,016 · unweighted FocalLoss(γ=2) · early stopping on validation. `v1.0.0` is preserved as
archived history; `active_version.json` → `v1.0.1`.

| Metric | FT-Transformer | Residual MLP | Majority baseline |
|---|---|---|---|
| Accuracy | 0.5715 | 0.5715 | **0.5715** |
| Balanced accuracy | 0.2500 | 0.2500 | 0.2500 |
| Precision (weighted) | 0.3266 | 0.3266 | — |
| Recall (weighted) | 0.5715 | 0.5715 | — |
| F1 (weighted) | 0.4156 | 0.4156 | — |
| F1 (macro) | 0.1818 | 0.1818 | — |
| ROC-AUC (weighted OVR) | 0.4928 | 0.5027 | — |
| PR-AUC (macro) | 0.2466 | 0.2508 | — |
| Log loss | 1.0747 | 1.0769 | — |
| Cohen κ / MCC | 0.0000 / 0.0000 | 0.0000 / 0.0000 | — |

**Interpretation.** Both architectures converge to the majority-class predictor, which is the
Bayes-optimal decision rule for an uninformative feature set. The earlier "degenerate confusion
matrix" was therefore **the mathematically correct outcome for this target**, not merely a bug —
though it *was* also masked by a real scaling defect. Accuracy here is **not** a measure of model
skill; it is a property of the class prior. Balanced accuracy and macro-F1 confirm no signal.

---

## 7. Known limitations / follow-ups

- **Target redefinition is required** before classification performance is presented as a capability.
  Neither `Crime Domain` nor `Case Closed` is predictable from the current features.
- **`Crime Description` → `Crime Domain`** is a deterministic lookup, not a learned mapping; if that
  mapping is wanted in-product it should be an explicit rule, not a "model".
- **The embedding network** (`embedding_model.pt`) was trained under the pre-audit feature semantics
  and scaled-feature assumption; it was preserved unchanged and **should be retrained** for parity.
- The exact historical `v1.0.0` test split remains unrecoverable (documented above); `v1.0.1` is fully
  reproducible.

---

## 8. Reproducing this work

```powershell
# Retrain + re-evaluate (writes a new registry version and updates active_version.json)
.venv\Scripts\python.exe -m ai.training.train_classifier --version v1.0.1

# Tests
.venv\Scripts\python.exe -m pytest ai/tests/ -q
.venv\Scripts\python.exe -m pytest backend/tests/ -q
```

Artifacts of this audit: `ai/registry/v1.0.1/` (checkpoints, `preprocessor.pkl` incl. fitted scaler,
`feature_engineer.pkl`, `feature_columns.json`, `metrics.json`, `training_config.json`,
`model_metadata.json`, `split_indices.json`, `training_statistics.json`), and the regression suite
`ai/tests/test_classifier_audit.py`.

### Verification performed

- `ai/tests/` — **44 passed** (including 12 new regression tests: leakage-free schema, label-encoder
  round-trip, scaler leakage-safety, train/serve frequency parity, metric agreement with scikit-learn,
  absent-class/NaN handling, model shapes, loss behaviour, and registry-metric consistency).
- `backend/tests/` — **117 passed** (was 116; includes a new cross-version switch round-trip test).
- Frontend — `npm run build` succeeded; `npm run test` (Vitest) passed.
- End-to-end inference verified against `v1.0.1`: `registry_dir = ai/registry/v1.0.1`,
  `feature_columns = 26`, scaler fitted, `feature_engineer` loaded fitted, and a sample record yields
  `City_Crime_Freq = 3523` / `State_Crime_Freq = 7579` (not the historical `1`).
- Test runs leave `active_version.json` unchanged (`v1.0.1`).
