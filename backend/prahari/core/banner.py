"""Startup banner.

Printed on API boot and by the CLI. Its job is to answer, at a glance and
without anyone opening a terminal tab, the three questions a judge or a
sceptical engineer will ask in the first ten seconds:

  * which extraction path is live — the trained ONNX model, or the deterministic
    keyword fallback? (Claiming a model is running when it silently fell back
    would be the single most damaging thing this project could do to itself.)
  * how many reports are actually in the database?
  * is anything reaching the network?

No colour codes by default: this has to be legible in a projector-washed
terminal on a laptop that is not ours.
"""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass

WIDTH = 66


@dataclass(frozen=True, slots=True)
class BannerFacts:
    extractor: str
    extractor_detail: str
    engine_version: str
    model_present: bool
    model_note: str
    report_count: int | str
    db_path: str
    python: str


def collect(report_count: int | str = "?") -> BannerFacts:
    from prahari.ml import active_extractor
    from prahari.ml.neural_extractor import model_status
    from prahari.rules.engine import ENGINE_VERSION

    status = model_status()
    active = active_extractor()

    if active.startswith("neural"):
        detail = f"ONNX token classifier ({active.split(':', 1)[1]} mode)"
        note = status.onnx_path
    elif os.environ.get("PRAHARI_EXTRACTOR", "").lower() == "keyword":
        detail = "keyword matcher (pinned by PRAHARI_EXTRACTOR=keyword)"
        note = "model not consulted"
    else:
        detail = "keyword matcher (deterministic fallback)"
        note = status.reason

    from prahari.core.config import get_settings
    from prahari.db.session import resolved_db_path

    db = resolved_db_path() or str(get_settings().db_path)
    if resolved_db_path() and resolved_db_path() != str(get_settings().db_path):
        db += "   (relocated: the configured folder cannot host SQLite)"

    return BannerFacts(
        extractor="NEURAL" if active.startswith("neural") else "KEYWORD",
        extractor_detail=detail,
        engine_version=ENGINE_VERSION,
        model_present=status.loaded,
        model_note=note,
        report_count=report_count,
        db_path=db,
        python=platform.python_version(),
    )


def count_reports() -> int | str:
    try:
        from sqlalchemy import func, select

        from prahari.db.models import Report
        from prahari.db.session import session_scope

        with session_scope() as db:
            return db.scalar(select(func.count()).select_from(Report)) or 0
    except Exception:  # noqa: BLE001 — a banner must never break startup
        return "unavailable"


def render(facts: BannerFacts) -> str:
    bar = "=" * WIDTH

    def row(label: str, value: str) -> str:
        return f"  {label:<16}{value}"

    marker = "[OK]" if facts.extractor == "NEURAL" else "[--]"
    lines = [
        "",
        bar,
        "  prahari  ·  SIF precursor detection  ·  100% OFFLINE".ljust(WIDTH),
        bar,
        row("extraction", f"{marker} {facts.extractor}  —  {facts.extractor_detail}"),
        row("", f"     {facts.model_note}"),
        row("rule engine", facts.engine_version),
        row("reports in db", str(facts.report_count)),
        row("database", facts.db_path),
        row("python", facts.python),
        bar,
    ]
    if facts.report_count == 0:
        lines.append("  NO DATA — run:  python -m prahari.cli seed --limit 800")
        lines.append(bar)
    if facts.extractor == "KEYWORD":
        lines.append("  Running the deterministic path. Every verdict is still fully")
        lines.append("  traceable to a named rule; only span detection is lexicon-based.")
        lines.append(bar)
    lines.append("")
    return "\n".join(lines)


def print_banner(stream=None) -> BannerFacts:  # noqa: ANN001
    facts = collect(count_reports())
    print(render(facts), file=stream or sys.stdout, flush=True)
    return facts
