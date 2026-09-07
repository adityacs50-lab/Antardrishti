"""Analytics, including the Precursor Accumulation Index.

THE PRECURSOR ACCUMULATION INDEX
--------------------------------
The claim this system rests on is not "we can spot a dangerous report". It is
that *the same barrier failing repeatedly at the same place* is the pattern
that precedes an actual event, and that this pattern is invisible in a normal
incident dashboard because each individual report is unremarkable and closed
out on its own.

So the index scores a (site, energy source) pair, and it is deliberately NOT a
simple count:

  1. Only precursors and actual high-energy events count. Controlled work
     (Capacity, Success) and low-energy incidents contribute nothing.
  2. Every contributing report is exponentially time-decayed, so a cluster from
     two years ago fades and a cluster from last month does not.
  3. Reports are grouped by BARRIER SIGNATURE - the (control, control status)
     pair. "Fall arrest absent" and "fall arrest not followed" are different
     signatures.
  4. Each signature's decayed count is raised to an exponent above 1. This is
     the whole point: three failures of the SAME barrier score higher than one
     failure each of three different barriers. Repetition is the signal.
  5. The result is banded and compared against the previous window to give a
     direction of travel.

Every number is reproducible by hand from the contributing report ids, which
are returned with the score. There is no model here, and no learned weight -
the constants are declared below and can be argued with.

WHY THE WEIGHTS ARE NOT A SEVERITY MODEL
----------------------------------------
`CLASS_WEIGHT` assigns a fixed multiplier to each SCL class. That is an
ordering chosen by us over classes that a deterministic table produced - not a
severity a model inferred from text. It is declared, auditable and constant.
CLAUDE.md forbids a model emitting a severity; it does not forbid the rule
layer from ranking its own deterministic output.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from prahari.domain.classification import SifClassification
from prahari.domain.controls import CONTROLS_BY_KEY, ControlStatus
from prahari.domain.energy import EnergySource
from prahari.domain.lsr import LIFE_SAVING_RULES, LifeSavingRule
from prahari.db.models import Report, Verdict

# -- Constants (declared, auditable, arguable) ------------------------------

#: Classes that count towards accumulation, and how much each is worth.
CLASS_WEIGHT: dict[SifClassification, float] = {
    SifClassification.HSIF: 5.0,
    SifClassification.PSIF: 3.0,
    SifClassification.EXPOSURE: 2.0,
}

DEFAULT_WINDOW_DAYS = 180
DEFAULT_HALF_LIFE_DAYS = 45.0
#: Above 1.0 so repeats escalate super-linearly WITHIN one barrier signature.
REPEAT_EXPONENT = 1.6

#: How much a SECOND, unrelated barrier failure at the same place adds.
#: Deliberately heavily discounted. Summing signatures linearly would let four
#: unrelated one-off failures outscore two repeats of the same barrier - which
#: is the exact inversion of what this index claims to measure. The strongest
#: repeated signature therefore dominates, and variety is a minor addition.
DIVERSITY_DISCOUNT = 0.35

BANDS: dict[str, float] = {"watch": 0.0, "elevated": 8.0, "high": 20.0, "critical": 40.0}

PRECURSOR_CLASSES = (SifClassification.PSIF.value, SifClassification.EXPOSURE.value)


def _band(score: float) -> str:
    label = "watch"
    for name, threshold in BANDS.items():
        if score >= threshold:
            label = name
    return label


def _trend(recent: float, previous: float, min_history: float = 1e-9) -> str:
    if previous <= min_history and recent <= min_history:
        return "insufficient_history"
    if previous <= min_history:
        return "rising"
    ratio = recent / previous
    if ratio > 1.15:
        return "rising"
    if ratio < 0.85:
        return "falling"
    return "flat"


@dataclass(frozen=True, slots=True)
class _Row:
    report_id: int
    report_uid: str
    site: str
    activity: str | None
    day: date
    classification: str
    energy_source: str | None
    control_key: str | None
    control_status: str


def _load_rows(
    db: Session,
    *,
    since: date | None = None,
    until: date | None = None,
    site: str | None = None,
) -> list[_Row]:
    stmt = select(Report, Verdict).join(Verdict, Verdict.report_id == Report.id)
    if since is not None:
        stmt = stmt.where(Report.report_date >= since)
    if until is not None:
        stmt = stmt.where(Report.report_date <= until)
    if site is not None:
        stmt = stmt.where(Report.site == site)
    return [
        _Row(
            report_id=r.id,
            report_uid=r.report_uid,
            site=r.site,
            activity=r.activity,
            day=r.report_date,
            classification=v.classification,
            energy_source=v.energy_source,
            control_key=v.direct_control_key,
            control_status=v.control_status,
        )
        for r, v in db.execute(stmt).all()
    ]


# -- Density ----------------------------------------------------------------


def density(
    db: Session, *, since: date | None = None, until: date | None = None
) -> dict:
    """SIF-precursor density per site x activity: count and rate."""
    rows = _load_rows(db, since=since, until=until)
    totals: Counter = Counter()
    precursors: Counter = Counter()
    for row in rows:
        activity = row.activity or "(unspecified)"
        totals[(row.site, activity)] += 1
        if row.classification in PRECURSOR_CLASSES:
            precursors[(row.site, activity)] += 1

    cells = [
        {
            "site": site,
            "activity": activity,
            "total_reports": total,
            "precursor_count": precursors[(site, activity)],
            "precursor_rate": round(precursors[(site, activity)] / total, 4) if total else 0.0,
        }
        for (site, activity), total in sorted(totals.items())
    ]
    window = (until - since).days if since and until else None
    return {
        "window_days": window,
        "sites": sorted({c["site"] for c in cells}),
        "activities": sorted({c["activity"] for c in cells}),
        "cells": sorted(cells, key=lambda c: (-c["precursor_count"], c["site"])),
    }


# -- Life-Saving Rule distribution -----------------------------------------


def lsr_distribution(
    db: Session, *, since: date | None = None, until: date | None = None, site: str | None = None
) -> dict:
    """Distribution across all nine rules. Rules with zero are still returned."""
    counts: Counter = Counter()
    precursor_counts: Counter = Counter()
    stmt = select(Report, Verdict).join(Verdict, Verdict.report_id == Report.id)
    if since is not None:
        stmt = stmt.where(Report.report_date >= since)
    if until is not None:
        stmt = stmt.where(Report.report_date <= until)
    if site is not None:
        stmt = stmt.where(Report.site == site)

    total = 0
    unassigned = 0
    unassigned_illegible = 0
    unassigned_no_energy = 0
    precursor_total = 0
    precursor_assigned = 0
    for _, v in db.execute(stmt).all():
        total += 1
        is_precursor = v.classification in PRECURSOR_CLASSES
        precursor_total += is_precursor
        if not v.primary_lsr:
            unassigned += 1
            # Two different things, and conflating them misreads the engine.
            # An illegible report never reached the LSR rules at all
            # (R-INSUFF-01 returns before them). A report that *was* classified
            # but names no energy source is one the nine rules — a fatality
            # prevention set — do not address; leaving it untagged is the
            # designed behaviour, not a coverage hole.
            if v.classification == SifClassification.INSUFFICIENT_INFORMATION.value:
                unassigned_illegible += 1
            else:
                unassigned_no_energy += 1
            continue
        counts[v.primary_lsr] += 1
        precursor_assigned += is_precursor
        if is_precursor:
            precursor_counts[v.primary_lsr] += 1

    assigned = sum(counts.values())
    buckets = [
        {
            "lsr": rule.value,
            "short_name": LIFE_SAVING_RULES[rule].short_name,
            "count": counts.get(rule.value, 0),
            "precursor_count": precursor_counts.get(rule.value, 0),
            "share": round(counts.get(rule.value, 0) / assigned, 4) if assigned else 0.0,
        }
        for rule in LifeSavingRule
    ]
    buckets.sort(key=lambda b: -b["count"])
    return {
        "total": total,
        "assigned": assigned,
        "unassigned": unassigned,
        "unassigned_illegible": unassigned_illegible,
        "unassigned_no_energy": unassigned_no_energy,
        # Coverage over the reports that matter. A rule tag on an illegible
        # report would be an invention; a rule tag on every precursor is the
        # thing an HSE officer actually needs, so that is what gets reported.
        "precursor_total": precursor_total,
        "precursor_assigned": precursor_assigned,
        "buckets": buckets,
    }


# -- Barrier failure patterns ----------------------------------------------


def barrier_patterns(
    db: Session,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    site: str | None = None,
    as_of: date | None = None,
    limit: int = 40,
) -> dict:
    """Which control fails most often, where, and whether it is trending."""
    as_of = as_of or date.today()
    window_start = as_of - timedelta(days=window_days)
    previous_start = window_start - timedelta(days=window_days)

    rows = _load_rows(db, since=previous_start, until=as_of, site=site)
    failing = [
        r
        for r in rows
        if r.control_key
        and r.control_status
        != ControlStatus.PRESENT_VERIFIED.value
        and r.classification in (*PRECURSOR_CLASSES, SifClassification.HSIF.value)
    ]

    grouped: dict[tuple[str, str | None, str], list[_Row]] = defaultdict(list)
    for r in failing:
        grouped[(r.control_key, r.energy_source, r.site)].append(r)

    patterns = []
    for (control_key, energy, site_name), group in grouped.items():
        recent = [r for r in group if r.day >= window_start]
        previous = [r for r in group if previous_start <= r.day < window_start]
        if not recent:
            continue
        control = CONTROLS_BY_KEY.get(control_key)
        days = [r.day for r in recent]
        patterns.append(
            {
                "control_key": control_key,
                "control_label": control.label if control else control_key,
                "control_class": control.control_class.value if control else "unknown",
                "energy_source": energy,
                "site": site_name,
                "failure_count": len(recent),
                "statuses": dict(Counter(r.control_status for r in recent)),
                "first_seen": min(days),
                "last_seen": max(days),
                "recent_count": len(recent),
                "previous_count": len(previous),
                "trend": _trend(len(recent), len(previous)),
            }
        )

    patterns.sort(key=lambda p: (-p["failure_count"], p["control_key"]))
    return {"window_days": window_days, "patterns": patterns[:limit]}


# -- The Precursor Accumulation Index --------------------------------------


def accumulation(
    db: Session,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    repeat_exponent: float = REPEAT_EXPONENT,
    site: str | None = None,
    as_of: date | None = None,
    min_index: float = 0.0,
) -> dict:
    """Rising score where the same barrier failure repeats at one site+energy.

    Reproducible by hand: every contributing report id and its decayed weight
    is returned alongside the score.
    """
    as_of = as_of or date.today()
    window_start = as_of - timedelta(days=window_days)
    previous_start = window_start - timedelta(days=window_days)

    rows = [
        r
        for r in _load_rows(db, since=previous_start, until=as_of, site=site)
        if r.energy_source and r.classification in {c.value for c in CLASS_WEIGHT}
    ]

    def score_window(subset: list[_Row], reference: date) -> tuple[float, list[dict], int]:
        by_signature: dict[tuple[str, str], list[_Row]] = defaultdict(list)
        for r in subset:
            by_signature[(r.control_key or "(control not named in report)", r.control_status)].append(r)

        contributions: list[float] = []
        signatures = []
        max_repeat = 0
        for (control_key, status), group in by_signature.items():
            contributors = []
            decayed_total = 0.0
            weighted_total = 0.0
            for r in group:
                age = max((reference - r.day).days, 0)
                decay = 0.5 ** (age / half_life_days)
                weight = CLASS_WEIGHT[SifClassification(r.classification)]
                decayed_total += decay
                weighted_total += decay * weight
                contributors.append(
                    {
                        "report_id": r.report_id,
                        "report_uid": r.report_uid,
                        "date": r.day,
                        "classification": r.classification,
                        "control_status": r.control_status,
                        "age_days": age,
                        "decayed_weight": round(decay * weight, 4),
                    }
                )
            if decayed_total <= 0:
                continue
            # Repetition escalates: the mean weight is scaled by the decayed
            # count raised to an exponent above one.
            mean_weight = weighted_total / decayed_total
            contribution = mean_weight * (decayed_total**repeat_exponent)
            contributions.append(contribution)
            max_repeat = max(max_repeat, len(group))
            control = CONTROLS_BY_KEY.get(control_key)
            contributors.sort(key=lambda c: c["date"], reverse=True)
            signatures.append(
                {
                    "control_key": control_key,
                    "control_label": control.label if control else control_key,
                    "control_status": status,
                    "occurrences": len(group),
                    "decayed_occurrences": round(decayed_total, 4),
                    "contribution": round(contribution, 4),
                    "contributors": contributors,
                }
            )
        signatures.sort(key=lambda s: -s["contribution"])
        # The strongest repeated signature dominates; everything else is
        # discounted. See DIVERSITY_DISCOUNT.
        contributions.sort(reverse=True)
        total = (
            contributions[0] + DIVERSITY_DISCOUNT * sum(contributions[1:])
            if contributions
            else 0.0
        )
        return total, signatures, max_repeat

    by_cell: dict[tuple[str, str], list[_Row]] = defaultdict(list)
    for r in rows:
        by_cell[(r.site, r.energy_source)].append(r)

    cells = []
    for (site_name, energy), group in by_cell.items():
        recent = [r for r in group if r.day >= window_start]
        previous = [r for r in group if previous_start <= r.day < window_start]
        if not recent:
            continue
        index, signatures, max_repeat = score_window(recent, as_of)
        prev_index, _, _ = score_window(previous, window_start)
        if index < min_index:
            continue

        top = signatures[0] if signatures else None
        n_sig = len(signatures)
        if top and top["occurrences"] > 1:
            explanation = (
                f"'{top['control_label']}' was {top['control_status'].replace('_', ' ')} "
                f"{top['occurrences']} times at {site_name} for {energy} energy within "
                f"{window_days} days. Repetition of ONE barrier failure at ONE place is "
                f"the pattern that precedes an event, so it escalates faster than the "
                f"same number of unrelated failures would. "
                f"{len(recent)} contributing precursor(s) across {n_sig} distinct "
                f"barrier signature(s)."
            )
        elif top:
            explanation = (
                f"{len(recent)} precursor(s) at {site_name} for {energy} energy across "
                f"{n_sig} distinct barrier signature(s), none of them yet repeating. "
                f"Strongest is '{top['control_label']}' "
                f"{top['control_status'].replace('_', ' ')}. Unrelated one-off failures "
                f"are discounted relative to a repeat, so this stays low until the same "
                f"barrier fails again here."
            )
        else:
            explanation = "No contributing precursors in the window."

        cells.append(
            {
                "site": site_name,
                "energy_source": energy,
                "index": round(index, 4),
                "band": _band(index),
                "total_precursors": len(recent),
                "max_repeat": max_repeat,
                "trend": _trend(index, prev_index),
                "previous_index": round(prev_index, 4),
                "signatures": signatures,
                "explanation": explanation,
            }
        )

    cells.sort(key=lambda c: -c["index"])
    return {
        "window_days": window_days,
        "half_life_days": half_life_days,
        "repeat_exponent": repeat_exponent,
        "diversity_discount": DIVERSITY_DISCOUNT,
        "bands": BANDS,
        "as_of": as_of,
        "cells": cells,
    }
