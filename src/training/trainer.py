"""
Fine-tune PhoBERT for 7-label emotion classification: one run (the ablation runner loops it).

Loss: focal loss (Lin et al., 2017) times inverse-frequency class weights, two of the three
imbalance techniques the proposal names (the third, data augmentation, is the synthetic data of
the combined scenario). Everything else is standard Hugging Face fine-tuning:
AutoModelForSequenceClassification head, AdamW, linear warmup then the configured schedule
(cosine), evaluation and checkpointing once per epoch, early stopping and best-checkpoint
selection on validation F1-macro, padding per batch.
"""

import os
from pathlib import Path

import pandas as pd
import torch
import torch.nn.functional as F
import transformers
from huggingface_hub.utils import disable_progress_bars
from torch.utils.data import Dataset
from transformers import (
    EarlyStoppingCallback,
    PreTrainedModel,
    PreTrainedTokenizerBase,
    PrinterCallback,
    Trainer,
    TrainerCallback,
    TrainingArguments,
)

from ..utils.config_schema import TrainingConfig
from ..utils.logger import get_logger
from ..utils.metrics import compute_metrics_for_trainer

logger = get_logger("trainer")


class EmotionDataset(Dataset):
    """A `text,label` CSV (text already word-segmented), tokenized once and left unpadded."""

    def __init__(self, path: str | Path, tokenizer: PreTrainedTokenizerBase, max_length: int):
        frame = pd.read_csv(path)
        self.encodings = tokenizer(frame["text"].tolist(), truncation=True, max_length=max_length)
        self.labels = frame["label"].tolist()

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> dict:
        item = {key: values[idx] for key, values in self.encodings.items()}
        item["labels"] = self.labels[idx]
        return item


def focal_loss(
    logits: torch.Tensor,
    labels: torch.Tensor,
    gamma: float,
    weight: torch.Tensor | None = None,
    num_items_in_batch: torch.Tensor | int | None = None,
) -> torch.Tensor:
    """
    Focal loss, optionally class-weighted: -w[y] * (1 - p_y)^gamma * log p_y.

    p_y comes from the unweighted cross-entropy: the class weight scales the loss, it must not
    change the probability the modulating factor is computed from.

    Args:
        logits: (batch, num_labels)
        labels: (batch,) class ids
        gamma: Focusing parameter; 0 gives (weighted) cross-entropy
        weight: Per-class weights, or None
        num_items_in_batch: Items in the whole accumulated batch, passed by the Trainer while
            training; the sum is divided by it so gradient accumulation equals one big batch.
            None (evaluation) gives the plain mean.

    Returns:
        Scalar loss
    """
    ce = F.cross_entropy(logits.float(), labels, reduction="none")
    loss = (1 - torch.exp(-ce)) ** gamma * ce
    if weight is not None:
        loss = loss * weight.to(loss.device)[labels]
    if num_items_in_batch is None:
        return loss.mean()
    return loss.sum() / num_items_in_batch


def train_model(
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizerBase,
    train_dataset: EmotionDataset,
    eval_dataset: EmotionDataset,
    config: TrainingConfig,
    focal_gamma: float,
    class_weights: torch.Tensor | None,
    seed: int,
    output_dir: str | Path,
    run_name: str,
) -> Trainer:
    """
    Train until early stopping or num_epochs and load the best checkpoint (validation F1-macro).

    Args:
        model: Freshly initialised classifier (seed it before creating it)
        tokenizer: Its tokenizer, also used to pad each batch
        train_dataset: Training data
        eval_dataset: Validation data (early stopping + checkpoint selection)
        config: Training config
        focal_gamma: Focal loss gamma (model config)
        class_weights: Per-class loss weights, or None
        seed: Run seed (data order, dropout)
        output_dir: Checkpoint directory
        run_name: Name of the run in the experiment tracker

    Returns:
        The trainer, holding the best model
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
        metric_for_best_model="f1_macro",
        logging_steps=config.logging.log_steps,
        report_to=["wandb"] if config.wandb.enabled else "none",
        disable_tqdm=True,
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
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
    # disable_tqdm swaps the progress bars for a callback printing every log dict: EpochLogger
    # prints instead. The experiment tracker still receives every log.
    trainer.remove_callback(PrinterCallback)
    trainer.train()
    reload_best(trainer)
    return trainer


def reload_best(trainer: Trainer) -> None:
    """
    Load the best checkpoint into trainer.model, LayerNorm included.

    transformers 5.3 saves PhoBERT's LayerNorm under the checkpoint's legacy names (gamma/beta),
    and load_best_model_at_end restores the checkpoint with a raw load_state_dict that skips
    them, leaving the last epoch's LayerNorm in the model. from_pretrained maps the names; the
    strict load fails if any tensor does not match.

    Args:
        trainer: A trainer after train(), with load_best_model_at_end (its best checkpoint is
            kept on disk whatever save_total_limit is)
    """
    best = type(trainer.model).from_pretrained(trainer.state.best_model_checkpoint)
    trainer.model.load_state_dict(best.state_dict())


class EpochLogger(TrainerCallback):
    """One log line per evaluation and one per run, in place of progress bars and log dicts."""

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        # eval_f1_macro, or eval_<set>_f1_macro when the Trainer evaluates a dict of sets
        prefix = next(key for key in metrics if key.endswith("f1_macro")).removesuffix("f1_macro")
        name = prefix.removeprefix("eval_").rstrip("_") or "val"
        values = " ".join(
            f"{m} {metrics[prefix + m]:.4f}" for m in ("loss", "accuracy", "f1_macro")
        )
        logger.info(f"epoch {state.epoch:.0f}/{args.num_train_epochs:.0f} {name}: {values}")

    def on_train_end(self, args, state, control, **kwargs):
        key = args.metric_for_best_model
        key = key if key.startswith("eval_") else f"eval_{key}"
        best = next(h["epoch"] for h in state.log_history if h.get(key) == state.best_metric)
        logger.info(
            f"best epoch {best:.0f} ({key.removeprefix('eval_')} {state.best_metric:.4f}), "
            f"stopped at epoch {state.epoch:.0f}/{args.num_train_epochs:.0f}"
        )


def quiet_logs() -> None:
    """
    Keep the console to the runners' INFO lines and EpochLogger.

    Silences transformers warnings (all expected here: the new classifier head, the legacy
    LayerNorm names reload_best handles, early stopping seeing one validation set at a time),
    progress bars and W&B's console output. Errors still show; W&B still records every log.
    """
    transformers.logging.set_verbosity_error()
    transformers.logging.disable_progress_bar()
    disable_progress_bars()
    os.environ.setdefault("WANDB_SILENT", "true")
