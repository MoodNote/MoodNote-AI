"""
Generate synthetic Vietnamese diary entries per emotion label with an open-source LLM.

Runs on Colab (see notebooks/datagen_colab.ipynb):
    python -m src.data.synthetic.generate --model llama

Rows are appended to <data-dir>/raw/<model>.jsonl after every batch. A re-run resumes and
only generates the rows still missing, so a Colab disconnect loses at most one batch.
Empty or truncated outputs are kept and counted by `filter`; raise --per-label and re-run
to top up a label that ends up short.
"""

import argparse
import json
import random
import re
import zlib
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import Any

from ...utils.config import load_config
from ...utils.config_schema import DatagenConfig
from ...utils.emotion_constants import DEFAULT_EMOTION_LABELS
from ...utils.logger import get_logger, setup_logger
from .llm_client import HFClient
from .prompts import build_generation_messages

logger = get_logger("generate")

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of dicts."""
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: str | Path, rows: Iterable[Mapping[Any, Any]], append: bool = False) -> None:
    """Write (or append) dicts as JSONL, keeping Vietnamese text readable."""
    with open(path, "a" if append else "w", encoding="utf-8") as f:
        f.writelines(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def clean_output(text: str) -> str:
    """Strip a leftover <think> block, surrounding whitespace and wrapping quotes."""
    return _THINK_BLOCK.sub("", text).strip().strip('"“”').strip()


def generate(
    model_key: str,
    per_label: int | None = None,
    data_dir: str = "data/synthetic",
    config_path: str = "configs/datagen_config.yaml",
) -> None:
    """
    Generate diary entries for every label with one model, resuming from existing output.

    Each label cycles through a seeded shuffle of all (van_phong, do_dai, ngu_canh)
    combinations, so the 3 diversity axes are covered evenly.

    Args:
        model_key: Key under `models` in the datagen config ("llama" or "qwen")
        per_label: Rows per label for this model (default: target_per_label split evenly
            among the models that generate the label; labels in exclude_labels are skipped)
        data_dir: Synthetic data root; output goes to <data_dir>/raw/<model_key>.jsonl
        config_path: Path to datagen config YAML
    """
    cfg = DatagenConfig(**load_config(config_path))
    if model_key not in cfg.models:
        raise ValueError(f"Unknown model {model_key!r}, expected one of {sorted(cfg.models)}")
    model_cfg = cfg.models[model_key]
    gen = cfg.generation
    template_id = cfg.prompt.instruction_template_id
    targets = {
        label: per_label or gen.target_per_label // len(cfg.generators_of(label))
        for label in DEFAULT_EMOTION_LABELS.values()
        if label not in model_cfg.exclude_labels
    }

    output_file = Path(data_dir) / "raw" / f"{model_key}.jsonl"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    existing = read_jsonl(output_file) if output_file.exists() else []
    stale = {row["template_id"] for row in existing} - {template_id}
    if stale:
        raise ValueError(
            f"{output_file} holds rows from template(s) {sorted(stale)}, not {template_id!r}. "
            "Move the previous round's data/synthetic/ away before generating a new round."
        )
    # Resume by the row indices still missing, not by a row count: a batch lost from the
    # Drive-mounted file (v3 lost Llama Anger 0096-0127) must be regenerated under its own ids,
    # not re-issued under the last ids as duplicates.
    done = {(row["label"], int(row["id"].rsplit("-", 1)[1])) for row in existing}
    missing = {
        label: [i for i in range(target) if (label, i) not in done]
        for label, target in targets.items()
    }
    labels = [label for label, indices in missing.items() if indices]
    if not labels:
        logger.info(f"{output_file}: every label already has its target {targets}, nothing to do")
        return

    logger.info(f"Loading {model_cfg.hf_model_id} (4-bit: {gen.load_in_4bit})")
    client = HFClient(model_cfg.hf_model_id, load_in_4bit=gen.load_in_4bit)
    axes = cfg.diversity_axes
    combos = list(product(axes.van_phong, axes.do_dai, axes.ngu_canh))

    for label in labels:
        label_combos = combos.copy()
        random.Random(f"{cfg.seed}-{model_key}-{label}").shuffle(label_combos)

        target, todo = targets[label], missing[label]
        for b in range(0, len(todo), gen.batch_size):
            batch = todo[b : b + gen.batch_size]
            picked = [label_combos[i % len(label_combos)] for i in batch]
            outputs = client.generate(
                [build_generation_messages(template_id, label, *combo) for combo in picked],
                max_new_tokens=gen.max_new_tokens,
                temperature=gen.temperature,
                top_p=gen.top_p,
                repetition_penalty=gen.repetition_penalty,
                seed=zlib.crc32(f"{cfg.seed}-{model_key}-{label}-{batch[0]}".encode()),
            )

            created_at = datetime.now(UTC).isoformat(timespec="seconds")
            rows = [
                {
                    "id": f"{model_key}-{label}-{i:04d}",
                    "text": clean_output(text),
                    "label": label,
                    "model": model_key,
                    "model_id": model_cfg.hf_model_id,
                    "template_id": template_id,
                    "van_phong": van_phong,
                    "do_dai": do_dai,
                    "ngu_canh": ngu_canh,
                    "truncated": truncated,
                    "created_at": created_at,
                }
                for i, (van_phong, do_dai, ngu_canh), (text, truncated) in zip(
                    batch, picked, outputs, strict=True
                )
            ]
            write_jsonl(output_file, rows, append=True)

            n = gen.log_every_n_samples
            end = target - len(todo) + b + len(batch)
            if end // n > (end - len(batch)) // n or end == target:
                logger.info(f"{model_key}/{label}: {end}/{target}")

    logger.info(f"Generation complete -> {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Key under `models` (llama / qwen)")
    parser.add_argument(
        "--per-label",
        type=int,
        help="Rows per label (default: config target split among the models generating it)",
    )
    parser.add_argument("--data-dir", default="data/synthetic")
    parser.add_argument("--config", default="configs/datagen_config.yaml")
    args = parser.parse_args()

    setup_logger()
    generate(args.model, args.per_label, args.data_dir, args.config)
