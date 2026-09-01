"""Pydantic v2 schemas for the prahari API.

A note on the word "confidence"
-------------------------------
This system has no confidence score in the machine-learning sense, and it never
will - see CLAUDE.md. What the API exposes is `evidence_completeness`: the
fraction of the four required fact slots (energy source, magnitude, control
state, outcome) for which the extractor found evidence in the text. It measures
how much of the report was legible, not how sure anything is that a verdict is
right. The list endpoint accepts `min_confidence` as a filter name because that
is what people type, and it filters on exactly this field.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from prahari.domain.classification import InjuryOutcome, SifClassification
from prahari.domain.controls import ControlStatus
from prahari.domain.energy import EnergySource
from prahari.domain.lsr import LifeSavingRule


class EvidenceSpanOut(BaseModel):
    """A character range in the report text, for UI highlighting.

    `start` and `end` index the ORIGINAL report text, so the frontend can
    slice `text[start:end]` directly and get `quoted_text` back.
    """

    model_config = ConfigDict(from_attributes=True)

    start: int = Field(..., ge=0)
    end: int = Field(..., ge=0)
    quoted_text: str
    rule_id: str | None = None


class RuleFiringOut(BaseModel):
    """One named rule that fired, with the spans that made it fire."""

    model_config = ConfigDict(from_attributes=True)

    rule_id: str
    description: str
    conclusion: str
    citation_key: str
    spans: list[EvidenceSpanOut] = Field(default_factory=list)


class SIFVerdictOut(BaseModel):
    """The engine's answer. Every field traceable through `fired_rules`."""

    model_config = ConfigDict(from_attributes=True)

    classification: SifClassification
    energy_source: EnergySource | None = None
    high_energy: bool
    high_energy_incident: bool
    control_status: ControlStatus
    direct_control_key: str | None = None
    direct_control_effective: bool
    injury_outcome: InjuryOutcome
    primary_lsr: LifeSavingRule | None = None
    secondary_lsr: list[LifeSavingRule] = Field(default_factory=list)
    evidence_completeness: float = Field(..., ge=0.0, le=1.0)
    triage_rank: int
    engine_version: str
    extractor_version: str
    fired_rules: list[RuleFiringOut] = Field(default_factory=list)


class ReportIn(BaseModel):
    """Ingest payload."""

    text: str = Field(..., min_length=1, max_length=20000)
    site: str = Field(..., min_length=1, max_length=120)
    date: date
    reporter_role: str | None = Field(default=None, max_length=120)
    activity: str | None = Field(default=None, max_length=160)
    report_uid: str | None = Field(default=None, max_length=64)

    @field_validator("text")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text must not be blank")
        return v


class ReviewIn(BaseModel):
    """An HSE officer confirming or overriding a verdict.

    The correction is stored as a new row. The verdict is never edited.
    """

    reviewer_role: str = Field(..., min_length=1, max_length=120)
    decision: Literal["confirm", "override"]
    reason: str = Field(..., min_length=3, max_length=2000)
    corrected_classification: SifClassification | None = None
    corrected_energy_source: EnergySource | None = None
    corrected_control_status: ControlStatus | None = None
    corrected_primary_lsr: LifeSavingRule | None = None

    @field_validator("corrected_classification")
    @classmethod
    def _override_needs_a_correction(cls, v, info):  # noqa: ANN001
        return v

    def has_correction(self) -> bool:
        return any(
            (
                self.corrected_classification,
                self.corrected_energy_source,
                self.corrected_control_status,
                self.corrected_primary_lsr,
            )
        )


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reviewer_role: str
    decision: str
    reason: str
    corrected_classification: SifClassification | None = None
    corrected_energy_source: EnergySource | None = None
    corrected_control_status: ControlStatus | None = None
    corrected_primary_lsr: LifeSavingRule | None = None
    created_at: datetime


class ReportSummary(BaseModel):
    """List-view row."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    report_uid: str
    site: str
    date: date
    reporter_role: str | None = None
    activity: str | None = None
    excerpt: str
    classification: SifClassification
    energy_source: EnergySource | None = None
    primary_lsr: LifeSavingRule | None = None
    control_status: ControlStatus
    evidence_completeness: float
    triage_rank: int
    reviewed: bool = False
    #: One deterministic line restating what the rules concluded, so a queue
    #: row and the detail page can never disagree.
    reason: str = ""


class ReportDetail(BaseModel):
    """Detail view: full text plus every span needed to highlight it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    report_uid: str
    text: str
    site: str
    date: date
    reporter_role: str | None = None
    activity: str | None = None
    source: str
    ingested_at: datetime
    verdict: SIFVerdictOut
    evidence_spans: list[EvidenceSpanOut] = Field(default_factory=list)
    reviews: list[ReviewOut] = Field(default_factory=list)
    #: The latest review's correction, if any. Never merged into `verdict`.
    effective_classification: SifClassification


class AnalyzeIn(BaseModel):
    """Ad-hoc analysis payload for the Live Analysis panel."""

    text: str = Field(..., min_length=1, max_length=20000)

    @field_validator("text")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text must not be blank")
        return v


class AnalyzeOut(BaseModel):
    """Result of analysing text WITHOUT persisting it.

    This exists so the UI never needs its own copy of the rule engine. There is
    exactly one engine in this system; a second implementation in another
    language would drift and would quietly break the auditability claim the
    whole project rests on.
    """

    text: str
    verdict: SIFVerdictOut
    evidence_spans: list[EvidenceSpanOut] = Field(default_factory=list)
    reason: str


class MetaOut(BaseModel):
    """Vocabulary for populating filter controls."""

    sites: list[str]
    activities: list[str]
    classifications: list[str]
    energy_sources: list[str]
    control_statuses: list[str]
    life_saving_rules: list[dict]
    engine_version: str
    extractor_version: str
    report_count: int


class Page(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ReportSummary]


class IngestResult(BaseModel):
    id: int
    report_uid: str
    verdict: SIFVerdictOut


class BulkResult(BaseModel):
    received: int
    ingested: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
    classification_counts: dict[str, int] = Field(default_factory=dict)


# -- Analytics -------------------------------------------------------------


class DensityCell(BaseModel):
    site: str
    activity: str
    total_reports: int
    precursor_count: int
    precursor_rate: float = Field(..., ge=0.0, le=1.0)


class DensityOut(BaseModel):
    window_days: int | None
    sites: list[str]
    activities: list[str]
    cells: list[DensityCell]


class LsrBucket(BaseModel):
    lsr: LifeSavingRule
    short_name: str
    count: int
    precursor_count: int
    share: float


class LsrOut(BaseModel):
    total: int
    unassigned: int
    buckets: list[LsrBucket]


class BarrierPattern(BaseModel):
    control_key: str
    control_label: str
    control_class: str
    energy_source: EnergySource | None = None
    site: str | None = None
    failure_count: int
    statuses: dict[str, int]
    first_seen: date | None = None
    last_seen: date | None = None
    trend: Literal["rising", "falling", "flat", "insufficient_history"]
    recent_count: int
    previous_count: int


class BarriersOut(BaseModel):
    window_days: int
    patterns: list[BarrierPattern]


class AccumulationContributor(BaseModel):
    report_id: int
    report_uid: str
    date: date
    classification: SifClassification
    control_status: ControlStatus
    age_days: int
    decayed_weight: float


class AccumulationSignature(BaseModel):
    """One repeated barrier failure at one place."""

    control_key: str
    control_label: str
    control_status: ControlStatus
    occurrences: int
    decayed_occurrences: float
    contribution: float
    contributors: list[AccumulationContributor]


class AccumulationCell(BaseModel):
    site: str
    energy_source: EnergySource
    index: float
    band: Literal["watch", "elevated", "high", "critical"]
    total_precursors: int
    max_repeat: int
    trend: Literal["rising", "falling", "flat", "insufficient_history"]
    previous_index: float
    signatures: list[AccumulationSignature]
    explanation: str


class AccumulationOut(BaseModel):
    window_days: int
    half_life_days: float
    repeat_exponent: float
    diversity_discount: float
    bands: dict[str, float]
    as_of: date
    cells: list[AccumulationCell]
