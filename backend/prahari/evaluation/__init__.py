"""Measured engine performance, reproducible from the committed corpus.

    PYTHONPATH=backend python -m prahari.evaluation.metrics

writes `engine_metrics.json` next to this file. The API serves that file
verbatim at `GET /api/engine-metrics`; the dashboard's Engine Performance card
renders it. Nothing on that card is typed in by hand - every number traces back
to a run of this module against `data/synthetic_reports.jsonl`.
"""

from __future__ import annotations

import json
from pathlib import Path

METRICS_PATH = Path(__file__).with_name("engine_metrics.json")


def load_metrics() -> dict | None:
    """The last committed benchmark run, or None if it was never run."""
    try:
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
