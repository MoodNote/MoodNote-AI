"""
Build the train/validation files of the 3 ablation scenarios (Nội dung 2 of the proposal).

    python -m src.data.ablation

The accepted synthetic rows are split train/validation/test by datagen_config
`generation.split_ratios` (the proposal's 70/15/15), stratified on label x generator model.
The split is written to <synthetic_dir>/split.csv (id, split) the first time and reused after
that, so every machine trains on the same rows: commit it. Each scenario validates on the
validation data of its own sources, so synthetic_only never sees a real sample:

    real_only       VSMEC train                    / VSMEC validation
    synthetic_only  synthetic train                / synthetic validation
    combined        VSMEC train + synthetic train  / VSMEC validation + synthetic validation

All 3 are tested on the fixed VSMEC test set (training_config `ablation.test_path`, read in
place by the runner). The synthetic test split is only a secondary, in-domain report.
"""

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from ..utils.config import load_config
from ..utils.config_schema import DatagenConfig, SplitRatios, TrainingConfig
from ..utils.emotion_constants import DEFAULT_EMOTION_LABELS
from ..utils.logger import get_logger, setup_logger

logger = get_logger("ablation")

SYNTHETIC_TEST_FILE = "synthetic_test.csv"


def split_synthetic(synthetic: pd.DataFrame, ratios: SplitRatios, seed: int) -> pd.Series:
    """
    Assign each synthetic row to train / validation / test.

    Args:
        synthetic: Rows with `label` and `model` columns
        ratios: Train / validation / test fractions
        seed: Random state of both splits

    Returns:
        Split name per row, aligned with `synthetic.index`
    """
    strata = synthetic["label"].astype(str) + "|" + synthetic["model"]
    train, rest = train_test_split(
        synthetic.index, train_size=ratios.train, stratify=strata, random_state=seed
    )
    validation, test = train_test_split(
        rest,
        train_size=ratios.validation / (ratios.validation + ratios.test),
        stratify=strata[rest],
        random_state=seed,
    )
    split = pd.Series("train", index=synthetic.index)
    split[validation] = "validation"
    split[test] = "test"
    return split


def build_ablation_datasets(
    training_config_path: str = "configs/training_config.yaml",
    datagen_config_path: str = "configs/datagen_config.yaml",
) -> None:
    """
    Write <ablation_dir>/<scenario>/{train,validation}.csv and <ablation_dir>/synthetic_test.csv.

    Args:
        training_config_path: Path to training config YAML (`ablation` block, `training.seed`)
        datagen_config_path: Path to datagen config YAML (`generation.split_ratios`)
    """
    training = TrainingConfig(**load_config(training_config_path))
    ablation = training.ablation
    ratios = DatagenConfig(**load_config(datagen_config_path)).generation.split_ratios

    # processed.csv (segmented text, int label) is row-aligned with accepted.csv (provenance).
    synthetic_dir = Path(ablation.synthetic_dir)
    accepted = pd.read_csv(synthetic_dir / "accepted.csv", usecols=["id", "model", "label"])
    processed = pd.read_csv(synthetic_dir / "processed.csv")
    label_ids = {name: idx for idx, name in DEFAULT_EMOTION_LABELS.items()}
    if (
        len(accepted) != len(processed)
        or not accepted["label"].map(label_ids).eq(processed["label"]).all()
    ):
        raise ValueError(f"accepted.csv and processed.csv in {synthetic_dir} are not row-aligned")
    synthetic = pd.concat([accepted[["id", "model"]], processed], axis=1)

    split_path = synthetic_dir / "split.csv"
    if split_path.exists():
        split = pd.read_csv(split_path).set_index("id")["split"]
        if set(split.index) != set(synthetic["id"]):
            raise ValueError(
                f"{split_path} does not cover exactly the accepted rows (accepted data changed "
                "after the split was made?); delete it to re-split"
            )
        synthetic["split"] = synthetic["id"].map(split)
        logger.info(f"Reusing synthetic split {split_path}")
    else:
        synthetic["split"] = split_synthetic(synthetic, ratios, training.training.seed)
        synthetic[["id", "split"]].to_csv(split_path, index=False, encoding="utf-8")
        logger.info(f"Wrote synthetic split {split_path}")

    columns = ["id", "model", "text", "label"]
    syn = {
        s: synthetic.loc[synthetic["split"] == s, columns] for s in ("train", "validation", "test")
    }
    real = {s: pd.read_csv(Path(ablation.real_dir) / f"{s}.csv") for s in ("train", "validation")}
    sources = {
        "real_only": [real],
        "synthetic_only": [syn],
        "combined": [real, syn],
    }

    out_dir = Path(ablation.ablation_dir)
    for scenario in ablation.scenarios:
        for split_name in ("train", "validation"):
            frame = pd.concat([src[split_name] for src in sources[scenario]], ignore_index=True)
            path = out_dir / scenario / f"{split_name}.csv"
            path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(path, index=False, encoding="utf-8")
            per_label = frame["label"].value_counts().sort_index().tolist()
            logger.info(f"{scenario}/{split_name}: {len(frame)} rows, per label {per_label}")
    syn["test"].to_csv(out_dir / SYNTHETIC_TEST_FILE, index=False, encoding="utf-8")
    logger.info(f"{SYNTHETIC_TEST_FILE}: {len(syn['test'])} rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-config", default="configs/training_config.yaml")
    parser.add_argument("--datagen-config", default="configs/datagen_config.yaml")
    args = parser.parse_args()

    setup_logger()
    build_ablation_datasets(args.training_config, args.datagen_config)
