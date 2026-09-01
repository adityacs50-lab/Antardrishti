# prahari · ML extraction layer (build-time)

Nothing in this directory is imported by the running application. The app
imports `prahari.ml.extract_facts`, which loads `models/prahari.onnx` if it is
there and silently uses the keyword extractor if it is not.

## Pipeline

```bash
# 1. corpus -> BIO dataset (uses the generator's gold spans, not the keyword extractor)
python -m prahari.ml.training.prepare_data --out models/dataset

# 2. LoRA fine-tune MuRIL   (~2 GPU-hours on a Colab T4, reproducible at seed 42)
python -m prahari.ml.training.train_lora --epochs 4

# 3. per-entity + end-to-end metrics, confusion matrix, false-negative dossier
python -m prahari.ml.training.evaluate --split test

# 4. merge adapters -> ONNX -> INT8, writes models/prahari.onnx + tokenizer.json
python -m prahari.ml.training.export_onnx
```

Training extras: `pip install -e ".[ml]"`.

## Why the labels come from the generator

Training labels are the `gold_spans` the generator emits — what it KNOWS it
wrote — not the keyword extractor's matches over its own output. A model
trained on the latter can only imitate the keyword extractor and inherits
exactly the blind spots that justify replacing it. It would never learn that
`safety belt pindhi noasil` is a control negation, because the phrase list is
what taught it.

This is clause-scoped distant supervision, not human annotation: the clause
ROLE is ground truth, and the head phrase inside it is located by lexicon.
Where that lookup fails the whole clause is labelled — true, but coarse. Real
annotated OIL reports would beat it. See `prahari/data/annotation.py`.

## Why MuRIL

The corpus is code-mixed and heavily transliterated: `safety belt nahi pehna
tha`, `eku aghat poa nai`, Devanagari and Assamese script mid-sentence. MuRIL
is pretrained on 17 Indian languages *and their romanised forms*, which is the
specific thing mBERT treats as noise and IndicBERT (native-script focused)
handles poorly.

## Why the threshold favours recall

`config.DEFAULT_ENTITY_THRESHOLD = 0.35`, not 0.5, and the best checkpoint is
selected on recall, not F1.

> A false positive costs one HSE officer a few minutes of review — bounded,
> visible, recoverable. A false negative costs a life.

Those costs are not comparable, so the operating point is deliberately left of
the F1 optimum. `tests/ml/test_recall_floor.py` fails the build below 0.90.

## What the model does and does not decide

It tags six span types: `ENERGY_SOURCE`, `MAGNITUDE_CUE`, `CONTROL_MENTION`,
`CONTROL_NEGATION`, `ACTIVITY`, `LOCATION`. It does **not** emit a SIF verdict,
a severity or a score — the rule engine decides, unchanged, from the spans.

Mapping a span to *which* energy type or *which* control state is a closed
vocabulary lookup (`resolver.py`), not a prediction: the model does the part
the lexicon cannot (finding the span in unseen transliterated text), the
lexicon does the part it is better at (naming the category).
