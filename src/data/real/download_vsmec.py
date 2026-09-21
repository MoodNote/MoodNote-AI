"""
Download UIT-VSMEC from Hugging Face into raw CSV files.
"""

from pathlib import Path

import pandas as pd
from datasets import load_dataset

from ...utils.logger import get_logger, setup_logger

logger = get_logger("download_vsmec")

VSMEC_REPO = "tridm/UIT-VSMEC"
VSMEC_REVISION = "6feda28cba29ea564c76a75b2c77f9af1fbc56e6"
SPLITS = ("train", "validation", "test")


def download_vsmec(output_dir: str = "data/real/raw") -> None:
    """
    Download UIT-VSMEC and save each split as CSV (original columns: Sentence, Emotion).

    Args:
        output_dir: Directory to save the raw CSV files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading {VSMEC_REPO}@{VSMEC_REVISION[:8]}...")
    dataset = load_dataset(VSMEC_REPO, revision=VSMEC_REVISION)

    for split in SPLITS:
        df = dataset[split].to_pandas()
        assert isinstance(df, pd.DataFrame)
        output_file = output_path / f"{split}.csv"
        df.to_csv(output_file, index=False, encoding="utf-8")
        logger.info(f"{split}: {len(df)} samples -> {output_file}")
        logger.info(f"  {df['Emotion'].value_counts().to_dict()}")


if __name__ == "__main__":
    setup_logger()
    download_vsmec()
