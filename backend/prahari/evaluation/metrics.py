"""Score the shipped pipeline (extractor + rule engine) against gold labels.

Why a runtime module and not a notebook: the dashboard shows these numbers to
judges and HSE officers. A figure on screen that nobody can regenerate is a
claim, not a measurement. This module is the regeneration path, and the JSON it
writes records the engine version, extractor path, corpus and date it was
measured on, so a stale number is visible as stale.

Headline task: SIF PRECURSOR DETECTION - a binary question, "is this report a
PSIF or an Exposure?" (`SIF_PRECURSOR_CLASSES`), which is exactly what the
Triage Queue surfaces. Precision / recall / F1 are for that positive class.
The 8-way SCL classification accuracy is reported alongside it.

Stdlib only; no network; no model required (it measures whichever extractor
path `extract_facts` routes to, and records which one that was).
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from prahari.domain.classification import ACTUAL_SIF_CLASSES, SIF_PRECURSOR_CLASSES
from prahari.ml import active_extractor
from prahari.ml.extractor import EXTRACTOR_VERSION
from prahari.rules.engine import ENGINE_VERSION, analyse

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CORPUS = REPO_ROOT / "data" / "synthetic_reports.jsonl"
DEFAULT_OUT = Path(__file__).with_name("engine_metrics.json")

PRECURSOR = {c.value for c in SIF_PRECURSOR_CLASSES}
SIF_POTENTIAL = PRECURSOR | {c.value for c in ACTUAL_SIF_CLASSES}


def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4)}


def _binary(pairs: list[tuple[str, str]], positive: set[str]) -> dict:
    tp = sum(1 for g, p in pairs if g in positive and p in positive)
    fp = sum(1 for g, p in pairs if g not in positive and p in positive)
    fn = sum(1 for g, p in pairs if g in positive and p not in positive)
    tn = len(pairs) - tp - fp - fn
    return {**_prf(tp, fp, fn), "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def score(records: list[dict]) -> dict:
    """Run every record through the pipeline and score it."""
    cls_pairs: list[tuple[str, str]] = []
    hits: Counter[str] = Counter()
    latencies: list[float] = []

    for rec in records:
        gold = rec["labels"]
        t0 = time.perf_counter()
        _, v = analyse(rec["text"])
        latencies.append((time.perf_counter() - t0) * 1000)

        pred_cls = v.classification.value
        cls_pairs.append((gold["sif_classification"], pred_cls))
        hits["classification"] += pred_cls == gold["sif_classification"]
        hits["energy_source"] += (v.energy_source.value if v.energy_source else None) == gold[
            "energy_source"
        ]
        hits["control_status"] += v.control_status.value == gold["control_status"]
        hits["injury_outcome"] += v.injury_outcome.value == gold["injury_outcome"]
        hits["primary_lsr"] += (v.primary_lsr.value if v.primary_lsr else None) == gold[
            "primary_lsr"
        ]

    n = len(records)
    classes = sorted({g for g, _ in cls_pairs} | {p for _, p in cls_pairs})
    per_class = {c: _binary(cls_pairs, {c}) for c in classes}
    macro_f1 = statistics.fmean(per_class[c]["f1"] for c in classes) if classes else 0.0
    latencies.sort()

    return {
        "n": n,
        "precursor_detection": _binary(cls_pairs, PRECURSOR),
        "sif_potential_detection": _binary(cls_pairs, SIF_POTENTIAL),
        "accuracy": {k: round(hits[k] / n, 4) for k in (
            "classification", "energy_source", "control_status", "injury_outcome", "primary_lsr",
        )},
        "classification_macro_f1": round(macro_f1, 4),
        "per_class": per_class,
        "latency_ms": {
            "mean": round(statistics.fmean(latencies), 3),
            "p95": round(latencies[int(0.95 * (n - 1))], 3),
        },
    }


def run(corpus: Path = DEFAULT_CORPUS) -> dict:
    records = [json.loads(line) for line in corpus.read_text(encoding="utf-8").splitlines() if line.strip()]
    test = [r for r in records if r.get("meta", {}).get("split") == "test"]
    return {
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "engine_version": ENGINE_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "extractor_path": active_extractor(),
        "corpus": {
            "file": corpus.name,
            "records": len(records),
            "kind": "synthetic, gold-labelled by construction",
            "note": (
                "Generated OIL-style field reports with known labels. Real OIL "
                "reports have not been scored yet; expect lower numbers on them."
            ),
        },
        "headline_split": "test",
        "splits": {"test": score(test), "all": score(records)},
        "reproduce": "PYTHONPATH=backend python -m prahari.evaluation.metrics",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    result = run(args.corpus)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    t = result["splits"]["test"]
    pd = t["precursor_detection"]
    print(
        f"test n={t['n']}  precursor P={pd['precision']:.3f} R={pd['recall']:.3f} "
        f"F1={pd['f1']:.3f}  class acc={t['accuracy']['classification']:.3f}  "
        f"mean {t['latency_ms']['mean']} ms  -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
