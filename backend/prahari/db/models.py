"""SQLAlchemy models.

The one structural rule that matters here: a Verdict is IMMUTABLE. When an HSE
officer disagrees, a Review row is written alongside it. The engine's original
output is never edited or deleted, because the audit question a safety
professional will ask is "what did the system say before a human touched it",
and a system that overwrites itself cannot answer.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Report(Base):
    """One safety report as submitted. Never modified after ingest."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    site: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    report_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    reporter_role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    activity: Mapped[str | None] = mapped_column(String(160), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="api", nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    verdict: Mapped["Verdict"] = relationship(
        back_populates="report", uselist=False, cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", order_by="Review.created_at"
    )


class Verdict(Base):
    """The engine's output. Immutable by convention and by API surface."""

    __tablename__ = "verdicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), unique=True, index=True
    )

    classification: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    energy_source: Mapped[str | None] = mapped_column(String(32), index=True)
    high_energy: Mapped[bool] = mapped_column(Boolean, default=False)
    high_energy_incident: Mapped[bool] = mapped_column(Boolean, default=False)
    control_status: Mapped[str] = mapped_column(String(32), index=True)
    direct_control_key: Mapped[str | None] = mapped_column(String(64), index=True)
    direct_control_effective: Mapped[bool] = mapped_column(Boolean, default=False)
    injury_outcome: Mapped[str] = mapped_column(String(32), index=True)
    primary_lsr: Mapped[str | None] = mapped_column(String(48), index=True)
    secondary_lsr: Mapped[list] = mapped_column(JSON, default=list)

    #: Fraction of required fact slots the extractor found evidence for.
    #: NOT a probability and NOT a severity - see the API docs.
    evidence_completeness: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    #: Deterministic ordering key for triage. Derived from the class and the
    #: control state by a fixed table, never by a model.
    triage_rank: Mapped[int] = mapped_column(Integer, default=0, index=True)

    engine_version: Mapped[str] = mapped_column(String(32))
    extractor_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    report: Mapped[Report] = relationship(back_populates="verdict")
    rule_firings: Mapped[list["RuleFiringRow"]] = relationship(
        back_populates="verdict", cascade="all, delete-orphan", order_by="RuleFiringRow.ordinal"
    )
    evidence_spans: Mapped[list["EvidenceSpan"]] = relationship(
        back_populates="verdict", cascade="all, delete-orphan", order_by="EvidenceSpan.start_char"
    )


class RuleFiringRow(Base):
    """One named rule that fired. This is what makes a verdict defensible."""

    __tablename__ = "rule_firings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    verdict_id: Mapped[int] = mapped_column(
        ForeignKey("verdicts.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    rule_id: Mapped[str] = mapped_column(String(32), index=True)
    description: Mapped[str] = mapped_column(Text)
    conclusion: Mapped[str] = mapped_column(Text)
    citation_key: Mapped[str] = mapped_column(String(48))

    verdict: Mapped[Verdict] = relationship(back_populates="rule_firings")
    spans: Mapped[list["EvidenceSpan"]] = relationship(
        back_populates="rule_firing", cascade="all, delete-orphan"
    )


class EvidenceSpan(Base):
    """Exact character offsets into the report text, for UI highlighting."""

    __tablename__ = "evidence_spans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    verdict_id: Mapped[int] = mapped_column(
        ForeignKey("verdicts.id", ondelete="CASCADE"), index=True
    )
    rule_firing_id: Mapped[int | None] = mapped_column(
        ForeignKey("rule_firings.id", ondelete="CASCADE"), nullable=True, index=True
    )
    start_char: Mapped[int] = mapped_column(Integer)
    end_char: Mapped[int] = mapped_column(Integer)
    quoted_text: Mapped[str] = mapped_column(Text)

    verdict: Mapped[Verdict] = relationship(back_populates="evidence_spans")
    rule_firing: Mapped[RuleFiringRow | None] = relationship(back_populates="spans")


class Review(Base):
    """An HSE officer's judgement, stored ALONGSIDE the verdict, never over it.

    A report may accumulate several reviews. The latest one is what a dashboard
    shows; the verdict is what an auditor compares it against, and the gap
    between them is the training signal for the next model.
    """

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), index=True
    )
    verdict_id: Mapped[int] = mapped_column(
        ForeignKey("verdicts.id", ondelete="CASCADE"), index=True
    )
    reviewer_role: Mapped[str] = mapped_column(String(120))
    decision: Mapped[str] = mapped_column(String(16), index=True)  # confirm | override

    corrected_classification: Mapped[str | None] = mapped_column(String(32), index=True)
    corrected_energy_source: Mapped[str | None] = mapped_column(String(32))
    corrected_control_status: Mapped[str | None] = mapped_column(String(32))
    corrected_primary_lsr: Mapped[str | None] = mapped_column(String(48))

    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    report: Mapped[Report] = relationship(back_populates="reviews")


Index("ix_verdict_site_energy", Verdict.energy_source, Verdict.classification)
Index("ix_report_site_date", Report.site, Report.report_date)
