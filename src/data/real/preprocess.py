"""
Vietnamese word segmentation for PhoBERT and UIT-VSMEC preprocessing.
"""

from pathlib import Path

import pandas as pd
from pyvi import ViTokenizer

from ...utils.config import load_config
from ...utils.config_schema import ModelConfig
from ...utils.emotion_constants import DEFAULT_EMOTION_LABELS
from ...utils.logger import get_logger, setup_logger

logger = get_logger("preprocess")

SPLITS = ("train", "validation", "test")


class VietnamesePreprocessor:
    """Vietnamese text preprocessor with word segmentation"""

    def __init__(self, segmenter: str = "pyvi") -> None:
        if segmenter != "pyvi":
            raise ValueError(f"Unsupported segmenter: {segmenter}")
        self.segmenter = segmenter

    def preprocess_text(self, text: str, lowercase: bool = False) -> str:
        """
        Segment Vietnamese text into words (e.g. "hôm nay" -> "hôm_nay")

        Args:
            text: Input text
            lowercase: Whether to lowercase the text

        Returns:
            Preprocessed text
        """
        text = ViTokenizer.tokenize(text.strip())
        return text.lower() if lowercase else text


def preprocess_frame(
    df: pd.DataFrame,
    text_col: str,
    label_col: str,
    preprocessor: VietnamesePreprocessor,
    lowercase: bool = False,
) -> pd.DataFrame:
    """
    Segment texts and map emotion names to label ids.

    Args:
        df: Input DataFrame
        text_col: Column holding the raw text
        label_col: Column holding the emotion name (e.g. "Enjoyment")
        preprocessor: Preprocessor used for segmentation
        lowercase: Whether to lowercase the text

    Returns:
        DataFrame with columns `text` (segmented) and `label` (int)
    """
    label_ids = {name.lower(): idx for idx, name in DEFAULT_EMOTION_LABELS.items()}
    labels = df[label_col].str.strip().str.lower().map(label_ids)
    unknown = df.loc[labels.isna(), label_col].unique()
    if len(unknown):
        raise ValueError(f"Unknown emotion labels: {list(unknown)}")

    return pd.DataFrame(
        {
            "text": [preprocessor.preprocess_text(t, lowercase) for t in df[text_col].tolist()],
            "label": labels.astype(int),
        }
    )


def preprocess_vsmec(
    raw_dir: str = "data/real/raw",
    output_dir: str = "data/real/processed",
    config_path: str = "configs/model_config.yaml",
) -> None:
    """
    Preprocess the raw UIT-VSMEC splits into `text,label` CSV files.

    `test.csv` is the fixed benchmark for every ablation scenario and is written once:
    a re-run with identical output leaves it untouched, a differing output raises.

    Args:
        raw_dir: Directory containing the raw VSMEC CSV files
        output_dir: Directory to save the preprocessed CSV files
        config_path: Path to model config YAML (reads the `preprocessing` block)
    """
    config = ModelConfig(**load_config(config_path)).preprocessing
    preprocessor = VietnamesePreprocessor(segmenter=config.segmenter)
    logger.info(f"Segmenter: {config.segmenter}, lowercase: {config.lowercase}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for split in SPLITS:
        raw = pd.read_csv(Path(raw_dir) / f"{split}.csv")
        df = preprocess_frame(raw, "Sentence", "Emotion", preprocessor, config.lowercase)
        output_file = output_path / f"{split}.csv"

        if split == "test" and output_file.exists():
            existing = pd.read_csv(output_file, keep_default_na=False)
            same = existing["text"].tolist() == df["text"].tolist() and (
                existing["label"].tolist() == df["label"].tolist()
            )
            if not same:
                raise RuntimeError(
                    f"{output_file} is the fixed test set and the new output differs. "
                    "Delete it manually only if you really intend to redefine the test set."
                )
            logger.info(f"test: {len(df)} samples, {output_file} unchanged (write-once)")
            continue

        df.to_csv(output_file, index=False, encoding="utf-8")
        logger.info(f"{split}: {len(df)} samples -> {output_file}")

    logger.info("Preprocessing complete!")


if __name__ == "__main__":
    setup_logger()
    preprocess_vsmec()
