"""
Acceptance gate: decide whether a synthetic round passes QA and write the accepted dataset.

    python -m src.qa.acceptance_gate

Round verdict (thresholds in configs/qa_config.yaml):
  - Cohen's Kappa between the 2 raters >= manual_audit.min_cohens_kappa
  - cross-LLM label mismatch rate <= cross_llm_audit.max_label_mismatch_rate
  - cross-LLM unnatural rate <= cross_llm_audit.max_unnatural_rate
An unparseable auditor answer counts as a mismatch / unnatural.

The report is always written, one file per prompt template (reports/qa_report_<template>.json,
so failed rounds stay on record for the report). On failure the script exits 1 and
writes no accepted data (revise the prompt, regenerate). On success it drops audited rows
where at least one rater disagrees with the generated label, plus cross-LLM flagged rows if
acceptance.drop_cross_llm_flagged, and writes <data-dir>/accepted/accepted.csv (raw text +
provenance) and processed.csv (word-segmented `text`, int `label`, like data/real/processed).
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from ..data.real.preprocess import VietnamesePreprocessor, preprocess_frame
from ..data.synthetic.generate import read_jsonl
from ..utils.config import load_config
from ..utils.config_schema import ModelConfig, QAConfig
from ..utils.emotion_constants import DEFAULT_EMOTION_LABELS
from ..utils.logger import get_logger, setup_logger
from .cross_llm_audit import select_cross_llm_rows
from .manual_audit import draw_audit_sample

logger = get_logger("acceptance_gate")

ACCEPTED_COLUMNS = [
    "id",
    "text",
    "label",
    "model",
    "model_id",
    "template_id",
    "van_phong",
    "do_dai",
    "ngu_canh",
]


def _squash(texts: pd.Series) -> list[str]:
    """Collapse whitespace, so a spreadsheet round trip (CRLF, trailing spaces) still matches."""
    return [" ".join(t.split()) for t in texts]


def read_rater_sheet(path: Path, sample: pd.DataFrame) -> pd.Series:
    """
    Read a filled annotation sheet and map its `stt` rows back to pool ids.

    Args:
        path: Sheet written by manual_audit and filled by a rater
        sample: The seeded audit sample (draw_audit_sample), in sheet order

    Returns:
        Canonical label names indexed by row id
    """
    sheet = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    if _squash(sheet["text"]) != _squash(sample["text"]):
        raise ValueError(
            f"{path} does not match the seeded audit sample of the current pool "
            "(rows edited, reordered or removed, or the sheet belongs to another round)"
        )
    names = {name.lower(): name for name in DEFAULT_EMOTION_LABELS.values()}
    labels = sheet["label"].str.strip().str.lower().map(names)
    bad = sheet.loc[labels.isna(), "stt"].tolist()
    if bad:
        raise ValueError(f"{path}: {len(bad)} rows with a missing or unknown label, stt {bad[:10]}")
    return pd.Series(labels.to_numpy(), index=sample["id"].to_numpy())


def run_acceptance_gate(
    data_dir: str = "data/synthetic",
    report_path: str | None = None,
    qa_config_path: str = "configs/qa_config.yaml",
    model_config_path: str = "configs/model_config.yaml",
) -> bool:
    """
    Compute the QA metrics, write the report and, if the round passes, the accepted data.

    Args:
        data_dir: Synthetic data root (reads filtered/ and audit/, writes accepted/)
        report_path: Where to write the QA report JSON (default: per template id in reports/)
        qa_config_path: Path to QA config YAML
        model_config_path: Path to model config YAML (`preprocessing` block, for processed.csv)

    Returns:
        True if the round passed the gate
    """
    qa = QAConfig(**load_config(qa_config_path))
    data = Path(data_dir)
    pool = pd.DataFrame(read_jsonl(data / "filtered" / "pool.jsonl"))
    generated = pool.set_index("id")["label"]

    template_ids = sorted(pool["template_id"].unique())

    # Layer 1: manual audit.
    sample = draw_audit_sample(pool, qa.manual_audit)
    rater_a, rater_b = (
        read_rater_sheet(data / "audit" / f"{r}.csv", sample) for r in qa.manual_audit.raters
    )
    intended = generated.loc[rater_a.index]
    kappa = float(cohen_kappa_score(rater_a, rater_b))
    manual_drop = set(rater_a.index[(rater_a != intended) | (rater_b != intended)])

    # Layer 2: cross-LLM audit. Only verdicts on the current text of a selected row count.
    selected = select_cross_llm_rows(pool, qa.cross_llm_audit)[["id", "text"]]
    verdicts = pd.DataFrame(read_jsonl(data / "audit" / "cross_llm.jsonl"))
    audits = selected.merge(
        verdicts.drop_duplicates(["id", "text"], keep="last"), on=["id", "text"]
    )
    missing = set(selected["id"]) - set(audits["id"])
    if missing:
        raise ValueError(
            f"{len(missing)} selected rows not cross-audited on their current text yet, "
            f"e.g. {sorted(missing)[:5]}"
        )
    audits = audits.set_index("id")
    mismatch = audits["predicted_label"].ne(generated.loc[audits.index])
    unnatural = ~audits["natural"].eq(True)
    mismatch_rate, unnatural_rate = float(mismatch.mean()), float(unnatural.mean())
    cross_flagged = set(audits.index[mismatch | unnatural])

    passed = (
        kappa >= qa.manual_audit.min_cohens_kappa
        and mismatch_rate <= qa.cross_llm_audit.max_label_mismatch_rate
        and unnatural_rate <= qa.cross_llm_audit.max_unnatural_rate
    )
    drop = manual_drop | (cross_flagged if qa.acceptance.drop_cross_llm_flagged else set())
    accepted = pool[~pool["id"].isin(drop)]

    report = {
        "passed": passed,
        "template_ids": template_ids,
        "manual_audit": {
            "n": len(rater_a),
            "cohens_kappa": kappa,
            "rater_agreement_with_generated_label": {
                qa.manual_audit.raters[0]: float((rater_a == intended).mean()),
                qa.manual_audit.raters[1]: float((rater_b == intended).mean()),
            },
            "rows_with_rater_disagreement": len(manual_drop),
        },
        "cross_llm_audit": {
            "n": len(audits),
            "label_mismatch_rate": mismatch_rate,
            "unnatural_rate": unnatural_rate,
            "unparseable": int((audits["predicted_label"].isna() | audits["natural"].isna()).sum()),
            "flagged_rows": len(cross_flagged),
        },
        "thresholds": {
            "min_cohens_kappa": qa.manual_audit.min_cohens_kappa,
            "max_label_mismatch_rate": qa.cross_llm_audit.max_label_mismatch_rate,
            "max_unnatural_rate": qa.cross_llm_audit.max_unnatural_rate,
        },
        "counts": {
            "pool": len(pool),
            "dropped": len(drop) if passed else None,
            "accepted": len(accepted) if passed else None,
            "accepted_per_label": accepted["label"].value_counts().to_dict() if passed else None,
        },
    }
    report_file = Path(report_path or f"reports/qa_report_{'+'.join(template_ids)}.json")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"QA report -> {report_file}")
    logger.info(
        f"kappa={kappa:.3f}, label_mismatch_rate={mismatch_rate:.3f}, "
        f"unnatural_rate={unnatural_rate:.3f}"
    )

    if not passed:
        logger.error("Round FAILED the acceptance gate: revise the prompt and regenerate")
        return False

    preprocessing = ModelConfig(**load_config(model_config_path)).preprocessing
    preprocessor = VietnamesePreprocessor(segmenter=preprocessing.segmenter)
    processed = preprocess_frame(accepted, "text", "label", preprocessor, preprocessing.lowercase)

    accepted_dir = data / "accepted"
    accepted_dir.mkdir(parents=True, exist_ok=True)
    accepted[ACCEPTED_COLUMNS].to_csv(accepted_dir / "accepted.csv", index=False, encoding="utf-8")
    processed.to_csv(accepted_dir / "processed.csv", index=False, encoding="utf-8")
    logger.info(f"Round PASSED: {len(accepted)}/{len(pool)} rows accepted -> {accepted_dir}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/synthetic")
    parser.add_argument("--report", help="Default: reports/qa_report_<template_id>.json")
    parser.add_argument("--qa-config", default="configs/qa_config.yaml")
    parser.add_argument("--model-config", default="configs/model_config.yaml")
    args = parser.parse_args()

    setup_logger()
    sys.exit(
        0
        if run_acceptance_gate(args.data_dir, args.report, args.qa_config, args.model_config)
        else 1
    )
