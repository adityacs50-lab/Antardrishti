"""Ingest and persistence service: run the engine, store everything traceably."""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from prahari.db.models import EvidenceSpan, Report, RuleFiringRow, Verdict
from prahari.domain.controls import CONTROLS_BY_KEY
from prahari.domain.classification import SifClassification
from prahari.domain.controls import ControlStatus
from prahari.ml.extractor import EXTRACTOR_VERSION
from prahari.rules.engine import SifVerdict, analyse

#: Deterministic triage ordering over classes the rule engine produced.
#: Declared here, not learned. Higher means "look at this first".
TRIAGE_CLASS_RANK: dict[SifClassification, int] = {
    SifClassification.HSIF: 100,
    SifClassification.PSIF: 80,
    SifClassification.EXPOSURE: 60,
    SifClassification.LSIF: 40,
    SifClassification.LOW_SEVERITY: 20,
    SifClassification.CAPACITY: 15,
    SifClassification.SUCCESS: 10,
    SifClassification.INSUFFICIENT_INFORMATION: 5,
}

#: How much the control state adds. A deliberately defeated barrier outranks a
#: merely missing one, because someone chose to defeat it.
TRIAGE_STATUS_BONUS: dict[ControlStatus, int] = {
    ControlStatus.BYPASSED: 9,
    ControlStatus.FAILED: 7,
    ControlStatus.NOT_FOLLOWED: 5,
    ControlStatus.ABSENT: 4,
    ControlStatus.PRESENT_UNVERIFIED: 2,
    ControlStatus.PRESENT_VERIFIED: 0,
    ControlStatus.UNKNOWN: 1,
}


def triage_rank(verdict: SifVerdict) -> int:
    return TRIAGE_CLASS_RANK[verdict.classification] + TRIAGE_STATUS_BONUS[verdict.control_status]


def verdict_reason(
    classification: str,
    control_key: str | None,
    control_status: str,
    injury: str,
    energy: str | None,
) -> str:
    """One line an HSE officer can act on, derived deterministically.

    Not a summary of the text - a restatement of what the rules concluded, so
    the queue row and the detail page can never disagree.
    """
    control = CONTROLS_BY_KEY.get(control_key or "")
    named = control.label[0].lower() + control.label[1:] if control else None
    verb = {
        "present_verified": "was verified",
        "present_unverified": "was present but unverified",
        "absent": "was absent",
        "failed": "failed",
        "bypassed": "was bypassed",
        "not_followed": "was not followed",
        "unknown": "could not be established",
    }.get(control_status, f"was {control_status.replace('_', ' ')}")
    barrier = f"{named} {verb}" if named else f"no direct control was named, and it {verb}"
    energy_label = (energy or "unidentified").replace("_", " ")

    if classification == SifClassification.HSIF.value:
        return f"Serious outcome from a high-energy {energy_label} release; {barrier}."
    if classification == SifClassification.PSIF.value:
        return (
            f"High-energy {energy_label} was released and {barrier}. "
            f"Outcome this time: {injury.replace('_', ' ')}."
        )
    if classification == SifClassification.EXPOSURE.value:
        return f"A high-energy {energy_label} hazard was present and {barrier}. Nothing was released."
    if classification == SifClassification.CAPACITY.value:
        return f"High-energy {energy_label} was released but {barrier} — the control held."
    if classification == SifClassification.SUCCESS.value:
        return f"A high-energy {energy_label} hazard was present and {barrier}."
    if classification == SifClassification.LSIF.value:
        return "Serious outcome from a low-energy source. Not the failure mode that kills crews."
    if classification == SifClassification.LOW_SEVERITY.value:
        return f"Low energy, no fatal potential. Outcome: {injury.replace('_', ' ')}."
    return "The report does not establish an energy source and a control state."


def persist(
    db: Session,
    *,
    text: str,
    site: str,
    report_date: date,
    reporter_role: str | None = None,
    activity: str | None = None,
    report_uid: str | None = None,
    source: str = "api",
    commit: bool = True,
) -> Report:
    """Run extraction + engine, then store the report, verdict and evidence."""
    facts, verdict = analyse(text)

    report = Report(
        report_uid=report_uid or f"R-{uuid.uuid4().hex[:12]}",
        text=text,
        site=site,
        report_date=report_date,
        reporter_role=reporter_role,
        activity=activity,
        source=source,
    )
    db.add(report)
    db.flush()

    row = Verdict(
        report_id=report.id,
        classification=verdict.classification.value,
        energy_source=verdict.energy_source.value if verdict.energy_source else None,
        high_energy=verdict.high_energy,
        high_energy_incident=verdict.high_energy_incident,
        control_status=verdict.control_status.value,
        direct_control_key=verdict.direct_control_key,
        direct_control_effective=verdict.direct_control_effective,
        injury_outcome=verdict.injury_outcome.value,
        primary_lsr=verdict.primary_lsr.value if verdict.primary_lsr else None,
        secondary_lsr=[r.value for r in verdict.secondary_lsr],
        evidence_completeness=verdict.evidence_completeness,
        triage_rank=triage_rank(verdict),
        engine_version=verdict.engine_version,
        extractor_version=EXTRACTOR_VERSION,
    )
    db.add(row)
    db.flush()

    for ordinal, firing in enumerate(verdict.fired_rules):
        firing_row = RuleFiringRow(
            verdict_id=row.id,
            ordinal=ordinal,
            rule_id=firing.rule_id,
            description=firing.description,
            conclusion=firing.conclusion,
            citation_key=firing.citation_key,
        )
        db.add(firing_row)
        db.flush()
        for span in firing.spans:
            db.add(
                EvidenceSpan(
                    verdict_id=row.id,
                    rule_firing_id=firing_row.id,
                    start_char=span.start,
                    end_char=span.end,
                    quoted_text=facts.text[span.start : span.end],
                )
            )

    if commit:
        db.commit()
    return report


def extract_pdf_text(raw: bytes) -> str:
    """Pull the text layer out of a PDF for the report-entry form.

    No OCR: a scanned page with no embedded text layer yields nothing, and
    the caller (the /api/extract-text route) turns that into a clear error
    rather than silently returning an empty report. pypdf is imported lazily
    so an environment that never uses this endpoint (tests, the CLI, a bare
    `make api`) never needs it installed to import this module at all - the
    same fail-closed pattern as prahari.ml.neural_extractor's optional
    onnxruntime/tokenizers imports.
    """
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw))
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 — one malformed page must not fail the whole upload
            continue
    return "\n\n".join(p for p in pages if p.strip())


#: Column/field names a real-world export is likely to use for each field the
#: ingest path needs. A public incident corpus (OSHA's severe-injury file, an
#: OIL/ONGC register, a plant's own spreadsheet) never happens to name its
#: narrative column "text" — before this, every such row was skipped as
#: "missing text" and the import reported nothing ingested for a file that was
#: perfectly good. Matching is done on a normalised key (lowercased, with
#: spaces/underscores/hyphens removed), so "Final Narrative", "final_narrative"
#: and "FINAL NARRATIVE" are all the same column.
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "text": (
        "text", "finalnarrative", "narrative", "description", "incidentdescription",
        "eventdescription", "report", "reporttext", "reportdescription", "details",
        "detail", "summary", "observation", "observations", "remarks", "body",
        "whathappened", "briefdescription", "abstract",
    ),
    "site": (
        "site", "location", "installation", "facility", "plant", "field", "area",
        "city", "employer", "workplace", "department", "unit",
    ),
    "date": (
        "date", "reportdate", "eventdate", "incidentdate", "occurrencedate",
        "dateofincident", "occurredon", "datetime", "timestamp",
    ),
    "activity": ("activity", "task", "job", "operation", "worktype", "jobtype", "process"),
    "reporter_role": ("reporterrole", "role", "reportedby", "reporter", "designation"),
    "report_uid": ("reportuid", "reportid", "id", "uid", "refno", "referenceno", "inspection"),
}

#: Date formats seen in real exports, tried in order. ISO first because that is
#: what this project's own tooling writes; the US-style m/d/Y next because that
#: is what the OSHA corpus uses; the day-first forms after that for Indian
#: spreadsheets, which is also why %d/%m/%Y is NOT in this list — it is
#: indistinguishable from %m/%d/%Y and guessing wrong silently corrupts every
#: date in the file. A slashed date is read as month-first; a dashed or dotted
#: one as day-first, which is how each is conventionally written.
_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m/%d/%y",
    "%d-%m-%Y", "%d-%m-%y", "%d.%m.%Y", "%d.%m.%y", "%d %b %Y", "%d %B %Y",
)


def _norm_key(key: str) -> str:
    return "".join(ch for ch in str(key).lower() if ch.isalnum())


def normalise_record(rec: dict) -> dict:
    """Map an arbitrary export's columns onto the fields ingest understands.

    Exact/canonical names always win: a file that already has a `text` column
    keeps it, and nothing here can override an explicit field. Only unmatched
    canonical fields are filled in from an alias, and the first alias listed
    wins, so `text` beats `narrative` beats `description` deterministically.
    Unrecognised columns are preserved untouched — a caller may still want them.
    """
    if not isinstance(rec, dict):
        return {}
    out = dict(rec)
    by_norm: dict[str, object] = {}
    for key, value in rec.items():
        nk = _norm_key(key)
        if nk and nk not in by_norm:
            by_norm[nk] = value

    for canonical, aliases in FIELD_ALIASES.items():
        existing = out.get(canonical)
        if isinstance(existing, str) and existing.strip():
            continue
        if existing not in (None, ""):
            continue
        for alias in aliases:
            value = by_norm.get(alias)
            if isinstance(value, str) and value.strip():
                out[canonical] = value.strip()
                break
            if value not in (None, ""):
                out[canonical] = value
                break
    return out


def coerce_date(raw: object) -> date | None:
    """Read a date written in any of the formats real exports actually use.

    Returns None when nothing parses, so the caller can fall back rather than
    lose an otherwise-valid report. A row whose narrative is good should never
    be discarded because its date column is formatted for a different country.
    """
    if raw in (None, ""):
        return None
    if isinstance(raw, date):
        return raw
    s = str(raw).strip()
    if not s:
        return None
    s = s.split("T")[0].split(" ")[0] if s[:4].isdigit() else s
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def parse_upload(filename: str, raw: bytes) -> list[dict]:
    """Parse a JSONL or CSV upload into ingest dicts. Never touches the network.

    Column names are normalised through FIELD_ALIASES on the way out, so an
    export that calls its narrative "Final Narrative" and its date "EventDate"
    lands on `text`/`date` like anything else.
    """
    text = raw.decode("utf-8-sig", errors="replace")
    name = (filename or "").lower()
    records: list[dict] = []

    if name.endswith(".csv"):
        for row in csv.DictReader(io.StringIO(text)):
            cleaned = {
                k: (v.strip() if isinstance(v, str) else v)
                for k, v in row.items()
                if k is not None
            }
            records.append(normalise_record(cleaned))
        return records

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(normalise_record(json.loads(line)))
    return records
