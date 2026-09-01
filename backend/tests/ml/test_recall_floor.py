"""The recall floor, and the CPU latency budget.

Both skip when no trained model is present — but LOUDLY, naming what is
missing, so a green suite is never mistaken for a validated model.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from prahari.ml.config import LATENCY_BUDGET_MS, MIN_ENTITY_RECALL
from prahari.ml.neural_extractor import model_status, predict_spans

DATASET = Path(__file__).resolve().parents[2] / "models" / "dataset"


def _requires_model():
    status = model_status()
    if not status.loaded:
        pytest.skip(
            f"no trained model ({status.reason}). Train and export it first:\n"
            "  python -m prahari.ml.training.prepare_data\n"
            "  python -m prahari.ml.training.train_lora\n"
            "  python -m prahari.ml.training.export_onnx"
        )
    if not (DATASET / "test.jsonl").exists():
        pytest.skip("no prepared dataset — run prahari.ml.training.prepare_data")


def _test_rows(limit: int = 450) -> list[dict]:
    lines = (DATASET / "test.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()][:limit]


def test_entity_recall_stays_above_the_floor() -> None:
    """Recall is the metric this project optimises. A regression fails the build.

    A false positive costs one HSE officer a few minutes of review. A false
    negative is a precursor nobody ever looks at again. The floor is set on
    recall for that reason, not on F1.
    """
    _requires_model()
    rows = _test_rows()

    tp = fn = 0
    for row in rows:
        predicted = predict_spans(row["text"]) or []
        gold = row.get("gold_spans", [])
        taken: set[int] = set()
        for want in gold:
            hit = next(
                (
                    i
                    for i, got in enumerate(predicted)
                    if i not in taken
                    and got.label == want["label"]
                    and got.start < want["end"]
                    and want["start"] < got.end
                ),
                None,
            )
            if hit is None:
                fn += 1
            else:
                taken.add(hit)
                tp += 1

    recall = tp / (tp + fn) if tp + fn else 0.0
    assert recall >= MIN_ENTITY_RECALL, (
        f"entity recall {recall:.3f} is below the {MIN_ENTITY_RECALL:.2f} floor "
        f"({fn} gold spans missed of {tp + fn}). Lower "
        "PRAHARI_ENTITY_THRESHOLD or retrain before shipping."
    )


def test_cpu_inference_stays_inside_the_latency_budget() -> None:
    _requires_model()
    rows = _test_rows(40)
    for row in rows[:3]:
        predict_spans(row["text"])          # warm the session

    timings = []
    for row in rows:
        started = time.perf_counter()
        predict_spans(row["text"])
        timings.append((time.perf_counter() - started) * 1000)
    timings.sort()
    p95 = timings[int(len(timings) * 0.95)]
    assert p95 <= LATENCY_BUDGET_MS, f"p95 {p95:.0f}ms exceeds the {LATENCY_BUDGET_MS:.0f}ms budget"


def test_a_trained_model_beats_the_keyword_baseline_end_to_end() -> None:
    """The model has to earn its place: it must not be worse than the lexicon."""
    _requires_model()
    from prahari.ml import extract_facts
    from prahari.ml.extractor import extract as keyword_extract
    from prahari.rules.engine import evaluate

    rows = _test_rows()
    neural = sum(
        evaluate(extract_facts(r["text"])).classification.value == r["sif_classification"]
        for r in rows
    )
    keyword = sum(
        evaluate(keyword_extract(r["text"])).classification.value == r["sif_classification"]
        for r in rows
    )
    assert neural >= keyword, (
        f"neural path scored {neural}/{len(rows)} vs keyword {keyword}/{len(rows)} — "
        "the model is not earning its place; ship the keyword extractor instead."
    )
