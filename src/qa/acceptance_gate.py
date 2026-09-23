"""
Acceptance gate: decide whether a synthetic round passes QA and write the accepted dataset.

    python -m src.qa.acceptance_gate

Round verdict (thresholds in configs/qa_config.yaml):
  - Cohen's Kappa between the 2 raters >= manual_audit.min_cohens_kappa
  - Cohen's Kappa between generated and auditor labels >= cross_llm_audit.min_cohens_kappa
  - cross-LLM unnatural rate <= cross_llm_audit.max_unnatural_rate
An unparseable auditor answer counts as a disagreement / unnatural. The label mismatch rate,
a per-generator Kappa, and the Kappa between the generated label and each rater / the rater
consensus are reported but do not gate.

The report is always written, one file per prompt template (reports/qa_report_<template>.json,
so failed rounds stay on record for the report). On failure the script exits 1 and
writes no accepted data (revise the prompt, regenerate). On success it adjudicates the audited
rows (see `adjudicate`): rows the raters read differently are dropped, rows they agree on are
kept, relabelled to their reading where it differs from the generated label. Cross-LLM flagged
rows are dropped too if acceptance.drop_cross_llm_flagged. It then writes
<data-dir>/accepted/accepted.csv (raw text + provenance) and processed.csv (word-segmented
`text`, int `label`, like data/real/processed).
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
    "label_source",
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


def adjudicate(
    rater_a: pd.Series, rater_b: pd.Series, generated: pd.Series
) -> tuple[pd.Series, set[str]]:
    """
    Apply the human-in-the-loop label rule to the audited rows.

    The generated label is a generation *intent*, not an independent annotation: the text was
    written to express it. So the two raters are the only annotators:

      - both raters agree with the generated label -> keep it
      - both raters agree on another label         -> the text conveys that label, relabel
      - the raters disagree                        -> the text is ambiguous, drop

    Args:
        rater_a: First rater's labels, indexed by row id
        rater_b: Second rater's labels, same index
        generated: Generated label of the audited rows, same index

    Returns:
        (labels to apply in place of the generated one, ids to drop)
    """
    agree = rater_a == rater_b
    return rater_a[agree & rater_a.ne(generated)], set(rater_a.index[~agree])


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
    agree = rater_a == rater_b
    adjudicated, manual_drop = adjudicate(rater_a, rater_b, intended)

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
    expected = generated.loc[audits.index]
    predicted = audits["predicted_label"].fillna("unparseable")
    generator = pool.set_index("id")["model"].loc[audits.index]
    cross_kappa = float(cohen_kappa_score(expected, predicted))
    cross_kappa_per_generator = {
        model: float(cohen_kappa_score(expected[generator == model], predicted[generator == model]))
        for model in sorted(generator.unique())
    }
    mismatch = predicted.ne(expected)
    unnatural = ~audits["natural"].eq(True)
    mismatch_rate, unnatural_rate = float(mismatch.mean()), float(unnatural.mean())
    # Two raters outrank the 8B auditor on the label, but they never judged naturalness.
    label_flag = mismatch & ~audits.index.isin(rater_a.index[agree])
    cross_flagged = set(audits.index[label_flag | unnatural])

    passed = (
        kappa >= qa.manual_audit.min_cohens_kappa
        and cross_kappa >= qa.cross_llm_audit.min_cohens_kappa
        and unnatural_rate <= qa.cross_llm_audit.max_unnatural_rate
    )
    drop = manual_drop | (cross_flagged if qa.acceptance.drop_cross_llm_flagged else set())
    accepted = pool[~pool["id"].isin(drop)].copy()
    accepted["label"] = accepted["id"].map(adjudicated).fillna(accepted["label"])
    accepted["label_source"] = (
        accepted["id"].isin(adjudicated.index).map({True: "human_adjudicated", False: "generated"})
    )

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
            "cohens_kappa_with_generated_label": {
                qa.manual_audit.raters[0]: float(cohen_kappa_score(intended, rater_a)),
                qa.manual_audit.raters[1]: float(cohen_kappa_score(intended, rater_b)),
                "consensus": float(cohen_kappa_score(intended[agree], rater_a[agree])),
            },
            "agreement_per_generated_label": pd.DataFrame(
                {
                    qa.manual_audit.raters[0]: rater_a == intended,
                    qa.manual_audit.raters[1]: rater_b == intended,
                    "raters_agree": agree,
                }
            )
            .groupby(intended)
            .mean()
            .to_dict(orient="index"),
            "rows_with_rater_disagreement": len(manual_drop),
            "rows_relabelled": len(adjudicated),
        },
        "cross_llm_audit": {
            "n": len(audits),
            "cohens_kappa": cross_kappa,
            "cohens_kappa_per_generator": cross_kappa_per_generator,
            "label_mismatch_rate": mismatch_rate,
            "unnatural_rate": unnatural_rate,
            "unparseable": int((audits["predicted_label"].isna() | audits["natural"].isna()).sum()),
            "flagged_rows": len(cross_flagged),
        },
        "thresholds": {
            "min_cohens_kappa": qa.manual_audit.min_cohens_kappa,
            "min_cross_llm_cohens_kappa": qa.cross_llm_audit.min_cohens_kappa,
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
        f"kappa={kappa:.3f}, cross_llm_kappa={cross_kappa:.3f}, "
        f"label_mismatch_rate={mismatch_rate:.3f}, unnatural_rate={unnatural_rate:.3f}"
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


def _self_check() -> None:
    """Assert the four audit cases of `adjudicate`, run with --self-check."""
    idx = ["a", "b", "c", "d"]
    gen = pd.Series(["Enjoyment"] * 4, index=idx)
    ra = pd.Series(["Enjoyment", "Sadness", "Enjoyment", "Sadness"], index=idx)
    rb = pd.Series(["Enjoyment", "Sadness", "Fear", "Fear"], index=idx)
    adjudicated, drop = adjudicate(ra, rb, gen)
    assert adjudicated.to_dict() == {"b": "Sadness"}, adjudicated.to_dict()
    assert drop == {"c", "d"}, drop
    logger.info("adjudicate: 4/4 cases OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/synthetic")
    parser.add_argument("--report", help="Default: reports/qa_report_<template_id>.json")
    parser.add_argument("--qa-config", default="configs/qa_config.yaml")
    parser.add_argument("--model-config", default="configs/model_config.yaml")
    parser.add_argument("--self-check", action="store_true", help="Check adjudicate() and exit")
    args = parser.parse_args()

    setup_logger()
    if args.self_check:
        _self_check()
        sys.exit(0)
    sys.exit(
        0
        if run_acceptance_gate(args.data_dir, args.report, args.qa_config, args.model_config)
        else 1
    )
