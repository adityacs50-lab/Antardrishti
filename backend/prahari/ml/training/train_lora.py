"""LoRA fine-tune MuRIL for span extraction.

    python -m prahari.ml.training.train_lora --epochs 4

Reproducible: one seed drives Python, NumPy and Torch, and the dataloader is
seeded too. Two runs with the same seed and the same corpus produce the same
adapters.

Budget: ~3k reports x 4 epochs at batch 16, seq 320, on a base-size encoder with
LoRA on the attention projections only. That is roughly 750 optimiser steps and
comfortably inside 2 GPU-hours on a Colab T4 — most of the wall clock is the
first-run model download, not the training.

Build-time only. Nothing in the running application imports this file.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from prahari.data.annotation import BIO_LABELS, ID_TO_LABEL, LABEL_TO_ID
from prahari.ml.config import BASE_MODEL, MAX_LENGTH, SEED


def set_seed(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(False)  # cuDNN kernels have no det. path here


def load_split(dataset_dir: Path, split: str):  # noqa: ANN201
    rows = []
    with (dataset_dir / f"{split}.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m prahari.ml.training.train_lora")
    parser.add_argument("--dataset", type=Path, default=Path("models/dataset"))
    parser.add_argument("--out", type=Path, default=Path("models/lora-adapters"))
    parser.add_argument("--model", default=BASE_MODEL)
    parser.add_argument("--epochs", type=float, default=4.0)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=3e-4)  # LoRA tolerates a high LR
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    args = parser.parse_args(argv)

    import numpy as np
    import torch
    from peft import LoraConfig, TaskType, get_peft_model
    from torch.utils.data import Dataset
    from transformers import (
        AutoModelForTokenClassification, DataCollatorForTokenClassification,
        AutoTokenizer, Trainer, TrainingArguments,
    )

    set_seed(args.seed)

    class SpanDataset(Dataset):
        def __init__(self, rows):  # noqa: ANN001
            self.rows = rows

        def __len__(self) -> int:
            return len(self.rows)

        def __getitem__(self, i: int) -> dict:
            row = self.rows[i]
            return {
                "input_ids": row["input_ids"],
                "attention_mask": row["attention_mask"],
                "labels": row["labels"],
            }

    train_rows = load_split(args.dataset, "train")
    val_rows = load_split(args.dataset, "val")
    print(f"train={len(train_rows)}  val={len(val_rows)}  labels={len(BIO_LABELS)}")

    tokenizer = AutoTokenizer.from_pretrained(args.dataset / "tokenizer")
    model = AutoModelForTokenClassification.from_pretrained(
        args.model,
        num_labels=len(BIO_LABELS),
        id2label=ID_TO_LABEL,
        label2id=LABEL_TO_ID,
    )

    # LoRA on the attention projections only. The classification head is new and
    # trains in full; adapting the attention is what lets a 17-language encoder
    # specialise to code-mixed oilfield register without 110M trainable params.
    peft_config = LoraConfig(
        task_type=TaskType.TOKEN_CLS,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        target_modules=["query", "key", "value", "dense"],
        modules_to_save=["classifier"],
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    def compute_metrics(pred):  # noqa: ANN001, ANN202
        logits, labels = pred
        preds = np.argmax(logits, axis=-1)
        tp = fp = fn = 0
        for p_row, l_row in zip(preds, labels):
            for p, l in zip(p_row, l_row):
                if l == -100:
                    continue
                if l > 0 and p == l:
                    tp += 1
                elif l > 0 and p != l:
                    fn += 1
                elif l == 0 and p > 0:
                    fp += 1
        recall = tp / (tp + fn) if tp + fn else 0.0
        precision = tp / (tp + fp) if tp + fp else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        # Recall is first because that is the metric this project optimises.
        return {"token_recall": recall, "token_precision": precision, "token_f1": f1}

    training_args = TrainingArguments(
        output_dir=str(args.out / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        learning_rate=args.lr,
        warmup_ratio=0.06,
        weight_decay=0.01,
        logging_steps=25,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=1,
        load_best_model_at_end=True,
        metric_for_best_model="eval_token_recall",  # not F1 — see config.py
        greater_is_better=True,
        seed=args.seed,
        data_seed=args.seed,
        fp16=torch.cuda.is_available(),
        report_to=[],
        dataloader_num_workers=2,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=SpanDataset(train_rows),
        eval_dataset=SpanDataset(val_rows),
        data_collator=DataCollatorForTokenClassification(tokenizer, max_length=MAX_LENGTH),
        compute_metrics=compute_metrics,
    )
    trainer.train()

    args.out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.out)
    tokenizer.save_pretrained(args.out)
    metrics = trainer.evaluate()
    (args.out / "train_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("\n" + "=" * 62)
    print(f"adapters saved to {args.out}")
    for key in ("eval_token_recall", "eval_token_precision", "eval_token_f1"):
        if key in metrics:
            print(f"  {key:24s} {metrics[key]:.4f}")
    print("=" * 62)
    print("next:  python -m prahari.ml.training.evaluate")
    print("       python -m prahari.ml.training.export_onnx")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
