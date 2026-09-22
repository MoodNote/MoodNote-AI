"""
Export the LLM labels of the manual-audit rows, for the project owner only (not the raters).

    python -m src.qa.audit_key

Redraws the seeded manual-audit sample (same rows and `stt` as the rater sheets) and writes
<data-dir>/audit/llm_labels.xlsx with columns stt, id, text, generated_label, generator,
auditor_label. The auditor label comes from audit/cross_llm.jsonl and exists only for rows that
also fell in the cross-LLM sample; the other rows are left empty ("unparseable" when the auditor
answered but its answer could not be parsed). Keep this file away from the raters: seeing the
labels breaks the blind audit.
"""

import argparse
from pathlib import Path

import pandas as pd

from ..data.synthetic.generate import read_jsonl
from ..utils.config import load_config
from ..utils.config_schema import QAConfig
from ..utils.logger import get_logger, setup_logger
from .manual_audit import draw_audit_sample
from .sheet_convert import write_xlsx

logger = get_logger("audit_key")


def export_audit_key(
    data_dir: str = "data/synthetic", config_path: str = "configs/qa_config.yaml"
) -> Path:
    """
    Write the generated and cross-LLM auditor labels of the manual-audit rows to Excel.

    Args:
        data_dir: Synthetic data root (reads filtered/pool.jsonl and audit/cross_llm.jsonl)
        config_path: Path to QA config YAML

    Returns:
        Path of the written file
    """
    cfg = QAConfig(**load_config(config_path)).manual_audit
    data = Path(data_dir)
    pool = pd.DataFrame(read_jsonl(data / "filtered" / "pool.jsonl"))
    sample = draw_audit_sample(pool, cfg)
    # Only a verdict on the current text counts, as in the acceptance gate.
    verdicts = pd.DataFrame(read_jsonl(data / "audit" / "cross_llm.jsonl"))
    verdicts = verdicts.drop_duplicates(["id", "text"], keep="last")
    verdicts["predicted_label"] = verdicts["predicted_label"].fillna("unparseable")
    rows = sample.merge(verdicts[["id", "text", "predicted_label"]], on=["id", "text"], how="left")

    key = pd.DataFrame(
        {
            "stt": range(1, len(rows) + 1),
            "id": rows["id"],
            "text": rows["text"],
            "generated_label": rows["label"],
            "generator": rows["model"],
            "auditor_label": rows["predicted_label"].fillna(""),
        }
    )
    output = data / "audit" / "llm_labels.xlsx"
    write_xlsx(key, output)
    logger.info(f"{len(key)} rows ({key['auditor_label'].ne('').sum()} cross-audited) -> {output}")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/synthetic")
    parser.add_argument("--config", default="configs/qa_config.yaml")
    args = parser.parse_args()

    setup_logger()
    export_audit_key(args.data_dir, args.config)
