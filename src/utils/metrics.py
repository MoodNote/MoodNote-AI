"""
Evaluation metrics for emotion classification
"""

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)

from .emotion_constants import DEFAULT_EMOTION_LABELS
from .logger import get_logger

logger = get_logger("metrics")

EMOTION_LABELS = DEFAULT_EMOTION_LABELS.copy()

# Passed as `labels=` to every sklearn call below. Without it sklearn infers the class set
# from unique(y_true ∪ y_pred), so a class absent from an eval split silently drops out:
# per-class arrays get shorter (misaligning them with the label names), the confusion matrix
# shrinks, and f1_macro changes denominator between runs — which would make the ablation
# scenarios and seeds incomparable.
LABEL_IDS = sorted(EMOTION_LABELS)


def compute_metrics(predictions, labels):
    """
    Compute evaluation metrics

    Args:
        predictions: Model predictions (logits or class indices)
        labels: True labels

    Returns:
        dict: Dictionary containing metrics
    """
    # Convert predictions to class indices if needed
    if len(predictions.shape) > 1:
        preds = np.argmax(predictions, axis=1)
    else:
        preds = predictions

    # Overall metrics
    accuracy = accuracy_score(labels, preds)
    f1_macro = f1_score(labels, preds, labels=LABEL_IDS, average="macro", zero_division=0)
    f1_weighted = f1_score(labels, preds, labels=LABEL_IDS, average="weighted", zero_division=0)

    # Per-class metrics, one entry per LABEL_IDS entry even for classes absent from this split
    precision, recall, f1, support = (
        np.asarray(x)
        for x in precision_recall_fscore_support(
            labels, preds, labels=LABEL_IDS, average=None, zero_division=0
        )
    )

    # Create results dictionary
    metrics = {
        "accuracy": accuracy,
        "f1_macro": f1_macro,
        "f1_weighted": f1_weighted,
        "per_class": {
            "precision": precision.tolist(),
            "recall": recall.tolist(),
            "f1": f1.tolist(),
            "support": support.tolist(),
        },
    }

    return metrics


def print_metrics(metrics, emotion_labels=EMOTION_LABELS):
    """
    Print metrics in a readable format

    Args:
        metrics: Metrics dictionary from compute_metrics
        emotion_labels: Dictionary mapping label indices to names
    """
    print("\n" + "=" * 60)
    print("Evaluation Metrics")
    print("=" * 60)

    print("\nOverall Metrics:")
    print(f"  Accuracy:    {metrics['accuracy']:.4f}")
    print(f"  F1-Macro:    {metrics['f1_macro']:.4f}")
    print(f"  F1-Weighted: {metrics['f1_weighted']:.4f}")

    print("\nPer-Class Metrics:")
    print(f"{'Emotion':<15} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<10}")
    print("-" * 60)

    # strict=True: per-class arrays must line up with the label ids, or the printed
    # emotion names would be attached to another class's numbers.
    for idx, prec, rec, f1, sup in zip(
        sorted(emotion_labels),
        metrics["per_class"]["precision"],
        metrics["per_class"]["recall"],
        metrics["per_class"]["f1"],
        metrics["per_class"]["support"],
        strict=True,
    ):
        emotion = emotion_labels[idx]
        print(f"{emotion:<15} {prec:<12.4f} {rec:<12.4f} {f1:<12.4f} {int(sup):<10}")

    print("=" * 60 + "\n")


def get_classification_report(predictions, labels, emotion_labels=EMOTION_LABELS):
    """
    Get detailed classification report

    Args:
        predictions: Model predictions
        labels: True labels
        emotion_labels: Dictionary mapping label indices to names

    Returns:
        str: Classification report
    """
    # Convert predictions to class indices if needed
    if len(predictions.shape) > 1:
        preds = np.argmax(predictions, axis=1)
    else:
        preds = predictions

    # Get label ids and names in order
    label_ids = sorted(emotion_labels)
    label_names = [emotion_labels[i] for i in label_ids]

    # Generate report
    report = classification_report(
        labels, preds, labels=label_ids, target_names=label_names, digits=4, zero_division=0
    )

    return report


def plot_confusion_matrix(
    predictions, labels, emotion_labels=EMOTION_LABELS, save_path=None, figsize=(10, 8)
):
    """
    Plot confusion matrix

    Args:
        predictions: Model predictions
        labels: True labels
        emotion_labels: Dictionary mapping label indices to names
        save_path: Path to save the plot (optional)
        figsize: Figure size

    Returns:
        matplotlib.figure.Figure: The confusion matrix figure
    """
    # Imported here so the plotting stack stays optional for training/eval-only runs.
    import matplotlib.pyplot as plt
    import seaborn as sns

    # Convert predictions to class indices if needed
    if len(predictions.shape) > 1:
        preds = np.argmax(predictions, axis=1)
    else:
        preds = predictions

    # Get label ids and names in order
    label_ids = sorted(emotion_labels)
    label_names = [emotion_labels[i] for i in label_ids]

    # Compute confusion matrix, fixed at len(label_ids) x len(label_ids) so it matches the ticklabels
    cm = confusion_matrix(labels, preds, labels=label_ids)

    # Plot
    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=label_names,
        yticklabels=label_names,
        ax=ax,
        cbar_kws={"label": "Count"},
    )

    ax.set_xlabel("Predicted Label", fontsize=12)
    ax.set_ylabel("True Label", fontsize=12)
    ax.set_title("Confusion Matrix", fontsize=14, fontweight="bold")

    plt.tight_layout()

    # Save if path provided
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        logger.info(f"Confusion matrix saved to {save_path}")

    return fig


def compute_metrics_for_trainer(eval_pred):
    """
    Compute metrics for Hugging Face Trainer

    Args:
        eval_pred: EvalPrediction object with predictions and label_ids

    Returns:
        dict: Metrics dictionary
    """
    predictions, labels = eval_pred
    metrics = compute_metrics(predictions, labels)

    # Return only scalar metrics for Trainer
    return {
        "accuracy": metrics["accuracy"],
        "f1_macro": metrics["f1_macro"],
        "f1_weighted": metrics["f1_weighted"],
    }


if __name__ == "__main__":
    # Classes 4, 5 and 6 appear in neither y_true nor y_pred: without labels= sklearn drops
    # them, per_class comes back with 4 entries and classification_report raises.
    y_true = np.array([0, 0, 1, 1, 2, 3])
    y_pred = np.array([0, 1, 1, 1, 2, 3])

    result = compute_metrics(y_pred, y_true)
    assert len(result["per_class"]["f1"]) == len(EMOTION_LABELS), result["per_class"]
    assert result["per_class"]["support"][6] == 0, result["per_class"]["support"]

    report = get_classification_report(y_pred, y_true)
    assert "Other" in report, report

    print_metrics(result)
    print("metrics self-check OK")
