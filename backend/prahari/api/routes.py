"""API routes. No network calls anywhere in this module or anything it imports."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from prahari.api import analytics as an
from prahari.api.schemas import (
    AccumulationOut,
    AnalyzeIn,
    AnalyzeOut,
    MetaOut,
    BarriersOut,
    BulkResult,
    DensityOut,
    EvidenceSpanOut,
    IngestResult,
    LsrOut,
    Page,
    ReportDetail,
    ReportIn,
    ReportSummary,
    ReviewIn,
    ReviewOut,
    RuleFiringOut,
    SIFVerdictOut,
)
from prahari.api.service import parse_upload, persist, triage_rank, verdict_reason
from prahari.ml.extractor import EXTRACTOR_VERSION
from prahari.rules.engine import ENGINE_VERSION, analyse
from prahari.db.models import Report, Review, Verdict
from prahari.db.session import get_db
from prahari.domain.classification import SifClassification
from prahari.domain.energy import EnergySource
from prahari.domain.controls import ControlStatus
from prahari.domain.lsr import LIFE_SAVING_RULES, LifeSavingRule

router = APIRouter(prefix="/api")

EXCERPT_CHARS = 240


def _verdict_out(verdict: Verdict) -> SIFVerdictOut:
    firings = [
        RuleFiringOut(
            rule_id=f.rule_id,
            description=f.description,
            conclusion=f.conclusion,
            citation_key=f.citation_key,
            spans=[
                EvidenceSpanOut(
                    start=s.start_char, end=s.end_char, quoted_text=s.quoted_text, rule_id=f.rule_id
                )
                for s in f.spans
            ],
        )
        for f in verdict.rule_firings
    ]
    return SIFVerdictOut(
        classification=verdict.classification,
        energy_source=verdict.energy_source,
        high_energy=verdict.high_energy,
        high_energy_incident=verdict.high_energy_incident,
        control_status=verdict.control_status,
        direct_control_key=verdict.direct_control_key,
        direct_control_effective=verdict.direct_control_effective,
        injury_outcome=verdict.injury_outcome,
        primary_lsr=verdict.primary_lsr,
        secondary_lsr=verdict.secondary_lsr or [],
        evidence_completeness=verdict.evidence_completeness,
        triage_rank=verdict.triage_rank,
        engine_version=verdict.engine_version,
        extractor_version=verdict.extractor_version,
        fired_rules=firings,
    )


def _summary(report: Report, verdict: Verdict, reviewed: bool) -> ReportSummary:
    return ReportSummary(
        id=report.id,
        report_uid=report.report_uid,
        site=report.site,
        date=report.report_date,
        reporter_role=report.reporter_role,
        activity=report.activity,
        excerpt=report.text[:EXCERPT_CHARS],
        classification=verdict.classification,
        energy_source=verdict.energy_source,
        primary_lsr=verdict.primary_lsr,
        control_status=verdict.control_status,
        evidence_completeness=verdict.evidence_completeness,
        triage_rank=verdict.triage_rank,
        reviewed=reviewed,
        reason=verdict_reason(
            verdict.classification,
            verdict.direct_control_key,
            verdict.control_status,
            verdict.injury_outcome,
            verdict.energy_source,
        ),
    )


# -- Ingest -----------------------------------------------------------------


@router.post("/reports", response_model=IngestResult, status_code=status.HTTP_201_CREATED)
def ingest_report(payload: ReportIn, db: Session = Depends(get_db)) -> IngestResult:
    """Ingest one report: extract facts, run the rule engine, persist, return the verdict."""
    if payload.report_uid:
        existing = db.scalar(select(Report).where(Report.report_uid == payload.report_uid))
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, f"report_uid {payload.report_uid} exists")
    report = persist(
        db,
        text=payload.text,
        site=payload.site,
        report_date=payload.date,
        reporter_role=payload.reporter_role,
        activity=payload.activity,
        report_uid=payload.report_uid,
        source="api",
    )
    db.refresh(report)
    return IngestResult(
        id=report.id, report_uid=report.report_uid, verdict=_verdict_out(report.verdict)
    )


@router.post("/analyze", response_model=AnalyzeOut)
def analyze_text(payload: AnalyzeIn) -> AnalyzeOut:
    """Run extraction + the rule engine on ad-hoc text WITHOUT persisting it.

    Powers the Live Analysis panel. Deliberately has no database dependency:
    pasting a report to see what the engine says must not pollute the corpus,
    and the UI must never need a second copy of the engine to do it.
    """
    facts, verdict = analyse(payload.text)
    spans = [
        EvidenceSpanOut(
            start=s.start,
            end=s.end,
            quoted_text=facts.text[s.start : s.end],
            rule_id=firing.rule_id,
        )
        for firing in verdict.fired_rules
        for s in firing.spans
    ]
    out = SIFVerdictOut(
        classification=verdict.classification,
        energy_source=verdict.energy_source,
        high_energy=verdict.high_energy,
        high_energy_incident=verdict.high_energy_incident,
        control_status=verdict.control_status,
        direct_control_key=verdict.direct_control_key,
        direct_control_effective=verdict.direct_control_effective,
        injury_outcome=verdict.injury_outcome,
        primary_lsr=verdict.primary_lsr,
        secondary_lsr=list(verdict.secondary_lsr),
        evidence_completeness=verdict.evidence_completeness,
        triage_rank=triage_rank(verdict),
        engine_version=verdict.engine_version,
        extractor_version=EXTRACTOR_VERSION,
        fired_rules=[
            RuleFiringOut(
                rule_id=f.rule_id,
                description=f.description,
                conclusion=f.conclusion,
                citation_key=f.citation_key,
                spans=[
                    EvidenceSpanOut(
                        start=s.start,
                        end=s.end,
                        quoted_text=facts.text[s.start : s.end],
                        rule_id=f.rule_id,
                    )
                    for s in f.spans
                ],
            )
            for f in verdict.fired_rules
        ],
    )
    return AnalyzeOut(
        text=payload.text,
        verdict=out,
        evidence_spans=spans,
        reason=verdict_reason(
            verdict.classification.value,
            verdict.direct_control_key,
            verdict.control_status.value,
            verdict.injury_outcome.value,
            verdict.energy_source.value if verdict.energy_source else None,
        ),
    )


@router.get("/meta", response_model=MetaOut)
def meta(db: Session = Depends(get_db)) -> MetaOut:
    """Vocabulary for filter controls, plus what is actually in the database."""
    sites = [r for (r,) in db.execute(select(Report.site).distinct().order_by(Report.site)).all()]
    activities = [
        r
        for (r,) in db.execute(
            select(Report.activity).distinct().order_by(Report.activity)
        ).all()
        if r
    ]
    return MetaOut(
        sites=sites,
        activities=activities,
        classifications=[c.value for c in SifClassification],
        energy_sources=[e.value for e in EnergySource],
        control_statuses=[c.value for c in ControlStatus],
        life_saving_rules=[
            {"value": r.value, "short_name": LIFE_SAVING_RULES[r].short_name}
            for r in LifeSavingRule
        ],
        engine_version=ENGINE_VERSION,
        extractor_version=EXTRACTOR_VERSION,
        report_count=db.scalar(select(func.count()).select_from(Report)) or 0,
    )


@router.post("/reports/bulk", response_model=BulkResult)
async def ingest_bulk(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> BulkResult:
    """Ingest a JSONL or CSV upload.

    JSONL accepts either the plain ingest shape or a record from the synthetic
    corpus (which nests its text under `text` and its metadata elsewhere).
    """
    raw = await file.read()
    try:
        records = parse_upload(file.filename or "", raw)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"could not parse upload: {exc}") from exc

    ingested = 0
    skipped = 0
    errors: list[str] = []
    counts: dict[str, int] = {}

    for i, rec in enumerate(records, start=1):
        try:
            text = (rec.get("text") or "").strip()
            if not text:
                skipped += 1
                errors.append(f"row {i}: missing text")
                continue
            uid = rec.get("report_uid") or rec.get("report_id")
            if uid and db.scalar(select(Report.id).where(Report.report_uid == str(uid))):
                skipped += 1
                continue
            raw_date = rec.get("date") or rec.get("report_date")
            report_date = date.fromisoformat(str(raw_date)) if raw_date else date.today()
            report = persist(
                db,
                text=text,
                site=str(rec.get("site") or "(unspecified)"),
                report_date=report_date,
                reporter_role=rec.get("reporter_role"),
                activity=rec.get("activity"),
                report_uid=str(uid) if uid else None,
                source="bulk",
                commit=False,
            )
            db.flush()
            counts[report.verdict.classification] = counts.get(report.verdict.classification, 0) + 1
            ingested += 1
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            skipped += 1
            if len(errors) < 25:
                errors.append(f"row {i}: {exc}")

    db.commit()
    return BulkResult(
        received=len(records),
        ingested=ingested,
        skipped=skipped,
        errors=errors,
        classification_counts=counts,
    )


# -- Read -------------------------------------------------------------------


@router.get("/reports", response_model=Page)
def list_reports(
    db: Session = Depends(get_db),
    classification: list[SifClassification] | None = Query(default=None),
    lsr: list[LifeSavingRule] | None = Query(default=None),
    site: list[str] | None = Query(default=None),
    energy_source: list[EnergySource] | None = Query(default=None),
    date_from: date | None = None,
    date_to: date | None = None,
    min_confidence: float | None = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Filters on evidence_completeness: the fraction of required fact slots "
            "the extractor found evidence for. NOT a model probability."
        ),
    ),
    reviewed: bool | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> Page:
    """Paginated, filterable list of reports with their verdicts."""
    stmt = select(Report, Verdict).join(Verdict, Verdict.report_id == Report.id)
    if classification:
        stmt = stmt.where(Verdict.classification.in_([c.value for c in classification]))
    if lsr:
        stmt = stmt.where(Verdict.primary_lsr.in_([r.value for r in lsr]))
    if site:
        stmt = stmt.where(Report.site.in_(site))
    if energy_source:
        stmt = stmt.where(Verdict.energy_source.in_([e.value for e in energy_source]))
    if date_from:
        stmt = stmt.where(Report.report_date >= date_from)
    if date_to:
        stmt = stmt.where(Report.report_date <= date_to)
    if min_confidence is not None:
        stmt = stmt.where(Verdict.evidence_completeness >= min_confidence)

    reviewed_ids = {r for (r,) in db.execute(select(Review.report_id).distinct()).all()}
    if reviewed is not None:
        stmt = (
            stmt.where(Report.id.in_(reviewed_ids))
            if reviewed
            else stmt.where(Report.id.not_in(reviewed_ids or {-1}))
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(Report.report_date.desc(), Report.id.desc()).limit(limit).offset(offset)
    ).all()
    return Page(
        total=total,
        limit=limit,
        offset=offset,
        items=[_summary(r, v, r.id in reviewed_ids) for r, v in rows],
    )


@router.get("/triage", response_model=Page)
def triage(
    db: Session = Depends(get_db),
    site: list[str] | None = Query(default=None),
    include_actual_events: bool = Query(
        default=False, description="Also include HSIF/LSIF, not just uncontrolled potential."
    ),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> Page:
    """SIF potential only, ranked by deterministic triage rank then recency.

    `triage_rank` is a fixed table over the rule engine's own classes and control
    states, declared in `api/service.py`. It is not a model score.
    """
    wanted = [SifClassification.PSIF.value, SifClassification.EXPOSURE.value]
    if include_actual_events:
        wanted += [SifClassification.HSIF.value, SifClassification.LSIF.value]

    stmt = (
        select(Report, Verdict)
        .join(Verdict, Verdict.report_id == Report.id)
        .where(Verdict.classification.in_(wanted))
    )
    if site:
        stmt = stmt.where(Report.site.in_(site))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(Verdict.triage_rank.desc(), Report.report_date.desc(), Report.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    reviewed_ids = {r for (r,) in db.execute(select(Review.report_id).distinct()).all()}
    return Page(
        total=total,
        limit=limit,
        offset=offset,
        items=[_summary(r, v, r.id in reviewed_ids) for r, v in rows],
    )


@router.get("/reports/{report_id}", response_model=ReportDetail)
def get_report(report_id: int, db: Session = Depends(get_db)) -> ReportDetail:
    """Full detail including every evidence span, for text highlighting."""
    report = db.scalar(
        select(Report)
        .where(Report.id == report_id)
        .options(
            selectinload(Report.verdict).selectinload(Verdict.rule_firings),
            selectinload(Report.verdict).selectinload(Verdict.evidence_spans),
            selectinload(Report.reviews),
        )
    )
    if report is None or report.verdict is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "report not found")

    latest = report.reviews[-1] if report.reviews else None
    effective = report.verdict.classification
    if latest and latest.corrected_classification:
        effective = latest.corrected_classification

    return ReportDetail(
        id=report.id,
        report_uid=report.report_uid,
        text=report.text,
        site=report.site,
        date=report.report_date,
        reporter_role=report.reporter_role,
        activity=report.activity,
        source=report.source,
        ingested_at=report.ingested_at,
        verdict=_verdict_out(report.verdict),
        evidence_spans=[
            EvidenceSpanOut(
                start=s.start_char,
                end=s.end_char,
                quoted_text=s.quoted_text,
                rule_id=s.rule_firing.rule_id if s.rule_firing else None,
            )
            for s in report.verdict.evidence_spans
        ],
        reviews=[ReviewOut.model_validate(r) for r in report.reviews],
        effective_classification=effective,
    )


# -- Human in the loop ------------------------------------------------------


@router.patch("/reports/{report_id}/review", response_model=ReportDetail)
def review_report(report_id: int, payload: ReviewIn, db: Session = Depends(get_db)) -> ReportDetail:
    """Confirm or override a verdict.

    The correction is stored as a NEW row. The engine's verdict is never edited
    or deleted, so an auditor can always see what the system said before a human
    touched it, and the gap between the two is the training signal for the next
    model.
    """
    report = db.scalar(select(Report).where(Report.id == report_id))
    if report is None or report.verdict is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "report not found")

    if payload.decision == "override" and not payload.has_correction():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "an override must supply at least one corrected_* field",
        )

    db.add(
        Review(
            report_id=report.id,
            verdict_id=report.verdict.id,
            reviewer_role=payload.reviewer_role,
            decision=payload.decision,
            reason=payload.reason,
            corrected_classification=(
                payload.corrected_classification.value if payload.corrected_classification else None
            ),
            corrected_energy_source=(
                payload.corrected_energy_source.value if payload.corrected_energy_source else None
            ),
            corrected_control_status=(
                payload.corrected_control_status.value if payload.corrected_control_status else None
            ),
            corrected_primary_lsr=(
                payload.corrected_primary_lsr.value if payload.corrected_primary_lsr else None
            ),
        )
    )
    db.commit()
    return get_report(report_id, db)


# -- Analytics --------------------------------------------------------------


@router.get("/analytics/density", response_model=DensityOut)
def analytics_density(
    db: Session = Depends(get_db),
    date_from: date | None = None,
    date_to: date | None = None,
) -> DensityOut:
    """SIF-precursor density per site x activity: count and rate, for the heatmap."""
    return DensityOut(**an.density(db, since=date_from, until=date_to))


@router.get("/analytics/lsr", response_model=LsrOut)
def analytics_lsr(
    db: Session = Depends(get_db),
    date_from: date | None = None,
    date_to: date | None = None,
    site: str | None = None,
) -> LsrOut:
    """Distribution across the nine Life-Saving Rules. Zero-count rules are returned."""
    return LsrOut(**an.lsr_distribution(db, since=date_from, until=date_to, site=site))


@router.get("/analytics/barriers", response_model=BarriersOut)
def analytics_barriers(
    db: Session = Depends(get_db),
    window_days: int = Query(default=an.DEFAULT_WINDOW_DAYS, ge=7, le=1825),
    site: str | None = None,
    as_of: date | None = None,
    limit: int = Query(default=40, ge=1, le=200),
) -> BarriersOut:
    """Recurring barrier-failure patterns: which control fails, where, trending."""
    return BarriersOut(
        **an.barrier_patterns(db, window_days=window_days, site=site, as_of=as_of, limit=limit)
    )


@router.get("/analytics/accumulation", response_model=AccumulationOut)
def analytics_accumulation(
    db: Session = Depends(get_db),
    window_days: int = Query(default=an.DEFAULT_WINDOW_DAYS, ge=7, le=1825),
    half_life_days: float = Query(default=an.DEFAULT_HALF_LIFE_DAYS, gt=0, le=3650),
    repeat_exponent: float = Query(default=an.REPEAT_EXPONENT, ge=1.0, le=3.0),
    site: str | None = None,
    as_of: date | None = None,
    min_index: float = Query(default=0.0, ge=0.0),
) -> AccumulationOut:
    """PRECURSOR ACCUMULATION INDEX per site x energy source.

    Rises when the SAME barrier failure repeats at the SAME place inside a
    rolling window, because that repetition - not any single report - is the
    pattern that precedes an actual event. Every score returns the contributing
    report ids and their decayed weights, so it can be recomputed by hand.
    """
    return AccumulationOut(
        **an.accumulation(
            db,
            window_days=window_days,
            half_life_days=half_life_days,
            repeat_exponent=repeat_exponent,
            site=site,
            as_of=as_of,
            min_index=min_index,
        )
    )
