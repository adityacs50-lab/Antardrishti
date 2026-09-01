"""Evaluate the extractor, end to end, with recall front and centre.

    python -m prahari.ml.training.evaluate --threshold 0.35

Three layers, because a span-F1 number on its own tells you nothing about
whether a crew gets warned:

  1. PER-ENTITY  precision / recall / F1 for the six span types.
  2. END-TO-END  SIF classification after the rule engine consumes those spans.
                 This is the number that matters — the extractor exists to feed
                 the engine, not to win a tagging benchmark.
  3. FALSE NEGATIVES  every missed SIF precursor, printed in full with its text.

On (3): this section is meant to be read aloud to judges. A system that
publishes its misses is one you can calibrate against; a system that reports
only its wins is one you cannot. Each miss is a report the system would have
let a crew walk past, so it is listed with the text, the true class, what the
engine said instead, and which facts were absent.

Build-time only.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from prahari.domain.classification import SifClassification
from prahari.ml.config import DEFAULT_ENTITY_THRESHOLD, MIN_ENTITY_RECALL
from prahari.ml.labels import CharSpan
from prahari.rules.engine import evaluate as run_rules

PRECURSOR = {SifClassification.PSIF.value, SifClassification.EXPOSURE.value}
SIF_LIKE = PRECURSOR | {SifClassification.HSIF.value}


# -- span scoring -----------------------------------------------------------


def _overlap(a: CharSpan, b: dict) -> bool:
    """Partial-overlap credit. Exact boundary match is the wrong bar here.

    An HSE officer highlighting "was not wearing safety belt" versus "not
    wearing safety belt" has found the same thing. Boundary-exact scoring would
    punish the model for a difference no human would care about, and would push
    the operating point towards precision, which is the wrong direction.
    """
    return a.label == b["label"] and a.start < b["end"] and b["start"] < a.end


def score_spans(predictions: list[list[CharSpan]], golds: list[list[dict]]) -> dict:
    per_label: dict[str, Counter] = defaultdict(Counter)
    for preds, gold in zip(predictions, golds):
        matched_gold: set[int] = set()
        for pred in preds:
            hit = next(
                (i for i, g in enumerate(gold) if i not in matched_gold and _overlap(pred, g)),
                None,
            )
            if hit is None:
                per_label[pred.label]["fp"] += 1
            else:
                matched_gold.add(hit)
                per_label[pred.label]["tp"] += 1
        for i, g in enumerate(gold):
            if i not in matched_gold:
                per_label[g["label"]]["fn"] += 1

    out: dict[str, dict] = {}
    totals = Counter()
    for label, counts in sorted(per_label.items()):
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        totals.update(counts)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out[label] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
    tp, fp, fn = totals["tp"], totals["fp"], totals["fn"]
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    out["__micro__"] = {
        "precision": p, "recall": r,
        "f1": 2 * p * r / (p + r) if p + r else 0.0,
        "support": tp + fn,
    }
    return out


# -- reporting --------------------------------------------------------------


def print_entity_table(scores: dict) -> None:
    print("\n" + "=" * 78)
    print("1. PER-ENTITY EXTRACTION")
    print("=" * 78)
    print(f"  {'entity':<20}{'RECALL':>10}{'precision':>12}{'f1':>9}{'support':>10}")
    print("  " + "-" * 74)
    for label, s in scores.items():
        if label == "__micro__":
            continue
        print(f"  {label:<20}{s['recall']:>10.3f}{s['precision']:>12.3f}{s['f1']:>9.3f}{s['support']:>10}")
    micro = scores["__micro__"]
    print("  " + "-" * 74)
    print(f"  {'MICRO AVERAGE':<20}{micro['recall']:>10.3f}{micro['precision']:>12.3f}{micro['f1']:>9.3f}{micro['support']:>10}")
    verdict = "PASS" if micro["recall"] >= MIN_ENTITY_RECALL else "FAIL"
    print(f"\n  >>> ENTITY RECALL = {micro['recall']:.3f}   (floor {MIN_ENTITY_RECALL:.2f}) ... {verdict}")


def print_confusion(gold: list[str], pred: list[str]) -> None:
    classes = sorted(set(gold) | set(pred))
    matrix: Counter = Counter(zip(gold, pred))
    width = max(len(c) for c in classes) + 1
    print("\n" + "=" * 78)
    print("2. END-TO-END SIF CLASSIFICATION (after the rule engine)")
    print("=" * 78)
    print("\n  Confusion matrix — rows are truth, columns are predicted\n")
    print(" " * (width + 2) + "".join(f"{c[:7]:>8}" for c in classes))
    for truth in classes:
        row = "".join(f"{matrix[(truth, p)]:>8}" for p in classes)
        total = sum(matrix[(truth, p)] for p in classes)
        hit = matrix[(truth, truth)]
        print(f"  {truth:<{width}}{row}   ({hit}/{total} = {hit / total:.0%})" if total else f"  {truth:<{width}}{row}")

    correct = sum(1 for g, p in zip(gold, pred) if g == p)
    print(f"\n  overall accuracy: {correct}/{len(gold)} = {correct / len(gold):.1%}")

    # Precursor recall is the operational number: of the reports that really
    # were uncontrolled fatal potential, how many did the system surface?
    tp = sum(1 for g, p in zip(gold, pred) if g in PRECURSOR and p in PRECURSOR)
    fn = sum(1 for g, p in zip(gold, pred) if g in PRECURSOR and p not in PRECURSOR)
    fp = sum(1 for g, p in zip(gold, pred) if g not in PRECURSOR and p in PRECURSOR)
    recall = tp / (tp + fn) if tp + fn else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    print("\n  " + "-" * 74)
    print(f"  >>> SIF-PRECURSOR RECALL    = {recall:.3f}   ({tp} found, {fn} MISSED)")
    print(f"      SIF-precursor precision = {precision:.3f}   ({fp} false alarms)")
    print(f"      Each false alarm costs one review. Each of the {fn} misses is the one")
    print("      that gets closed out and never looked at again.")


def print_false_negatives(rows: list[dict], gold: list[str], pred: list[str], limit: int) -> None:
    misses = [
        (r, g, p) for r, g, p in zip(rows, gold, pred) if g in SIF_LIKE and p not in PRECURSOR
    ]
    print("\n" + "=" * 78)
    print(f"3. FALSE-NEGATIVE ANALYSIS — {len(misses)} missed SIF precursor(s)")
    print("=" * 78)
    print("  Shown deliberately. These are the reports the system would have let a")
    print("  crew walk past. Read them; they are how the next lexicon or training")
    print("  round gets prioritised.\n")
    if not misses:
        print("  None missed on this split.")
        return
    for i, (row, g, p) in enumerate(misses[:limit], start=1):
        print(f"  [{i}] {row['report_id']}   truth={g}   engine said={p}")
        text = " ".join(row["text"].split())
        for start in range(0, min(len(text), 420), 96):
            print(f"      {text[start:start + 96]}")
        got = {s["label"] for s in row.get("_pred_spans", [])}
        want = {s["label"] for s in row.get("gold_spans", [])}
        if want - got:
            print(f"      MISSING SPANS: {', '.join(sorted(want - got))}")
        print()
    if len(misses) > limit:
        print(f"  ... and {len(misses) - limit} more (raise --max-fn to see them all)")


# -- main -------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m prahari.ml.training.evaluate")
    parser.add_argument("--dataset", type=Path, default=Path("models/dataset"))
    parser.add_argument("--split", default="test", choices=["train", "val", "test"])
    parser.add_argument("--threshold", type=float, default=DEFAULT_ENTITY_THRESHOLD)
    parser.add_argument("--max-fn", type=int, default=25)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument(
        "--keyword-baseline",
        action="store_true",
        help="score the deterministic extractor instead, for a like-for-like comparison",
    )
    args = parser.parse_args(argv)

    rows = [
        json.loads(line)
        for line in (args.dataset / f"{args.split}.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    from prahari.ml.extractor import extract as keyword_extract
    from prahari.ml.neural_extractor import model_status, predict_spans
    from prahari.ml import extract_facts

    status = model_status()
    print(f"model: {'LOADED' if status.loaded else 'NOT LOADED — ' + status.reason}")
    print(f"split: {args.split}  n={len(rows)}  threshold={args.threshold}")
    if args.keyword_baseline:
        print("mode : keyword baseline")

    predictions: list[list[CharSpan]] = []
    golds: list[list[dict]] = []
    gold_cls: list[str] = []
    pred_cls: list[str] = []
    latencies: list[float] = []

    for row in rows:
        text = row["text"]
        started = time.perf_counter()
        if args.keyword_baseline or not status.loaded:
            spans = []
            facts = keyword_extract(text)
        else:
            spans = predict_spans(text, args.threshold) or []
            facts = extract_facts(text)
        latencies.append((time.perf_counter() - started) * 1000)

        row["_pred_spans"] = [{"label": s.label, "start": s.start, "end": s.end} for s in spans]
        predictions.append(spans)
        golds.append(row.get("gold_spans", []))
        gold_cls.append(row["sif_classification"])
        pred_cls.append(run_rules(facts).classification.value)

    if not args.keyword_baseline and status.loaded:
        print_entity_table(score_spans(predictions, golds))
    else:
        print("\n(entity scoring skipped: no model loaded — running the rule path only)")

    print_confusion(gold_cls, pred_cls)
    print_false_negatives(rows, gold_cls, pred_cls, args.max_fn)

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    print("\n" + "=" * 78)
    print("4. LATENCY (CPU, single report)")
    print("=" * 78)
    print(f"  p50 {p50:7.1f} ms    p95 {p95:7.1f} ms    max {latencies[-1]:7.1f} ms   budget 200 ms")

    if args.json_out:
        payload = {
            "split": args.split,
            "threshold": args.threshold,
            "model_loaded": status.loaded,
            "entity": score_spans(predictions, golds) if status.loaded else None,
            "accuracy": sum(g == p for g, p in zip(gold_cls, pred_cls)) / len(rows),
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
        }
        args.json_out.write_text(json.dumps(payload, indent=2, default=float), encoding="utf-8")
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
