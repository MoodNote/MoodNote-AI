"""
Pydantic schemas for the YAML files in `configs/`.

Validation catches typos and drift between config and code at load time instead of
halfway through a training run. Schemas mirror the YAML exactly; they are a checking
layer, not a second source of default values.

Emotion labels and sentiment scores deliberately live in `emotion_constants.py` only —
the YAML does not repeat them. `ModelConfig` cross-checks `model.num_labels` against
that constant so the two cannot drift apart.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from .config import load_config
from .emotion_constants import DEFAULT_EMOTION_LABELS


class _Strict(BaseModel):
    """Base model that rejects unknown keys."""

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- model_config.yaml


class ModelParams(_Strict):
    name: str
    num_labels: int
    max_seq_length: int
    dropout: float
    label_smoothing: float
    focal_gamma: float


class ModelPreprocessingParams(_Strict):
    segmenter: str
    lowercase: bool


class ModelConfig(_Strict):
    model: ModelParams
    preprocessing: ModelPreprocessingParams

    @model_validator(mode="after")
    def _labels_are_consistent(self) -> ModelConfig:
        expected = len(DEFAULT_EMOTION_LABELS)
        if self.model.num_labels != expected:
            raise ValueError(
                f"model.num_labels is {self.model.num_labels} but emotion_constants "
                f"defines {expected} labels"
            )
        return self


# ------------------------------------------------------------------------ training_config.yaml


class TrainingParams(_Strict):
    learning_rate: float
    batch_size: int
    gradient_accumulation_steps: int
    num_epochs: int
    warmup_ratio: float
    weight_decay: float
    fp16: bool
    seed: int
    early_stopping_patience: int
    use_llrd: bool
    llrd_factor: float
    use_class_weights: bool
    rdrop_alpha: float


class OptimizerParams(_Strict):
    type: str
    betas: list[float]
    eps: float


class SchedulerParams(_Strict):
    type: str


class LoggingParams(_Strict):
    log_steps: int
    eval_steps: int
    save_steps: int
    save_total_limit: int


class WandbParams(_Strict):
    project: str
    name: str
    enabled: bool


class AblationParams(_Strict):
    scenarios: list[str]
    baseline: str
    metrics: list[str]
    seeds: list[int]
    multi_seed_scenarios: list[str]
    real_dir: str
    synthetic_dir: str
    ablation_dir: str
    validation_path: str
    test_path: str
    results_dir: str

    @model_validator(mode="after")
    def _scenarios_are_consistent(self) -> AblationParams:
        if self.baseline not in self.scenarios:
            raise ValueError(f"baseline {self.baseline!r} is not one of scenarios {self.scenarios}")
        unknown = set(self.multi_seed_scenarios) - set(self.scenarios)
        if unknown:
            raise ValueError(f"multi_seed_scenarios not in scenarios: {sorted(unknown)}")
        return self


class TrainingConfig(_Strict):
    training: TrainingParams
    optimizer: OptimizerParams
    scheduler: SchedulerParams
    logging: LoggingParams
    wandb: WandbParams
    # Written for the phase 4 ablation runner; absent in earlier phases.
    ablation: AblationParams | None = None


# ----------------------------------------------------------------------------- api_config.yaml


class ApiServerParams(_Strict):
    host: str
    port: int
    reload: bool
    workers: int


class ApiModelParams(_Strict):
    path: str
    device: Literal["cuda", "cpu"]
    max_batch_size: int


class ApiPreprocessingParams(_Strict):
    segmenter: str
    max_length: int


class APIConfig(_Strict):
    api: ApiServerParams
    model: ApiModelParams
    preprocessing: ApiPreprocessingParams


# ------------------------------------------------------------------------- datagen_config.yaml


class LLMModelParams(_Strict):
    display_name: str
    hf_model_id: str


class SplitRatios(_Strict):
    train: float
    validation: float
    test: float


class GenerationParams(_Strict):
    target_total_samples: int
    target_per_label: int
    split_ratios: SplitRatios
    load_in_4bit: bool
    batch_size: int
    max_new_tokens: int
    temperature: float
    top_p: float
    repetition_penalty: float
    log_every_n_samples: int


class DiversityAxes(_Strict):
    van_phong: list[str]
    do_dai: list[str]
    ngu_canh: list[str]


class DedupParams(_Strict):
    near_dup_threshold: float


class LeakageGuardParams(_Strict):
    near_dup_threshold: float
    compare_splits: list[Literal["train", "validation", "test"]]
    partial_match_min_words: int


class PromptParams(_Strict):
    instruction_template_id: str


class DatagenConfig(_Strict):
    seed: int
    models: dict[str, LLMModelParams]
    generation: GenerationParams
    diversity_axes: DiversityAxes
    dedup: DedupParams
    leakage_guard: LeakageGuardParams
    prompt: PromptParams

    @model_validator(mode="after")
    def _targets_are_consistent(self) -> DatagenConfig:
        # Cross-LLM audit swaps the two generators (Qwen checks Llama and vice versa).
        if len(self.models) != 2:
            raise ValueError(f"models must list exactly 2 LLMs, got {sorted(self.models)}")
        gen = self.generation
        expected = gen.target_per_label * len(DEFAULT_EMOTION_LABELS)
        if gen.target_total_samples != expected:
            raise ValueError(
                f"target_total_samples is {gen.target_total_samples} but target_per_label x "
                f"{len(DEFAULT_EMOTION_LABELS)} labels = {expected}"
            )
        ratios = gen.split_ratios
        if abs(ratios.train + ratios.validation + ratios.test - 1.0) > 1e-9:
            raise ValueError(f"split_ratios must sum to 1, got {ratios}")
        return self


# ------------------------------------------------------------------------------ qa_config.yaml


class ManualAuditParams(_Strict):
    sample_size: int
    seed: int
    raters: list[str]
    min_cohens_kappa: float

    @model_validator(mode="after")
    def _two_raters(self) -> ManualAuditParams:
        if len(self.raters) != 2:
            raise ValueError(f"Cohen's Kappa needs exactly 2 raters, got {self.raters}")
        return self


class CrossLLMAuditParams(_Strict):
    audit_fraction: float
    seed: int
    max_unnatural_rate: float
    max_label_mismatch_rate: float


class AcceptanceParams(_Strict):
    drop_cross_llm_flagged: bool


class QAConfig(_Strict):
    manual_audit: ManualAuditParams
    cross_llm_audit: CrossLLMAuditParams
    acceptance: AcceptanceParams


# ------------------------------------------------------------------------------------ loading


def load_validated_configs(
    config_dir: str | Path = "configs",
) -> tuple[ModelConfig, TrainingConfig, APIConfig]:
    """
    Load and validate model/training/api configs.

    Args:
        config_dir: Directory containing the YAML config files

    Returns:
        tuple: (ModelConfig, TrainingConfig, APIConfig)
    """
    config_path = Path(config_dir)
    raw: dict[str, dict[str, Any]] = {
        name: load_config(config_path / f"{name}_config.yaml")
        for name in ("model", "training", "api")
    }

    return (
        ModelConfig(**raw["model"]),
        TrainingConfig(**raw["training"]),
        APIConfig(**raw["api"]),
    )
