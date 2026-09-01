"""Configuration for the ML extraction layer.

Nothing here reaches the network at runtime. `BASE_MODEL` names the checkpoint
used at TRAINING time only; inference loads a local ONNX file and a local
tokenizer, and fails closed to the keyword extractor if either is missing.
"""

from __future__ import annotations

import os
from pathlib import Path

#: MuRIL: multilingual BERT pretrained on 17 Indian languages INCLUDING their
#: transliterated forms. That last part is the reason it is here — the corpus
#: is full of "safety belt nahi pehna tha" and "eku aghat poa nai" written in
#: Latin script, which mBERT sees as noise and IndicBERT (Devanagari/native
#: script focused) also handles poorly.
BASE_MODEL = "google/muril-base-cased"

MAX_LENGTH = 320
SEED = 42


def models_dir() -> Path:
    return Path(os.environ.get("PRAHARI_MODELS_DIR", Path(__file__).resolve().parents[3] / "models"))


def onnx_path() -> Path:
    return Path(os.environ.get("PRAHARI_ONNX_PATH", models_dir() / "prahari.onnx"))


def tokenizer_path() -> Path:
    return Path(os.environ.get("PRAHARI_TOKENIZER_PATH", models_dir() / "tokenizer.json"))


def adapter_dir() -> Path:
    return models_dir() / "lora-adapters"


# --------------------------------------------------------------------------
# The threshold, and why it is where it is
# --------------------------------------------------------------------------
#
# A token is taken as part of an entity when P(entity) exceeds this value, NOT
# when entity is the argmax class. Lowering it below 0.5 deliberately trades
# precision for recall.
#
# The asymmetry is not a modelling preference, it is the safety case:
#
#   A FALSE POSITIVE costs one HSE officer a few minutes of review. The report
#   is opened, the rule trace is read, the verdict is overridden, and the
#   correction is stored. The cost is bounded, visible and recoverable.
#
#   A FALSE NEGATIVE costs a life. A missed precursor is a report that was
#   closed out as unremarkable, sitting in a queue nobody looks at again, at a
#   site where the same barrier is about to fail once more.
#
# Those costs are not comparable, so the operating point is not the F1 optimum.
# It is deliberately to the left of it.
DEFAULT_ENTITY_THRESHOLD = float(os.environ.get("PRAHARI_ENTITY_THRESHOLD", "0.35"))

#: The floor the test suite enforces on the held-out split.
MIN_ENTITY_RECALL = 0.90

#: CPU inference budget per report.
LATENCY_BUDGET_MS = 200.0
