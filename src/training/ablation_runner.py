"""
Run the 3-scenario ablation of the proposal (Nội dung 2) and write the comparison report.

    python -m src.training.ablation_runner [--scenario combined] [--seed 43]

Needs `python -m src.data.ablation` first. Runs every scenario x seed of training_config
`ablation` (all `seeds` for multi_seed_scenarios, `training.seed` alone for the others) with the
same hyperparameters: only the train/validation data differ. Every run is tested on the fixed
VSMEC test set (`ablation.test_path`) and, as a secondary in-domain report only, on the
synthetic test split. One JSON per run, <results_dir>/<scenario>_seed<S>.json; a run whose JSON
exists is skipped, so re-running after a Colab disconnect resumes. The model of each
scenario's `training.seed` run is saved to models/ablation/<scenario>/ (Hugging Face format).

Afterwards every run JSON present is aggregated into <results_dir>/comparison.{json,md}: mean
± std per scenario, the proposal thresholds checked on the mean, and the verdict (`verdict`,
rule fixed before any result was seen).
"""

import argparse
import json
import shutil
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import transformers
from sklearn.metrics import confusion_matrix
from sklearn.utils.class_weight import compute_class_weight
from transformers import AutoModelForSequenceClassification, AutoTokenizer, set_seed

from ..data.ablation import SYNTHETIC_TEST_FILE
from ..utils.config_schema import (
    AblationParams,
    ModelConfig,
    TrainingConfig,
    load_validated_configs,
)
from ..utils.emotion_constants import DEFAULT_EMOTION_LABELS
from ..utils.logger import get_logger, setup_logger
from ..utils.metrics import LABEL_IDS, compute_metrics
from .trainer import EmotionDataset, focal_loss, quiet_logs, train_model

logger = get_logger("ablation_runner")

CANDIDATE = "combined"  # the scenario the proposal compares against the baseline
MODEL_DIR = Path("models/ablation")
CHECKPOINT_DIR = Path("models/checkpoints")


def scenario_seeds(ablation: AblationParams, default_seed: int) -> dict[str, list[int]]:
    """Seeds each scenario runs with."""
    return {
        s: ablation.seeds if s in ablation.multi_seed_scenarios else [default_seed]
        for s in ablation.scenarios
    }


def run_one(scenario: str, seed: int, model_cfg: ModelConfig, config: TrainingConfig) -> dict:
    """
    Train one scenario with one seed and evaluate it.

    Args:
        scenario: Scenario name (a directory under ablation_dir)
        seed: Run seed
        model_cfg: Model config
        config: Training config

    Returns:
        The run record written to <results_dir>/<scenario>_seed<seed>.json
    """
    ablation = config.ablation
    data_dir = Path(ablation.ablation_dir)
    name, max_len = model_cfg.model.name, model_cfg.model.max_seq_length

    tokenizer = AutoTokenizer.from_pretrained(name)
    train_ds = EmotionDataset(data_dir / scenario / "train.csv", tokenizer, max_len)
    val_ds = EmotionDataset(data_dir / scenario / "validation.csv", tokenizer, max_len)
    class_weights = None
    if config.training.use_class_weights:
        weights = compute_class_weight("balanced", classes=np.array(LABEL_IDS), y=train_ds.labels)
        class_weights = torch.tensor(weights, dtype=torch.float)

    # Seed before the model exists, so the randomly initialised head is seeded too.
    set_seed(seed)
    model = AutoModelForSequenceClassification.from_pretrained(
        name,
        num_labels=model_cfg.model.num_labels,
        id2label=DEFAULT_EMOTION_LABELS,
        label2id={label: idx for idx, label in DEFAULT_EMOTION_LABELS.items()},
    )
    run_name = f"{scenario}_seed{seed}"
    output_dir = CHECKPOINT_DIR / run_name
    started = time.time()
    trainer = train_model(
        model,
        tokenizer,
        train_ds,
        val_ds,
        config,
        model_cfg.model.focal_gamma,
        class_weights,
        seed,
        output_dir,
        f"{config.wandb.name}-{run_name}",
    )

    history = [
        {k: h[k] for k in ("epoch", "eval_loss", "eval_accuracy", "eval_f1_macro")}
        for h in trainer.state.log_history
        if "eval_f1_macro" in h
    ]
    record = {
        "scenario": scenario,
        "seed": seed,
        "n_train": len(train_ds),
        "n_validation": len(val_ds),
        "class_weights": class_weights.tolist() if class_weights is not None else None,
        "epochs_run": trainer.state.epoch,
        "best_validation_f1_macro": trainer.state.best_metric,
        "best_epoch": next(
            h["epoch"] for h in history if h["eval_f1_macro"] == trainer.state.best_metric
        ),
        "validation_history": history,
        "train_seconds": round(time.time() - started),
    }
    for key, path in (
        ("test", Path(ablation.test_path)),
        ("synthetic_test", data_dir / SYNTHETIC_TEST_FILE),
    ):
        ds = EmotionDataset(path, tokenizer, max_len)
        # Own prefix per split, so trackers never show the synthetic score as test/*.
        preds = trainer.predict(ds, metric_key_prefix=key).predictions.argmax(-1)
        metrics = compute_metrics(preds, np.array(ds.labels))
        metrics["confusion_matrix"] = confusion_matrix(ds.labels, preds, labels=LABEL_IDS).tolist()
        if key == "test":
            metrics["predictions"] = preds.tolist()
        record[key] = metrics
    record["config"] = {"model": model_cfg.model_dump(), "training": config.model_dump()}
    record["environment"] = {
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "device": torch.cuda.get_device_name() if torch.cuda.is_available() else "cpu",
    }

    if config.wandb.enabled:
        import wandb

        # The HF callback reuses an open W&B run, so close it or every run logs into the first.
        wandb.finish()
    if seed == config.training.seed:
        trainer.save_model(str(MODEL_DIR / scenario))  # also saves the tokenizer
        logger.info(f"Model saved -> {MODEL_DIR / scenario}")
    shutil.rmtree(output_dir, ignore_errors=True)
    del trainer, model
    torch.cuda.empty_cache()
    return record


def verdict(
    scores: dict[str, dict[int, dict[str, float]]],
    seeds: list[int],
    min_accuracy: float,
    min_f1_macro: float,
    baseline: str,
    candidate: str = CANDIDATE,
) -> bool | None:
    """
    The proposal's pass rule, fixed before any result was seen (report-only, gates nothing).

    Passes when the candidate's mean accuracy and mean F1-macro over `seeds` reach the
    thresholds AND, for every seed, the candidate's accuracy and F1-macro are not lower than
    the baseline's with the same seed.

    Args:
        scores: scenario -> seed -> test metrics (`accuracy`, `f1_macro`)
        seeds: Seeds both scenarios ran with
        min_accuracy: Accuracy threshold
        min_f1_macro: F1-macro threshold
        baseline: Baseline scenario ("phương án nền")
        candidate: Scenario compared against the baseline

    Returns:
        True / False, or None while a needed run is missing
    """
    if any(seed not in scores.get(s, {}) for s in (baseline, candidate) for seed in seeds):
        return None
    cand, base = scores[candidate], scores[baseline]
    meets = (
        statistics.mean(cand[s]["accuracy"] for s in seeds) >= min_accuracy
        and statistics.mean(cand[s]["f1_macro"] for s in seeds) >= min_f1_macro
    )
    not_lower = all(cand[s][m] >= base[s][m] for s in seeds for m in ("accuracy", "f1_macro"))
    return meets and not_lower


def _mean_std(values: list[float]) -> dict:
    return {
        "mean": statistics.mean(values),
        "std": statistics.stdev(values) if len(values) > 1 else None,
        "values": values,
    }


def summarize(results_dir: Path, ablation: AblationParams, default_seed: int) -> dict:
    """
    Aggregate the run JSONs in `results_dir` and write comparison.json + comparison.md.

    Args:
        results_dir: Directory holding <scenario>_seed<S>.json
        ablation: Ablation config
        default_seed: `training.seed`

    Returns:
        The comparison record
    """
    planned = scenario_seeds(ablation, default_seed)
    runs = {}
    for scenario, seeds in planned.items():
        for seed in seeds:
            path = results_dir / f"{scenario}_seed{seed}.json"
            if path.exists():
                runs[(scenario, seed)] = json.loads(path.read_text(encoding="utf-8"))

    # Resumed runs may come from sessions with a different config: never mix them.
    by_config = {}
    for (scenario, seed), run in runs.items():
        key = json.dumps(run["config"], sort_keys=True)
        by_config.setdefault(key, []).append(f"{scenario}_seed{seed}")
    if len(by_config) > 1:
        raise ValueError(
            f"Runs in {results_dir} used different configs, groups {list(by_config.values())}: "
            "the ablation needs identical hyperparameters, delete the stale run JSONs and re-run"
        )

    scores = {}
    for (scenario, seed), run in runs.items():
        scores.setdefault(scenario, {})[seed] = run["test"]
    scenarios = {}
    for scenario, seeds in planned.items():
        done = [s for s in seeds if (scenario, s) in runs]
        summary = {"seeds_planned": seeds, "seeds_done": done}
        for split in ("test", "synthetic_test"):
            summary[split] = (
                {
                    m: _mean_std([runs[(scenario, s)][split][m] for s in done])
                    for m in ablation.metrics
                }
                if done
                else None
            )
        test = summary["test"]
        summary["meets_thresholds"] = (
            test["accuracy"]["mean"] >= ablation.min_accuracy
            and test["f1_macro"]["mean"] >= ablation.min_f1_macro
            if test
            else None
        )
        scenarios[scenario] = summary

    paired = [
        s for s in planned[CANDIDATE] if (CANDIDATE, s) in runs and (ablation.baseline, s) in runs
    ]
    comparison = {
        "verdict": verdict(
            scores,
            planned[CANDIDATE],
            ablation.min_accuracy,
            ablation.min_f1_macro,
            ablation.baseline,
        ),
        "rule": (
            f"{CANDIDATE}: mean accuracy >= {ablation.min_accuracy} and mean f1_macro >= "
            f"{ablation.min_f1_macro} on the VSMEC test set, and for every seed accuracy and "
            f"f1_macro not lower than {ablation.baseline} with the same seed"
        ),
        "thresholds": {"accuracy": ablation.min_accuracy, "f1_macro": ablation.min_f1_macro},
        "scenarios": scenarios,
        f"{CANDIDATE}_minus_{ablation.baseline}_per_seed": {
            s: {
                m: scores[CANDIDATE][s][m] - scores[ablation.baseline][s][m]
                for m in ablation.metrics
            }
            for s in paired
        },
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "comparison.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (results_dir / "comparison.md").write_text(_markdown(comparison, ablation), encoding="utf-8")
    logger.info(f"Comparison -> {results_dir / 'comparison.json'}")
    return comparison


def _markdown(comparison: dict, ablation: AblationParams) -> str:
    """Human-readable tables of the comparison record."""

    def cell(stat: dict) -> str:
        std = f" ± {stat['std']:.4f}" if stat["std"] is not None else ""
        return f"{stat['mean']:.4f}{std}"

    verdict_text = {True: "PASS", False: "FAIL", None: "INCOMPLETE (runs missing)"}
    lines = [f"# Ablation comparison — verdict: {verdict_text[comparison['verdict']]}", ""]
    lines += [f"Rule: {comparison['rule']}.", ""]
    for split, title in (
        ("test", "VSMEC test (main result)"),
        ("synthetic_test", "Synthetic test (in-domain, secondary)"),
    ):
        lines += [f"## {title}", ""]
        lines += ["| Scenario | Seeds | " + " | ".join(ablation.metrics) + " | Thresholds |"]
        lines += ["|---" * (len(ablation.metrics) + 3) + "|"]
        for scenario, summary in comparison["scenarios"].items():
            if summary[split] is None:
                continue
            flag = {True: "met", False: "not met"}[summary["meets_thresholds"]]
            metrics = " | ".join(cell(summary[split][m]) for m in ablation.metrics)
            lines += [
                f"| {scenario} | {len(summary['seeds_done'])}/{len(summary['seeds_planned'])} "
                f"| {metrics} | {flag if split == 'test' else '-'} |"
            ]
        lines += [""]
    diffs = comparison[f"{CANDIDATE}_minus_{ablation.baseline}_per_seed"]
    if diffs:
        lines += [f"## {CANDIDATE} − {ablation.baseline}, per seed (VSMEC test)", ""]
        lines += ["| Seed | " + " | ".join(ablation.metrics) + " |"]
        lines += ["|---" * (len(ablation.metrics) + 1) + "|"]
        for seed, diff in diffs.items():
            lines += [
                f"| {seed} | " + " | ".join(f"{diff[m]:+.4f}" for m in ablation.metrics) + " |"
            ]
    return "\n".join(lines) + "\n"


def run_ablation(
    config_dir: str = "configs", scenario: str | None = None, seed: int | None = None
) -> dict:
    """
    Run every planned (scenario, seed) without a result JSON yet, then summarize.

    Args:
        config_dir: Directory holding model/training/api config YAMLs
        scenario: Only run this scenario
        seed: Only run this seed

    Returns:
        The comparison record
    """
    model_cfg, config, _ = load_validated_configs(config_dir)
    ablation = config.ablation
    results_dir = Path(ablation.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    for name, seeds in scenario_seeds(ablation, config.training.seed).items():
        for run_seed in seeds:
            if (scenario and name != scenario) or (seed is not None and run_seed != seed):
                continue
            path = results_dir / f"{name}_seed{run_seed}.json"
            if path.exists():
                logger.info(f"{path.name} exists, skipping")
                continue
            logger.info(f"=== {name}, seed {run_seed} ===")
            record = run_one(name, run_seed, model_cfg, config)
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(
                f"{name} seed {run_seed}: test accuracy={record['test']['accuracy']:.4f} "
                f"f1_macro={record['test']['f1_macro']:.4f} -> {path}"
            )
    return summarize(results_dir, ablation, config.training.seed)


def _self_check() -> None:
    """Assert `verdict` and `focal_loss`, run with --self-check."""

    def run(acc: float, f1: float) -> dict:
        return {"accuracy": acc, "f1_macro": f1}

    seeds = [42, 43, 44]
    base = {42: run(0.64, 0.60), 43: run(0.65, 0.61), 44: run(0.63, 0.59)}
    good = {42: run(0.66, 0.61), 43: run(0.66, 0.62), 44: run(0.65, 0.60)}
    assert verdict({"real_only": base, "combined": good}, seeds, 0.65, 0.60, "real_only") is True
    # Beats the baseline on every seed but misses the accuracy threshold.
    weak_base = {s: run(r["accuracy"] - 0.05, r["f1_macro"]) for s, r in base.items()}
    weak = {s: run(r["accuracy"] - 0.04, r["f1_macro"]) for s, r in good.items()}
    assert (
        verdict({"real_only": weak_base, "combined": weak}, seeds, 0.65, 0.60, "real_only") is False
    )
    # Thresholds met on the mean, but seed 44 has a lower F1-macro than the baseline.
    one_loss = {**good, 44: run(0.65, 0.58)}
    assert (
        verdict({"real_only": base, "combined": one_loss}, seeds, 0.65, 0.60, "real_only") is False
    )
    missing = {s: r for s, r in good.items() if s != 44}
    assert verdict({"real_only": base, "combined": missing}, seeds, 0.65, 0.60, "real_only") is None
    logger.info("verdict: 4/4 cases OK")

    logits, labels = torch.randn(8, 7), torch.randint(0, 7, (8,))
    assert torch.allclose(focal_loss(logits, labels, 0.0), F.cross_entropy(logits, labels))
    assert torch.allclose(
        focal_loss(logits, labels, 2.0, num_items_in_batch=8), focal_loss(logits, labels, 2.0)
    )
    assert focal_loss(logits, labels, 2.0) < focal_loss(logits, labels, 0.0)
    logger.info("focal_loss: 3/3 cases OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", default="configs")
    parser.add_argument("--scenario", help="Only run this scenario")
    parser.add_argument("--seed", type=int, help="Only run this seed")
    parser.add_argument(
        "--self-check", action="store_true", help="Check verdict()/focal_loss() and exit"
    )
    args = parser.parse_args()

    setup_logger()
    quiet_logs()
    if args.self_check:
        _self_check()
        sys.exit(0)
    run_ablation(args.config_dir, args.scenario, args.seed)
