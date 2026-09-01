"""The barrier prahari reports must always be a DIRECT control.

The three-part direct control test is the load-bearing idea of the whole
system: training, signage, permits and supervision are NOT barriers, and an
industry that treats them as barriers is the reason SIF rates stopped falling.

So it is not enough for the engine to *classify* correctly while naming an
indirect control as the thing that failed. `direct_control_key` is surfaced in
the triage queue and aggregated in /api/analytics/barriers; an indirect control
appearing there would tell an HSE manager to go fix the toolbox talk.

This test walks the entire corpus and asserts the invariant holds everywhere.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prahari.domain.controls import CONTROLS_BY_KEY
from prahari.ml import extract_facts
from prahari.rules.engine import evaluate

CORPUS = Path(__file__).resolve().parents[3] / "data" / "synthetic_reports.jsonl"


def _corpus() -> list[dict]:
    if not CORPUS.exists():  # pragma: no cover - regenerable with the generator CLI
        pytest.skip(f"corpus not generated at {CORPUS}")
    with CORPUS.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def test_reported_barrier_is_never_an_indirect_control() -> None:
    offenders: list[tuple[str, str]] = []
    for row in _corpus():
        verdict = evaluate(extract_facts(row["text"]))
        key = verdict.direct_control_key
        if key is not None and not CONTROLS_BY_KEY[key].is_direct:
            offenders.append((row["report_id"], key))

    assert not offenders, (
        f"{len(offenders)} report(s) name an INDIRECT control as the failed barrier. "
        f"First five: {offenders[:5]}"
    )


def test_an_indirect_control_still_reaches_the_rule_trace() -> None:
    """Suppressing it from the barrier column must not delete the evidence.

    R-CTRL-04 is what tells the reader that a control WAS named and why it does
    not count. Losing that would trade one wrong answer for a silent one.
    """
    named_indirect_seen = False
    for row in _corpus():
        verdict = evaluate(extract_facts(row["text"]))
        firing = next((f for f in verdict.fired_rules if f.rule_id == "R-CTRL-04"), None)
        if firing is None:
            continue
        named_indirect_seen = True
        assert verdict.direct_control_key is None
        assert not verdict.direct_control_effective

    assert named_indirect_seen, "corpus no longer exercises R-CTRL-04 at all"
