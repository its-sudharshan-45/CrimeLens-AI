import json
import logging
import os

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import auc, roc_curve

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = "ai/artifacts"

def generate_eda_plots(df: pd.DataFrame, output_dir: str = ARTIFACTS_DIR) -> dict:
    """Generates EDA plots for crime dataset."""
    os.makedirs(output_dir, exist_ok=True)
    sns.set_theme(style="darkgrid", palette="muted")
    eda_summary = {}

    # 1. Crime Distribution Plot
    logger.info("Generating crime_distribution.png...")
    plt.figure(figsize=(14, 6))
    
    plt.subplot(1, 2, 1)
    domain_counts = df["Crime Domain"].value_counts()
    sns.barplot(x=domain_counts.values, y=domain_counts.index, hue=domain_counts.index, palette="viridis", legend=False)
    plt.title("Distribution of Crime Domains", fontsize=14, fontweight="bold")
    plt.xlabel("Count")
    
    plt.subplot(1, 2, 2)
    top_crimes = df["Crime Description"].value_counts().head(10)
    sns.barplot(x=top_crimes.values, y=top_crimes.index, hue=top_crimes.index, palette="mako", legend=False)
    plt.title("Top 10 Crime Descriptions", fontsize=14, fontweight="bold")
    plt.xlabel("Count")
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "crime_distribution.png"), dpi=300)
    plt.close()
    eda_summary["domain_counts"] = domain_counts.to_dict()

    # 2. State & City Wise Crimes Plot
    logger.info("Generating state_wise_crimes.png...")
    plt.figure(figsize=(14, 6))
    
    plt.subplot(1, 2, 1)
    if "State" in df.columns:
        state_counts = df["State"].value_counts().head(12)
        sns.barplot(x=state_counts.values, y=state_counts.index, hue=state_counts.index, palette="rocket", legend=False)
        plt.title("Top States by Crime Volume", fontsize=14, fontweight="bold")
        plt.xlabel("Incident Count")
    
    plt.subplot(1, 2, 2)
    city_counts = df["City"].value_counts().head(12)
    sns.barplot(x=city_counts.values, y=city_counts.index, hue=city_counts.index, palette="flare", legend=False)
    plt.title("Top Cities by Crime Volume", fontsize=14, fontweight="bold")
    plt.xlabel("Incident Count")
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "state_wise_crimes.png"), dpi=300)
    plt.close()

    # 3. Category Analysis Plot
    logger.info("Generating category_analysis.png...")
    plt.figure(figsize=(12, 7))
    cat_domain_ct = pd.crosstab(df["Crime Description"], df["Crime Domain"])
    cat_domain_ct.plot(kind="barh", stacked=True, figsize=(12, 7), colormap="crest")
    plt.title("Crime Description Breakdown by Crime Domain", fontsize=14, fontweight="bold")
    plt.xlabel("Incident Count")
    plt.ylabel("Crime Description")
    plt.legend(title="Crime Domain")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "category_analysis.png"), dpi=300)
    plt.close()

    # 4. Monthly Trend Plot
    logger.info("Generating monthly_trend.png...")
    if "Date of Occurrence" in df.columns:
        plt.figure(figsize=(12, 5))
        df_dt = df.dropna(subset=["Date of Occurrence"]).copy()
        df_dt["YearMonth"] = pd.to_datetime(df_dt["Date of Occurrence"]).dt.strftime("%Y-%m")
        monthly_counts = df_dt.groupby("YearMonth").size()
        
        plt.plot(list(monthly_counts.index), list(monthly_counts.values), marker="o", color="#2b5c8f", linewidth=2.5)
        plt.title("Monthly Incident Volume (2020-2024)", fontsize=14, fontweight="bold")
        plt.xlabel("Year-Month")
        plt.ylabel("Crime Count")
        plt.xticks(rotation=45)
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "monthly_trend.png"), dpi=300)
        plt.close()

    # 5. Heatmaps Plot
    logger.info("Generating heatmaps.png...")
    if "Hour" in df.columns and "Weekday" in df.columns:
        plt.figure(figsize=(10, 6))
        weekday_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
        df_heatmap = df.copy()
        df_heatmap["Weekday_Name"] = df_heatmap["Weekday"].map(lambda w: weekday_map.get(w, ""))
        
        heatmap_pt = pd.crosstab(df_heatmap["Weekday_Name"], df_heatmap["Hour"])
        heatmap_pt = heatmap_pt.reindex(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        
        sns.heatmap(heatmap_pt, cmap="YlOrRd", annot=False, fmt="d", cbar_kws={'label': 'Incidents'})
        plt.title("Crime Incident Density: Day of Week vs Hour of Day", fontsize=14, fontweight="bold")
        plt.xlabel("Hour of Day (0-23)")
        plt.ylabel("Day of Week")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "heatmaps.png"), dpi=300)
        plt.close()

    # 6. Correlation Matrix Plot
    logger.info("Generating correlation_matrix.png...")
    plt.figure(figsize=(10, 8))
    num_cols = ["Victim Age", "Police Deployed", "Year", "Month", "Day", "Weekday", "Hour", "Reporting_Lag_Hours"]
    avail_num_cols = [c for c in num_cols if c in df.columns]
    
    if len(avail_num_cols) > 1:
        corr = df[avail_num_cols].corr(numeric_only=True)
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1)
        plt.title("Numerical Feature Correlation Matrix", fontsize=14, fontweight="bold")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "correlation_matrix.png"), dpi=300)
        plt.close()

    summary_path = os.path.join(output_dir, "eda_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(eda_summary, f, indent=4)

    return eda_summary

def plot_training_curves(history: dict, output_dir: str = ARTIFACTS_DIR):
    """Plot PyTorch training vs. validation loss and accuracy curves."""
    os.makedirs(output_dir, exist_ok=True)
    plt.figure(figsize=(12, 5))

    plt.subplot(1, 2, 1)
    plt.plot(history["train_loss"], label="Train Loss", color="#1f77b4", linewidth=2)
    plt.plot(history["val_loss"], label="Val Loss", color="#ff7f0e", linewidth=2)
    plt.title("PyTorch Training & Validation Loss", fontsize=12, fontweight="bold")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()

    if "train_acc" in history and "val_acc" in history:
        plt.subplot(1, 2, 2)
        plt.plot(history["train_acc"], label="Train Acc", color="#2ca02c", linewidth=2)
        plt.plot(history["val_acc"], label="Val Acc", color="#d62728", linewidth=2)
        plt.title("PyTorch Training & Validation Accuracy", fontsize=12, fontweight="bold")
        plt.xlabel("Epoch")
        plt.ylabel("Accuracy")
        plt.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "training_validation_curves.png"), dpi=300)
    plt.close()

def plot_confusion_matrix(cm: list, class_names: list, output_dir: str = ARTIFACTS_DIR):
    """Plot PyTorch MLP confusion matrix heatmap."""
    os.makedirs(output_dir, exist_ok=True)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=class_names, yticklabels=class_names)
    plt.title("PyTorch MLP Classifier Confusion Matrix", fontsize=14, fontweight="bold")
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "confusion_matrix.png"), dpi=300)
    plt.close()

def plot_roc_curve(y_true: np.ndarray, y_proba: np.ndarray, class_names: list, output_dir: str = ARTIFACTS_DIR):
    """Plot multi-class ROC curve for PyTorch classifier."""
    os.makedirs(output_dir, exist_ok=True)
    plt.figure(figsize=(8, 6))
    
    num_classes = len(class_names)
    y_true_onehot = np.eye(num_classes)[y_true]

    for i in range(num_classes):
        fpr, tpr, _ = roc_curve(y_true_onehot[:, i], y_proba[:, i])
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, label=f"{class_names[i]} (AUC = {roc_auc:.3f})")

    plt.plot([0, 1], [0, 1], "k--", label="Random Classifier")
    plt.title("PyTorch MLP Multi-Class ROC Curves", fontsize=14, fontweight="bold")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "roc_curve.png"), dpi=300)
    plt.close()

def plot_feature_importance_explainability(model, X_sample: np.ndarray, feature_names: list, device: str = "cpu", output_dir: str = ARTIFACTS_DIR):
    """Feature attribution explainability analysis using PyTorch Gradient Sensitivity."""
    os.makedirs(output_dir, exist_ok=True)
    import torch
    model = model.to(device)
    model.eval()

    x_tensor = torch.tensor(X_sample, dtype=torch.float32, requires_grad=True).to(device)
    outputs = model(x_tensor)
    
    # Compute gradient of top predicted class wrt input features
    top_logits = outputs.max(dim=1)[0]
    top_logits.sum().backward()

    if x_tensor.grad is not None:
        gradients = x_tensor.grad.abs().mean(dim=0).cpu().numpy()
    else:
        gradients = np.zeros(X_sample.shape[1], dtype=np.float32)
    
    # Sort feature importances
    sorted_idx = np.argsort(gradients)[::-1]
    top_features = [feature_names[i] for i in sorted_idx[:15]]
    top_scores = [float(gradients[i]) for i in sorted_idx[:15]]

    plt.figure(figsize=(10, 6))
    sns.barplot(x=top_scores, y=top_features, palette="mako")
    plt.title("PyTorch Neural Feature Attribution (Gradient Sensitivity Explainability)", fontsize=14, fontweight="bold")
    plt.xlabel("Mean Absolute Gradient Attribution")
    plt.ylabel("Feature")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "feature_importance_explainability.png"), dpi=300)
    plt.close()
