"""
Shared emotion label constants and normalization helpers.
"""
from typing import Any, Dict, Mapping, Optional


DEFAULT_EMOTION_LABELS: Dict[int, str] = {
    0: "Enjoyment",
    1: "Sadness",
    2: "Anger",
    3: "Fear",
    4: "Disgust",
    5: "Surprise",
    6: "Other",
}


DEFAULT_SENTIMENT_SCORES: Dict[str, float] = {
    "Enjoyment": 1.0,
    "Surprise": 0.3,
    "Other": 0.0,
    "Fear": -0.5,
    "Disgust": -0.7,
    "Sadness": -0.8,
    "Anger": -0.9,
}


def normalize_emotion_labels(emotion_labels: Optional[Mapping[Any, str]]) -> Dict[int, str]:
    """Return a normalized label mapping with integer keys."""
    if emotion_labels is None:
        return DEFAULT_EMOTION_LABELS.copy()
    return {int(k): str(v) for k, v in emotion_labels.items()}


def normalize_sentiment_scores(sentiment_scores: Optional[Mapping[str, float]]) -> Dict[str, float]:
    """Return a normalized sentiment-score mapping with float values."""
    if sentiment_scores is None:
        return DEFAULT_SENTIMENT_SCORES.copy()
    return {str(k): float(v) for k, v in sentiment_scores.items()}


def find_label_index_by_name(emotion_labels: Mapping[int, str], label_name: str) -> Optional[int]:
    """Find label index by case-insensitive label name."""
    target = label_name.strip().lower()
    for idx, label in emotion_labels.items():
        if str(label).strip().lower() == target:
            return int(idx)
    return None
