"""
Filter the raw synthetic pool: drop empty/truncated rows, duplicates, and rows leaking VSMEC.

    python -m src.data.synthetic.filter

Reads <data-dir>/raw/*.jsonl, writes <data-dir>/filtered/pool.jsonl (kept rows) and
dropped.jsonl (with `drop_reason`). Checks run in order and each row gets the first reason
that hits it: empty -> truncated -> foreign_script -> exact_dup -> near_dup -> leakage.
`foreign_script` catches Chinese characters the generators sometimes slip in; English is not
filtered here (loanwords like "Facebook" are normal Vietnamese) and is left to the prompt and
the cross-LLM audit.
"""

import argparse
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process, utils

from ...utils.config import load_config
from ...utils.config_schema import DatagenConfig
from ...utils.logger import get_logger, setup_logger
from .generate import read_jsonl, write_jsonl

logger = get_logger("filter")


def near_duplicate_mask(texts: list[str], threshold: float) -> np.ndarray:
    """
    Flag texts that are near-duplicates of an earlier kept text (greedy, first one wins).

    Args:
        texts: Texts in priority order
        threshold: rapidfuzz token_sort_ratio (0-100) at or above which two texts are duplicates

    Returns:
        Boolean array, True = drop
    """
    # ponytail: full n x n score matrix (~40MB at 3k rows); chunk it if the pool grows past ~20k.
    scores = process.cdist(
        texts,
        texts,
        scorer=fuzz.token_sort_ratio,
        processor=utils.default_process,
        score_cutoff=threshold,
        workers=-1,
    )
    drop = np.zeros(len(texts), dtype=bool)
    for i in range(1, len(texts)):
        drop[i] = bool((scores[i, :i][~drop[:i]] >= threshold).any())
    return drop


def leakage_mask(
    texts: list[str], real_texts: list[str], threshold: float, partial_min_words: int
) -> np.ndarray:
    """
    Flag synthetic texts that match a real VSMEC text too closely.

    Two checks, both at `threshold`: token_sort_ratio against every VSMEC sentence (whole-text
    near-duplicate), and partial_ratio against VSMEC sentences of at least `partial_min_words`
    words (a real sentence copied into a longer diary entry, which token_sort_ratio misses).

    Args:
        texts: Synthetic texts
        real_texts: Raw VSMEC sentences
        threshold: rapidfuzz score (0-100) at or above which a text counts as leaked
        partial_min_words: Minimum VSMEC sentence length for the containment check

    Returns:
        Boolean array, True = drop
    """
    long_real = [t for t in real_texts if len(t.split()) >= partial_min_words]
    leaked = np.zeros(len(texts), dtype=bool)
    for scorer, choices in ((fuzz.token_sort_ratio, real_texts), (fuzz.partial_ratio, long_real)):
        scores = process.cdist(
            texts,
            choices,
            scorer=scorer,
            processor=utils.default_process,
            score_cutoff=threshold,
            workers=-1,
        )
        leaked |= scores.max(axis=1) >= threshold
    return leaked


def filter_pool(
    data_dir: str = "data/synthetic",
    real_dir: str = "data/real/raw",
    config_path: str = "configs/datagen_config.yaml",
) -> None:
    """
    Run all filters over the raw pool and write the kept and dropped rows.

    Args:
        data_dir: Synthetic data root (reads raw/, writes filtered/)
        real_dir: Directory with the raw VSMEC CSV files (column `Sentence`)
        config_path: Path to datagen config YAML
    """
    cfg = DatagenConfig(**load_config(config_path))
    raw_files = sorted((Path(data_dir) / "raw").glob("*.jsonl"))
    if not raw_files:
        raise FileNotFoundError(f"No raw JSONL files in {Path(data_dir) / 'raw'}")

    df = pd.DataFrame([row for f in raw_files for row in read_jsonl(f)])
    real_texts = [
        text
        for split in cfg.leakage_guard.compare_splits
        for text in pd.read_csv(Path(real_dir) / f"{split}.csv")["Sentence"].astype(str)
    ]
    logger.info(f"Raw pool: {len(df)} rows from {[f.name for f in raw_files]}")

    checks: list[tuple[str, Callable[[pd.DataFrame], np.ndarray]]] = [
        ("empty", lambda d: (d["text"].str.strip() == "").to_numpy()),
        ("truncated", lambda d: d["truncated"].to_numpy(dtype=bool)),
        # Not a raw string: Python turns \u escapes into the characters themselves, which
        # pyarrow's RE2 engine (pandas 3 string dtype) accepts but cannot parse as escapes.
        ("foreign_script", lambda d: d["text"].str.contains("[\u3400-\u9fff]").to_numpy()),
        (
            "exact_dup",
            lambda d: d["text"].str.lower().str.split().str.join(" ").duplicated().to_numpy(),
        ),
        (
            "near_dup",
            lambda d: near_duplicate_mask(d["text"].tolist(), cfg.dedup.near_dup_threshold),
        ),
        (
            "leakage",
            lambda d: leakage_mask(
                d["text"].tolist(),
                real_texts,
                cfg.leakage_guard.near_dup_threshold,
                cfg.leakage_guard.partial_match_min_words,
            ),
        ),
    ]
    reason = pd.Series(None, index=df.index, dtype=object)
    for name, check in checks:
        alive = df[reason.isna()]
        if alive.empty:
            break
        reason[alive.index[np.asarray(check(alive), dtype=bool)]] = name

    output_dir = Path(data_dir) / "filtered"
    output_dir.mkdir(parents=True, exist_ok=True)
    kept = df[reason.isna()]
    dropped = df[reason.notna()].assign(drop_reason=reason[reason.notna()])
    write_jsonl(output_dir / "pool.jsonl", kept.to_dict("records"))
    write_jsonl(output_dir / "dropped.jsonl", dropped.to_dict("records"))

    logger.info(f"Dropped: {reason.value_counts().to_dict()}")
    if not dropped.empty:
        # Truncation hits long entries first; a skew here means max_new_tokens is too tight.
        by_length = dropped.groupby(["drop_reason", "do_dai"]).size().unstack(fill_value=0)
        logger.info(f"Dropped per (reason, do_dai):\n{by_length}")
    logger.info(f"Kept per (model, label):\n{kept.groupby(['model', 'label']).size().unstack(0)}")
    logger.info(f"Kept {len(kept)}/{len(df)} -> {output_dir / 'pool.jsonl'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/synthetic")
    parser.add_argument("--real-dir", default="data/real/raw")
    parser.add_argument("--config", default="configs/datagen_config.yaml")
    args = parser.parse_args()

    setup_logger()
    filter_pool(args.data_dir, args.real_dir, args.config)
