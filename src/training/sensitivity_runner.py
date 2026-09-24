"""
Post-hoc sensitivity analysis of the ablation: `combined` with its checkpoint chosen on VSMEC val.

    python -m src.training.sensitivity_runner [--seed 43] [--baseline-dir reports/ablation]

The ablation runner early-stops and picks the best epoch of each scenario on the validation data
of its own sources, so `combined` selects on VSMEC val + synthetic val pooled while `real_only`
selects on VSMEC val alone. This runner re-trains `combined` (same train data, same config, the
`ablation.seeds`) but selects on VSMEC val only, the criterion real_only uses. Every epoch it
also scores synthetic val and the pooled val, so the report shows which epoch the pooled
criterion would have picked among the epochs trained.

Decided after the ablation results were seen: report-only (RULE). The ablation verdict stays the
main result.

Each run is tested twice (LOAD_NOTE): `test` / `synthetic_test` score the best checkpoint loaded
correctly (trainer.reload_best), like the ablation runs, and are what the comparison uses;
`test_as_loaded` / `synthetic_test_as_loaded` score the model as load_best_model_at_end left it,
measuring the load bug. The saved model is the correctly loaded one.

One JSON per run, <results_dir>/combined_vsmec_val_seed<S>.json; a run whose JSON exists is
skipped, so re-running after a Colab disconnect resumes. The `training.seed` model is saved to
models/ablation/combined_vsmec_val/. Afterwards <results_dir>/sensitivity.{json,md} compares the
runs with the real_only and combined run JSONs in --baseline-dir, which must share the config.
"""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import torch
import transformers
from sklearn.metrics import confusion_matrix
from sklearn.utils.class_weight import compute_class_weight
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    EarlyStoppingCallback,
    PreTrainedModel,
    PreTrainedTokenizerBase,
    PrinterCallback,
    Trainer,
    TrainingArguments,
    set_seed,
)

from ..data.ablation import SYNTHETIC_TEST_FILE
from ..utils.config_schema import (
    AblationParams,
    ModelConfig,
    TrainingConfig,
    load_validated_configs,
)
from ..utils.emotion_constants import DEFAULT_EMOTION_LABELS
from ..utils.logger import get_logger, setup_logger
from ..utils.metrics import LABEL_IDS, compute_metrics, compute_metrics_for_trainer
from .ablation_runner import CANDIDATE, CHECKPOINT_DIR, MODEL_DIR, _mean_std, verdict
from .trainer import EmotionDataset, EpochLogger, focal_loss, quiet_logs, reload_best

logger = get_logger("sensitivity_runner")

SCENARIO = "combined_vsmec_val"
RESULTS_DIR = Path("reports/ablation_sensitivity")
# Validation sets scored every epoch (under ablation_dir); "vsmec" picks the checkpoint.
VALIDATION_FILES = {
    "vsmec": "real_only/validation.csv",
    "synthetic": "synthetic_only/validation.csv",
    "pooled": "combined/validation.csv",
}
HISTORY_METRICS = ("loss", "accuracy", "f1_macro")
AS_LOADED = "_as_loaded"  # suffix of the scores of the model as load_best_model_at_end left it
RULE = (
    f"Post-hoc sensitivity analysis, decided after the ablation results were seen; report-only. "
    f"{SCENARIO} = {CANDIDATE} re-trained with the same train data and config, with checkpoint "
    f"selection and early stopping on VSMEC validation only. Its result under the ablation rule "
    f"is reported for context; the ablation verdict stays the main result."
)
LOAD_NOTE = (
    "transformers 5.3 saves PhoBERT's LayerNorm tensors under the checkpoint's legacy names "
    "(gamma/beta) and load_best_model_at_end restores the best checkpoint with a raw "
    "load_state_dict, which skips all 50 of them: the model keeps the LayerNorm of the last "
    "epoch trained. The first ablation run (archived in reports/ablation_run1_layernorm_bug/) "
    "was tested that way; trainer.reload_best now reloads the best checkpoint through "
    f"from_pretrained, which maps the legacy names. `*{AS_LOADED}` scores measure the bug."
)


def train_vsmec_selected(
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizerBase,
    train_dataset: EmotionDataset,
    eval_datasets: dict[str, EmotionDataset],
    config: TrainingConfig,
    focal_gamma: float,
    class_weights: torch.Tensor | None,
    seed: int,
    output_dir: str | Path,
    run_name: str,
) -> Trainer:
    """
    `trainer.train_model` with several validation sets, the checkpoint chosen on "vsmec".

    Same TrainingArguments as `train_model` (it takes one validation set and selects on its
    f1_macro, so it cannot be reused); only eval_dataset and metric_for_best_model differ.
    The Trainer logs every set of the dict under its own prefix, eval_<name>_<metric>.

    Args:
        model: Freshly initialised classifier (seed it before creating it)
        tokenizer: Its tokenizer, also used to pad each batch
        train_dataset: Training data
        eval_datasets: Validation sets by name; must contain "vsmec"
        config: Training config
        focal_gamma: Focal loss gamma (model config)
        class_weights: Per-class loss weights, or None
        seed: Run seed (data order, dropout)
        output_dir: Checkpoint directory
        run_name: Name of the run in the experiment tracker

    Returns:
        The trainer, holding the best model as load_best_model_at_end restores it (LOAD_NOTE)
    """
    params = config.training
    if config.wandb.enabled:
        os.environ.setdefault("WANDB_PROJECT", config.wandb.project)
    args = TrainingArguments(
        output_dir=str(output_dir),
        run_name=run_name,
        seed=seed,
        num_train_epochs=params.num_epochs,
        per_device_train_batch_size=params.batch_size,
        per_device_eval_batch_size=params.batch_size,
        gradient_accumulation_steps=params.gradient_accumulation_steps,
        learning_rate=params.learning_rate,
        weight_decay=params.weight_decay,
        warmup_steps=params.warmup_ratio,  # transformers 5: a value < 1 is a fraction of all steps
        lr_scheduler_type=config.scheduler.type,
        optim=config.optimizer.type,
        adam_beta1=config.optimizer.betas[0],
        adam_beta2=config.optimizer.betas[1],
        adam_epsilon=config.optimizer.eps,
        fp16=params.fp16 and torch.cuda.is_available(),
        eval_strategy="epoch",
        save_strategy="epoch",
        save_only_model=True,
        save_total_limit=config.logging.save_total_limit,
        load_best_model_at_end=True,
        metric_for_best_model="eval_vsmec_f1_macro",
        logging_steps=config.logging.log_steps,
        report_to=["wandb"] if config.wandb.enabled else "none",
        disable_tqdm=True,
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=eval_datasets,
        processing_class=tokenizer,
        compute_loss_func=lambda outputs, labels, num_items_in_batch=None: focal_loss(
            outputs.logits, labels, focal_gamma, class_weights, num_items_in_batch
        ),
        compute_metrics=compute_metrics_for_trainer,
        callbacks=[
            EarlyStoppingCallback(early_stopping_patience=params.early_stopping_patience),
            EpochLogger(),
        ],
    )
    trainer.remove_callback(PrinterCallback)  # EpochLogger prints instead, as in train_model
    trainer.train()
    return trainer


def merge_history(log_history: list[dict]) -> list[dict]:
    """
    One row per epoch, {epoch, <set>_<metric>}, from the Trainer log.

    Evaluating a dict of validation sets logs one entry per set (eval_<set>_<metric>); runtime
    and throughput keys are dropped.
    """
    rows = {}
    for entry in log_history:
        for key, value in entry.items():
            name, _, metric = key.removeprefix("eval_").partition("_")
            if key.startswith("eval_") and name in VALIDATION_FILES and metric in HISTORY_METRICS:
                row = rows.setdefault(entry["epoch"], {"epoch": entry["epoch"]})
                row[f"{name}_{metric}"] = value
    return list(rows.values())


def pick_epoch(history: list[dict], key: str) -> float:
    """First epoch with the highest `key`, the one the Trainer keeps (it needs a strict gain)."""
    return max(history, key=lambda row: row[key])["epoch"]


def score(trainer: Trainer, datasets: dict[str, EmotionDataset], suffix: str = "") -> dict:
    """
    Metrics + confusion matrix of the trainer's current model on each dataset, keyed
    <name><suffix>; the VSMEC test entries also keep the predictions.
    """
    record = {}
    for name, ds in datasets.items():
        key = f"{name}{suffix}"
        # Own prefix per split, so trackers never show the synthetic score as test/*.
        preds = trainer.predict(ds, metric_key_prefix=key).predictions.argmax(-1)
        metrics = compute_metrics(preds, np.array(ds.labels))
        metrics["confusion_matrix"] = confusion_matrix(ds.labels, preds, labels=LABEL_IDS).tolist()
        if name == "test":
            metrics["predictions"] = preds.tolist()
        record[key] = metrics
    return record


def run_one(seed: int, model_cfg: ModelConfig, config: TrainingConfig) -> dict:
    """
    Train `combined` with one seed, selecting on VSMEC val, and evaluate it.

    Args:
        seed: Run seed
        model_cfg: Model config
        config: Training config

    Returns:
        The run record written to <results_dir>/combined_vsmec_val_seed<seed>.json
    """
    data_dir = Path(config.ablation.ablation_dir)
    name, max_len = model_cfg.model.name, model_cfg.model.max_seq_length

    tokenizer = AutoTokenizer.from_pretrained(name)
    train_ds = EmotionDataset(data_dir / CANDIDATE / "train.csv", tokenizer, max_len)
    val_ds = {
        key: EmotionDataset(data_dir / path, tokenizer, max_len)
        for key, path in VALIDATION_FILES.items()
    }
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
    run_name = f"{SCENARIO}_seed{seed}"
    output_dir = CHECKPOINT_DIR / run_name
    started = time.time()
    trainer = train_vsmec_selected(
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

    history = merge_history(trainer.state.log_history)
    record = {
        "scenario": SCENARIO,
        "seed": seed,
        "n_train": len(train_ds),
        "n_validation": {key: len(ds) for key, ds in val_ds.items()},
        "class_weights": class_weights.tolist() if class_weights is not None else None,
        "epochs_run": trainer.state.epoch,
        "best_validation_f1_macro": trainer.state.best_metric,
        "best_epoch": pick_epoch(history, "vsmec_f1_macro"),
        "pooled_pick_epoch": pick_epoch(history, "pooled_f1_macro"),
        "validation_history": history,
        "train_seconds": round(time.time() - started),
    }
    test_sets = {
        "test": EmotionDataset(Path(config.ablation.test_path), tokenizer, max_len),
        "synthetic_test": EmotionDataset(data_dir / SYNTHETIC_TEST_FILE, tokenizer, max_len),
    }
    # First as load_best_model_at_end restored it (LOAD_NOTE), only to measure the load bug; then
    # loaded correctly, as train_model does for the ablation runs.
    record |= score(trainer, test_sets, AS_LOADED)
    reload_best(trainer)
    record |= score(trainer, test_sets)
    record["load_note"] = LOAD_NOTE
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
        trainer.save_model(str(MODEL_DIR / SCENARIO))  # also saves the tokenizer
        logger.info(f"Model saved -> {MODEL_DIR / SCENARIO}")
    shutil.rmtree(output_dir, ignore_errors=True)
    del trainer, model
    torch.cuda.empty_cache()
    return record


def summarize(results_dir: Path, baseline_dir: Path, ablation: AblationParams) -> dict:
    """
    Compare the sensitivity runs with the ablation's real_only and combined runs.

    Writes <results_dir>/sensitivity.json + sensitivity.md.

    Args:
        results_dir: Directory holding combined_vsmec_val_seed<S>.json
        baseline_dir: Directory holding the ablation's <scenario>_seed<S>.json
        ablation: Ablation config

    Returns:
        The sensitivity record
    """
    seeds, baseline, metrics = ablation.seeds, ablation.baseline, ablation.metrics
    scenario_dirs = {baseline: baseline_dir, CANDIDATE: baseline_dir, SCENARIO: results_dir}
    runs = {}
    for scenario, directory in scenario_dirs.items():
        for seed in seeds:
            path = directory / f"{scenario}_seed{seed}.json"
            if path.exists():
                runs[(scenario, seed)] = json.loads(path.read_text(encoding="utf-8"))
    if len({json.dumps(run["config"], sort_keys=True) for run in runs.values()}) > 1:
        raise ValueError(
            f"Runs in {baseline_dir} and {results_dir} used different configs: the comparison "
            "needs identical hyperparameters"
        )

    scores = {}
    for (scenario, seed), run in runs.items():
        scores.setdefault(scenario, {})[seed] = run["test"]
    scenarios = {}
    for scenario in scenario_dirs:
        done = [s for s in seeds if (scenario, s) in runs]
        splits = ["test", "synthetic_test"]
        if scenario == SCENARIO:
            splits += [f"{split}{AS_LOADED}" for split in splits]
        scenarios[scenario] = {"seeds_done": done}
        for split in splits:
            scenarios[scenario][split] = (
                {m: _mean_std([runs[(scenario, s)][split][m] for s in done]) for m in metrics}
                if done
                else None
            )

    per_seed, selection, load = {}, {}, {}
    for seed in seeds:
        if (SCENARIO, seed) not in runs:
            continue
        run = runs[(SCENARIO, seed)]
        per_seed[seed] = {
            f"minus_{other}": {m: run["test"][m] - runs[(other, seed)]["test"][m] for m in metrics}
            for other in (baseline, CANDIDATE)
            if (other, seed) in runs
        }
        vsmec_f1 = {row["epoch"]: row["vsmec_f1_macro"] for row in run["validation_history"]}
        selection[seed] = {
            f"{CANDIDATE}_best_epoch": runs.get((CANDIDATE, seed), {}).get("best_epoch"),
            "best_epoch": run["best_epoch"],
            "pooled_pick_epoch": run["pooled_pick_epoch"],
            "vsmec_f1_at_best_epoch": vsmec_f1[run["best_epoch"]],
            "vsmec_f1_at_pooled_pick_epoch": vsmec_f1[run["pooled_pick_epoch"]],
        }
        fixed, loaded = run["test"], run[f"test{AS_LOADED}"]
        load[seed] = {
            "best_epoch": run["best_epoch"],
            "epochs_run": run["epochs_run"],
            "fixed_minus_as_loaded": {m: fixed[m] - loaded[m] for m in metrics},
            "predictions_changed": int(
                np.sum(np.array(fixed["predictions"]) != np.array(loaded["predictions"]))
            ),
        }

    record = {
        "rule": RULE,
        "load_note": LOAD_NOTE,
        "ablation_verdict": verdict(
            scores, seeds, ablation.min_accuracy, ablation.min_f1_macro, baseline, CANDIDATE
        ),
        "same_rule_post_hoc": verdict(
            scores, seeds, ablation.min_accuracy, ablation.min_f1_macro, baseline, SCENARIO
        ),
        "scenarios": scenarios,
        "per_seed": per_seed,
        "checkpoint_selection": selection,
        "best_checkpoint_load": load,
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "sensitivity.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (results_dir / "sensitivity.md").write_text(_markdown(record, ablation), encoding="utf-8")
    logger.info(f"Sensitivity -> {results_dir / 'sensitivity.json'}")
    return record


def _markdown(record: dict, ablation: AblationParams) -> str:
    """Human-readable tables of the sensitivity record."""

    def cell(stat: dict) -> str:
        std = f" ± {stat['std']:.4f}" if stat["std"] is not None else ""
        return f"{stat['mean']:.4f}{std}"

    verdict_text = {True: "PASS", False: "FAIL", None: "INCOMPLETE (runs missing)"}
    baseline, metrics = ablation.baseline, ablation.metrics
    lines = [f"# Sensitivity: {SCENARIO} (post-hoc, report-only)", "", RULE, ""]
    lines += [
        f"- Ablation verdict ({CANDIDATE}, main result): "
        f"{verdict_text[record['ablation_verdict']]}",
        f"- {SCENARIO} under the same rule (context only): "
        f"{verdict_text[record['same_rule_post_hoc']]}",
        "",
    ]
    for split, title in (
        ("test", "VSMEC test"),
        ("synthetic_test", "Synthetic test (in-domain, secondary)"),
    ):
        lines += [f"## {title}", "", "| Scenario | Seeds | " + " | ".join(metrics) + " |"]
        lines += ["|---" * (len(metrics) + 2) + "|"]
        for scenario, summary in record["scenarios"].items():
            for key, label in (
                (split, scenario),
                (f"{split}{AS_LOADED}", f"{scenario} (as loaded)"),
            ):
                if summary.get(key) is not None:
                    row = " | ".join(cell(summary[key][m]) for m in metrics)
                    lines += [f"| {label} | {len(summary['seeds_done'])} | {row} |"]
        lines += [""]

    others = (baseline, CANDIDATE)
    lines += [f"## {SCENARIO} minus each scenario, per seed (VSMEC test)", ""]
    lines += ["| Seed | " + " | ".join(f"{m} vs {o}" for o in others for m in metrics) + " |"]
    lines += ["|---" * (len(metrics) * len(others) + 1) + "|"]
    for seed, diffs in record["per_seed"].items():
        values = [
            f"{diffs[f'minus_{o}'][m]:+.4f}" if f"minus_{o}" in diffs else "-"
            for o in others
            for m in metrics
        ]
        lines += [f"| {seed} | " + " | ".join(values) + " |"]
    lines += [""]

    lines += ["## Checkpoint selection per seed", ""]
    lines += [
        f"| Seed | {CANDIDATE} best epoch (pooled val) | best epoch (VSMEC val) | pooled val "
        "would pick | VSMEC val F1 at best | VSMEC val F1 at pooled pick |"
    ]
    lines += ["|---" * 6 + "|"]
    for seed, sel in record["checkpoint_selection"].items():
        lines += [
            f"| {seed} | {sel[f'{CANDIDATE}_best_epoch']} | {sel['best_epoch']} "
            f"| {sel['pooled_pick_epoch']} | {sel['vsmec_f1_at_best_epoch']:.4f} "
            f"| {sel['vsmec_f1_at_pooled_pick_epoch']:.4f} |"
        ]
    lines += [""]

    lines += ["## Best-checkpoint load: fixed minus as loaded (VSMEC test)", "", LOAD_NOTE, ""]
    lines += [
        "| Seed | Best epoch | Epochs run | " + " | ".join(metrics) + " | Predictions changed |"
    ]
    lines += ["|---" * (len(metrics) + 4) + "|"]
    for seed, entry in record["best_checkpoint_load"].items():
        diffs = " | ".join(f"{entry['fixed_minus_as_loaded'][m]:+.4f}" for m in metrics)
        lines += [
            f"| {seed} | {entry['best_epoch']} | {entry['epochs_run']} | {diffs} "
            f"| {entry['predictions_changed']} |"
        ]
    return "\n".join(lines) + "\n"


def run_sensitivity(
    config_dir: str = "configs",
    seed: int | None = None,
    baseline_dir: str | None = None,
    results_dir: str | Path = RESULTS_DIR,
) -> dict:
    """
    Run every seed of `ablation.seeds` without a result JSON yet, then summarize.

    Fails before training when a baseline run JSON is missing or used another config.

    Args:
        config_dir: Directory holding model/training/api config YAMLs
        seed: Only run this seed
        baseline_dir: Directory of the ablation run JSONs (default `ablation.results_dir`)
        results_dir: Where the sensitivity JSONs go

    Returns:
        The sensitivity record
    """
    model_cfg, config, _ = load_validated_configs(config_dir)
    ablation = config.ablation
    baseline_path = Path(baseline_dir or ablation.results_dir)
    results_path = Path(results_dir)

    current = json.dumps(
        {"model": model_cfg.model_dump(), "training": config.model_dump()}, sort_keys=True
    )
    for scenario in (ablation.baseline, CANDIDATE):
        for run_seed in ablation.seeds:
            path = baseline_path / f"{scenario}_seed{run_seed}.json"
            if not path.exists():
                raise FileNotFoundError(
                    f"{path} not found: point --baseline-dir at the ablation run JSONs"
                )
            run_config = json.loads(path.read_text(encoding="utf-8"))["config"]
            if json.dumps(run_config, sort_keys=True) != current:
                raise ValueError(
                    f"{path} used a different config than {config_dir}: the sensitivity runs "
                    "must reuse the ablation's exact hyperparameters"
                )

    results_path.mkdir(parents=True, exist_ok=True)
    for run_seed in ablation.seeds:
        if seed is not None and run_seed != seed:
            continue
        path = results_path / f"{SCENARIO}_seed{run_seed}.json"
        if path.exists():
            logger.info(f"{path.name} exists, skipping")
            continue
        logger.info(f"=== {SCENARIO}, seed {run_seed} ===")
        record = run_one(run_seed, model_cfg, config)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(
            f"{SCENARIO} seed {run_seed}: test f1_macro={record['test']['f1_macro']:.4f} "
            f"(as loaded {record[f'test{AS_LOADED}']['f1_macro']:.4f}) -> {path}"
        )
    return summarize(results_path, baseline_path, ablation)


def _self_check() -> None:
    """Assert `merge_history` and `pick_epoch`, run with --self-check."""

    def evals(epoch: float, **f1: float) -> list[dict]:
        return [
            {
                f"eval_{name}_loss": 1 - value,
                f"eval_{name}_accuracy": value,
                f"eval_{name}_f1_macro": value,
                f"eval_{name}_runtime": 1.0,
                "epoch": epoch,
            }
            for name, value in f1.items()
        ]

    log = [
        {"loss": 1.2, "grad_norm": 3.0, "learning_rate": 1e-5, "epoch": 0.5},
        *evals(1.0, vsmec=0.40, synthetic=0.90, pooled=0.60),
        *evals(2.0, vsmec=0.45, synthetic=0.93, pooled=0.65),
        *evals(3.0, vsmec=0.45, synthetic=0.96, pooled=0.70),
        {"train_runtime": 10.0, "train_loss": 0.5, "epoch": 3.0},
    ]
    history = merge_history(log)
    assert [row["epoch"] for row in history] == [1.0, 2.0, 3.0], history
    expected_keys = {"epoch"} | {f"{n}_{m}" for n in VALIDATION_FILES for m in HISTORY_METRICS}
    assert all(set(row) == expected_keys for row in history), history
    # Tie at 0.45: the Trainer keeps the first epoch (it needs a strict gain), so must pick_epoch.
    assert pick_epoch(history, "vsmec_f1_macro") == 2.0
    assert pick_epoch(history, "pooled_f1_macro") == 3.0
    logger.info("merge_history / pick_epoch: OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", default="configs")
    parser.add_argument("--seed", type=int, help="Only run this seed")
    parser.add_argument(
        "--baseline-dir", help="Ablation run JSONs (default: training_config ablation.results_dir)"
    )
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    parser.add_argument("--self-check", action="store_true", help="Check helpers and exit")
    args = parser.parse_args()

    setup_logger()
    quiet_logs()
    if args.self_check:
        _self_check()
        sys.exit(0)
    run_sensitivity(args.config_dir, args.seed, args.baseline_dir, args.results_dir)
