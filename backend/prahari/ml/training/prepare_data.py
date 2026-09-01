"""Corpus -> BIO token-classification dataset.

    python -m prahari.ml.training.prepare_data --out models/dataset

Reads `gold_spans` from the synthetic corpus. Those spans come from what the
GENERATOR knows it wrote, not from running the keyword extractor over its own
output — a model trained on the latter could only learn to imitate the keyword
extractor, inheriting exactly the blind spots that justify replacing it.
See prahari/data/annotation.py for the full argument and its limitations.

Build-time only. Not imported by the running application.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from prahari.ml.config import BASE_MODEL, MAX_LENGTH
from prahari.ml.labels import BIO_LABELS, CharSpan, spans_to_bio


def corpus_path() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "synthetic_reports.jsonl"


def build(
    out_dir: Path,
    corpus: Path,
    model_name: str = BASE_MODEL,
    tokenizer=None,  # noqa: ANN001 — injectable so the builder is testable without torch
) -> dict:
    """Corpus -> BIO dataset.

    `tokenizer` is injectable purely so this can be exercised in CI without
    downloading a 500MB checkpoint; production always passes None.
    """
    if tokenizer is None:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    if hasattr(tokenizer, "save_pretrained"):
        tokenizer.save_pretrained(out_dir / "tokenizer")

    buckets: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    label_counts: Counter = Counter()
    truncated = 0

    with corpus.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            text = record["text"]
            spans = [
                CharSpan(label=s["label"], start=s["start"], end=s["end"])
                for s in record.get("gold_spans", [])
            ]
            encoding = tokenizer(
                text,
                return_offsets_mapping=True,
                truncation=True,
                max_length=MAX_LENGTH,
            )
            offsets = [tuple(o) for o in encoding["offset_mapping"]]
            labels = spans_to_bio(spans, offsets)
            if len(encoding["input_ids"]) >= MAX_LENGTH:
                truncated += 1
            for lid in labels:
                if lid > 0:
                    label_counts[BIO_LABELS[lid]] += 1

            split = record["meta"]["split"]
            buckets[split].append(
                {
                    "report_id": record["report_id"],
                    "text": text,
                    "input_ids": encoding["input_ids"],
                    "attention_mask": encoding["attention_mask"],
                    "labels": labels,
                    "offsets": offsets,
                    "gold_spans": record.get("gold_spans", []),
                    "sif_classification": record["labels"]["sif_classification"],
                }
            )

    for split, rows in buckets.items():
        path = out_dir / f"{split}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    stats = {
        "train": len(buckets["train"]),
        "val": len(buckets["val"]),
        "test": len(buckets["test"]),
        "truncated_at_max_length": truncated,
        "entity_tokens": dict(label_counts),
        "num_labels": len(BIO_LABELS),
    }
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m prahari.ml.training.prepare_data")
    parser.add_argument("--out", type=Path, default=Path("models/dataset"))
    parser.add_argument("--corpus", type=Path, default=None)
    parser.add_argument("--model", default=BASE_MODEL)
    args = parser.parse_args(argv)

    stats = build(args.out, args.corpus or corpus_path(), args.model)
    print(json.dumps(stats, indent=2))
    print(f"\nWrote {args.out}/[train|val|test].jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
