"""
Export blind annotation sheets for the manual audit (layer 1 of Human-in-the-loop QA).

    python -m src.qa.manual_audit

Draws `manual_audit.sample_size` rows from the filtered pool and writes one sheet per rater
to <data-dir>/audit/<rater>.csv with columns stt,text,label. `label` is left empty. Rows are
numbered by `stt` instead of the pool id, because the id spells out the generated label and
model; the acceptance gate redraws the same seeded sample to map `stt` back to ids. The
sheets are UTF-8 with BOM so Excel shows Vietnamese correctly; save them back as "CSV UTF-8".
"""

import argparse
from pathlib import Path

import pandas as pd

from ..data.synthetic.generate import read_jsonl
from ..utils.config import load_config
from ..utils.config_schema import ManualAuditParams, QAConfig
from ..utils.logger import get_logger, setup_logger

logger = get_logger("manual_audit")


def draw_audit_sample(pool: pd.DataFrame, cfg: ManualAuditParams) -> pd.DataFrame:
    """
    Draw the seeded audit sample. The acceptance gate calls this too, to map sheets back.

    Args:
        pool: Filtered pool, in the order of filtered/pool.jsonl
        cfg: manual_audit block of the QA config

    Returns:
        The audited rows of `pool`, in sheet order
    """
    return pool.sample(n=cfg.sample_size, random_state=cfg.seed)


def export_audit_sheets(
    data_dir: str = "data/synthetic", config_path: str = "configs/qa_config.yaml"
) -> None:
    """
    Sample the audit rows and write one empty annotation sheet per rater.

    Refuses to run if a sheet already exists: it may already hold a rater's labels.

    Args:
        data_dir: Synthetic data root (reads filtered/pool.jsonl, writes audit/)
        config_path: Path to QA config YAML
    """
    cfg = QAConfig(**load_config(config_path)).manual_audit
    audit_dir = Path(data_dir) / "audit"
    sheets = [audit_dir / f"{rater}.csv" for rater in cfg.raters]
    existing = [str(p) for p in sheets if p.exists()]
    if existing:
        raise FileExistsError(f"Audit sheets already exist, not overwriting: {existing}")

    pool = pd.DataFrame(read_jsonl(Path(data_dir) / "filtered" / "pool.jsonl"))
    sample = draw_audit_sample(pool, cfg)
    blank = pd.DataFrame(
        {"stt": range(1, len(sample) + 1), "text": sample["text"].to_numpy(), "label": ""}
    )

    audit_dir.mkdir(parents=True, exist_ok=True)
    for sheet in sheets:
        blank.to_csv(sheet, index=False, encoding="utf-8-sig")
        logger.info(f"{len(blank)} rows -> {sheet}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/synthetic")
    parser.add_argument("--config", default="configs/qa_config.yaml")
    args = parser.parse_args()

    setup_logger()
    export_audit_sheets(args.data_dir, args.config)
