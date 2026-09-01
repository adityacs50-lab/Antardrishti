"""Offline fact extraction from safety report text.

WHAT THIS LAYER MAY AND MAY NOT DO
----------------------------------
It extracts STRUCTURED FACTS with exact character offsets. It never decides
whether something is a SIF precursor, never emits a severity, never emits a
risk score. Read CLAUDE.md before changing anything here.

Every fact carries the span that produced it, so the rule engine's verdict can
be traced back to the exact characters a human can highlight in the UI.

WHY THIS IS RULE-BASED TODAY
----------------------------
This is the v0 extractor: deterministic, dictionary-and-pattern based over the
domain lexicons, with negation and proximity handling. It needs no model, no
download and no network, so `docker compose up` works on a disconnected
machine today.

It is designed to be REPLACED by a fine-tuned token-classification model
exported to ONNX. The replacement changes only this file's internals: the
`ExtractedFacts` contract and the span discipline stay identical, and because
the rule engine consumes facts rather than text, swapping the extractor cannot
change how a verdict is justified. That is the whole benefit of the
neuro-symbolic split.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum

from prahari.domain.classification import InjuryOutcome
from prahari.domain.controls import ALL_CONTROLS, ControlStatus
from prahari.domain.energy import ENERGY_SOURCES, EnergySource
from prahari.domain.high_energy import HIGH_ENERGY_CUES
from prahari.domain.lsr import LIFE_SAVING_RULES, LifeSavingRule

EXTRACTOR_VERSION = "rule-v0.1"


class FactType(str, Enum):
    ENERGY_PHRASE = "energy_phrase"
    HIGH_ENERGY_CUE = "high_energy_cue"
    CONTROL_MENTION = "control_mention"
    CONTROL_STATUS = "control_status"
    INJURY = "injury"
    INCIDENT_MARKER = "incident_marker"
    CONDITION_MARKER = "condition_marker"
    LSR_PHRASE = "lsr_phrase"
    MEASUREMENT = "measurement"


@dataclass(frozen=True, slots=True)
class Span:
    """A half-open character range into the ORIGINAL report text."""

    start: int
    end: int

    def text_of(self, source: str) -> str:
        return source[self.start : self.end]


@dataclass(frozen=True, slots=True)
class Fact:
    """One extracted fact, anchored to the text that produced it."""

    fact_type: FactType
    value: str
    span: Span
    matched_text: str
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class Sentence:
    """A sentence with its offsets into the original text."""

    index: int
    span: Span


@dataclass(frozen=True, slots=True)
class ExtractedFacts:
    """Everything the extractor found. No conclusions, only observations."""

    text: str
    facts: tuple[Fact, ...]
    sentences: tuple[Sentence, ...] = ()
    extractor_version: str = EXTRACTOR_VERSION

    def of_type(self, fact_type: FactType) -> tuple[Fact, ...]:
        return tuple(f for f in self.facts if f.fact_type is fact_type)

    def values_of(self, fact_type: FactType) -> tuple[str, ...]:
        return tuple(f.value for f in self.of_type(fact_type))

    def sentence_index_of(self, span: Span) -> int:
        """Which sentence a span falls in; -1 if it falls outside all of them."""
        for sent in self.sentences:
            if sent.span.start <= span.start < sent.span.end:
                return sent.index
        return -1


# --------------------------------------------------------------------------
# Status cue lexicon
# --------------------------------------------------------------------------
# Ordered most-specific first: BYPASSED before ABSENT, because "guard had been
# removed" is a deliberate defeat, not a plain absence.

_STATUS_PATTERNS: tuple[tuple[ControlStatus, tuple[str, ...]], ...] = (
    (
        ControlStatus.BYPASSED,
        (
            r"\bby[- ]?pass(?:ed|ing)?\b", r"\boverr?idd?en\b", r"\boverride[d]?\b",
            r"\bdefeat(?:ed)?\b", r"\bdisabl(?:ed|ing)\b", r"\binhibit(?:ed)?\b",
            r"\bgagg?ed\b", r"\bjumper(?:ed)?\b", r"\bhad been removed\b",
            r"\bdeliberately\b", r"\bdispensed with\b", r"\bkept open\b",
            r"\bpainted over\b", r"\bbridged\b", r"\bcar seal(?:ed)? open\b",
            r"\bdisconnected by\b", r"\bswitched off as\b",
        ),
    ),
    (
        ControlStatus.FAILED,
        (
            r"\bgave way\b", r"\bfailed\b", r"\bparted\b", r"\bsnapp?ed\b",
            r"\bdid not hold\b", r"\bdefective\b", r"\bmalfunction",
            r"\bpassing\b", r"\bslipp?ed from\b", r"\bpulled out\b",
            r"\bwas found broken\b", r"\bnot latch\b", r"\bbattery was dead\b",
            r"\bcame off\b", r"\bopened under load\b", r"\bworn out\b",
            r"\bhad come off\b", r"\bjamm?ed\b", r"\bstopped during\b", r"\btorn\b",
        ),
    ),
    (
        ControlStatus.NOT_FOLLOWED,
        (
            r"\bbut (?:was |were )?not (?:used|worn|followed|placed|secured)\b",
            r"\bnot (?:used|worn|followed|placed|secured) by\b",
            r"\bwas available\b[^.]{0,60}\bnot\b", r"\bwere provided\b[^.]{0,60}\bnot\b",
            r"\bwas provided\b[^.]{0,60}\bnot\b", r"\bwere issued\b[^.]{0,60}\bnot\b",
            r"\bdid not tie off\b", r"\bdid not use\b", r"\bentered\b[^.]{0,40}\bdespite\b",
            r"\bdespite barricading\b", r"\bremained inside\b", r"\bwas not wearing the\b",
            r"\bnahi pehna\b", r"\bnot worn\b", r"\bkept on the forehead\b",
            r"\bhe took the short cut\b", r"\blifted (?:it |the item )?by hand\b",
            r"\b(?:provided|available|in place|fitted|issued|marked|installed|posted|worn|there)\s+(?:but|however)\b",
            r"\bbut (?:workman|worker|he|she|the crew|two|the operator|the electrician|the floorman|the injured)\b",
            r"\bleaning outside\b", r"\bkept his hand inside\b", r"\bentered the area without\b",
            r"\bwithout wearing it\b", r"\bhe left the manhole\b", r"\bnot maintained by\b",
        ),
    ),
    (
        ControlStatus.PRESENT_UNVERIFIED,
        (
            r"\bnot (?:been )?(?:checked|verified|inspected|tested|recorded|assessed)\b",
            r"\bno (?:inspection|test|verification|record|calibration)\b",
            r"\bnot (?:displayed|available at site)\b", r"\bcertificate was not\b",
            r"\bnobody (?:had )?verified\b", r"\bwas claimed\b", r"\bwas said to (?:be|have)\b",
            r"\bassumed to be\b", r"\bcalibration (?:was )?overdue\b",
            r"\bnot certified\b", r"\bnot been done for a long time\b",
            r"\bhowever\b[^.]{0,60}\bnot\b", r"\bnot bump tested\b",
            r"\bnot (?:proved|prove) dead\b", r"\bnever been tested\b",
            r"\bappeared adequate\b", r"\bwas not visible\b",
        ),
    ),
    (
        ControlStatus.ABSENT,
        (
            r"\bno (?:fall arrest|guardrail|handrail|edge protection|barricading|isolation|permit|gas test|ventilation|shoring|whip check|restraint|cover|monitor|survey meter|separation|secondary retention|lift plan|eye protection|mechanical aid|padding|specific control|engineering noise control|arrangement|evacuation arrangement|anti-venom)\b",
            r"\bwas not (?:wearing|provided|done|carried out|worn|fitted|taken|available)\b",
            r"\bwere not (?:worn|provided|done|fitted|available)\b",
            r"\bwithout any\b", r"\bw/?o any\b", r"\bwas missing\b", r"\bwere missing\b",
            r"\bnot isolated\b", r"\bnahi liya\b", r"\bnahi hua\b", r"\bnahi kiya\b",
            r"\bnasil\b", r"\bnoasil\b", r"\bnahi tha\b", r"\bnot provided\b",
            r"\bneither drained nor\b", r"\bleft open without\b", r"\bnot available\b",
        ),
    ),
    (
        ControlStatus.PRESENT_VERIFIED,
        (
            r"\bwas (?:inspected|verified|checked|tested|confirmed)\b",
            r"\bwere (?:inspected|verified|checked|tested|confirmed)\b",
            r"\bproved dead\b", r"\bproperly verified\b", r"\bzero (?:energy|pressure|voltage) (?:was )?(?:verified|confirmed)\b",
            r"\bconfirmed by survey meter\b", r"\bcolour coded\b", r"\bthird party tested\b",
            r"\bvalid test certificate\b", r"\bgreen tag\b", r"\bcontinuous(?:ly)? monitor",
            r"\bwas current\b", r"\bbump tested\b", r"\binspected before use\b",
            r"\bcertified\b", r"\b100% tie off\b", r"\bchecked by TP\b",
            r"\bin place and verified\b", r"\bfunction test\b",
            r"\b(?:was|were) fitted\b", r"\b(?:was|were) (?:in place|installed|posted|applied|secured|maintained|displayed|running|established)\b",
            r"\bin place on all sides\b", r"\bwas erected by trained\b", r"\bkept in place\b",
            r"\bproperly (?:benched|restrained|secured|anchored|rigged)\b",
            r"\b(?:was|were) provided (?:and|on|at|for)\b", r"\bwas worn and\b", r"\bwere worn and\b",
            r"\bwas used with\b", r"\bintact\b", r"\bvalid fitness\b", r"\bwas approved\b",
            r"\bwell was killed\b", r"\btwo tested barriers\b", r"\brated and certified\b",
            r"\bisolated and (?:blinded|purged|drained)\b", r"\blocked and tagged\b",
        ),
    ),
)

_INJURY_PATTERNS: tuple[tuple[InjuryOutcome, tuple[str, ...]], ...] = (
    (
        InjuryOutcome.FATALITY,
        (r"\bfatal\b", r"\bsuccumbed\b", r"\bbrought dead\b", r"\bdeath\b", r"\bdied\b", r"\bfatality\b"),
    ),
    (
        InjuryOutcome.SERIOUS_INJURY,
        (
            r"\bserious injury\b", r"\bfracture", r"\bamputat", r"\badmitted in hospital\b",
            r"\bLTI\b", r"\blost time injury\b", r"\breportable injury\b", r"\breferred to\b",
            r"\bunder treatment\b", r"\bevacuated\b", r"\bunconscious\b", r"\bcritical\b",
            r"\bmajor injury\b", r"\bdisabl(?:ing|ement)\b",
        ),
    ),
    (
        InjuryOutcome.MINOR_INJURY,
        (
            r"\bminor injury\b", r"\bdressing done\b", r"\bstitch", r"\bsprain",
            r"\breturned to duty\b", r"\bone day rest\b", r"\bbruise", r"\btwisted (?:his |her )?ankle\b",
            r"\bcut (?:injury|on)\b", r"\bdeclared fit\b", r"\bswelling\b",
        ),
    ),
    (
        InjuryOutcome.FIRST_AID,
        (r"\bfirst aid\b", r"\bfirst-aid\b", r"\btreated at site\b", r"\birritation\b", r"\bwatering in the eye\b"),
    ),
    (
        InjuryOutcome.NONE,
        (
            r"\bno injury\b", r"\bnobody was injured\b", r"\bno one was injured\b",
            r"\bnil injury\b", r"\bkoi chot nahi\b", r"\bkisi ko chot nahi\b",
            r"\beku aghat poa nai\b", r"\bkunu manuh aghat poa nai\b",
            r"\bno injury to (?:any )?person", r"\bnobody got hurt\b",
            r"\bकोई चोट नहीं\b", r"\bकोনো আঘাত হোৱা নাই\b", r"\bকোনো আঘাত হোৱা নাই\b",
            r"\bno injury and no property damage\b",
        ),
    ),
)

#: Text that indicates energy actually got loose (an event), versus text that
#: indicates a standing condition someone observed.
_INCIDENT_MARKERS: tuple[str, ...] = (
    r"\bfell\b", r"\bfell from\b", r"\bdropped\b", r"\bslipp?ed\b", r"\bcollided\b",
    r"\bcollapsed\b", r"\bcaved in\b", r"\bstruck\b", r"\bhit\b", r"\bparted\b",
    r"\bblew out\b", r"\breleased\b", r"\bignited\b", r"\bflash(?:over| fire)\b",
    r"\barc occurr?ed\b", r"\bcaught fire\b", r"\btoppled\b", r"\boverturned\b",
    r"\bwas bitten\b", r"\bbitten\b", r"\breceived a shock\b", r"\bswung\b",
    r"\bwhipped\b", r"\bcame off\b", r"\bcame within\b", r"\bnear miss\b",
    r"\bwent off the embankment\b", r"\bnarrow escape\b", r"\bbal bal bacha\b",
    r"\bdetached\b", r"\bsprayed out\b", r"\bwent into\b", r"\bbumped\b",
    r"\bentered his eye\b", r"\bpricked\b", r"\btripp?ed over\b", r"\blost balance\b",
    r"\bgave way\b", r"\bcame loose\b", r"\bstayed in the guide tube\b", r"\bdid not retract\b",
    r"\btilted\b", r"\bwent over the open edge\b", r"\bslid down\b", r"\bburied him\b",
    r"\bblew off\b", r"\bflew off\b", r"\bwhipped across\b", r"\bran down\b",
    r"\bstruck the\b", r"\bpassed just over\b", r"\bbrushed against\b", r"\btouched the line\b",
    r"\bwent into (?:high|alarm)\b", r"\balarmed at high\b", r"\bhad to be (?:rescued|pulled out)\b",
    r"\bsprayed\b", r"\bcame out with force\b", r"\bbuilt up again\b", r"\bopened and the load\b",
    r"\bstarted\b(?= *[a-z]* *(?:fire|on auto))", r"\bskidded\b", r"\bcaught his sleeve\b",
    r"\bbecame unconscious\b", r"\bfelt giddy\b", r"\bstarted on auto\b",
    r"\bmoved while\b", r"\bcaught his\b", r"\brotated while\b", r"\bwas found collapsed\b",
    r"\bdid not retract\b", r"\blifted and there was\b", r"\bstrained\b", r"\bfelt pain\b",
    r"\bknocked\b", r"\bwas thrown back\b", r"\bfound inside the valve pit\b",
)

_CONDITION_MARKERS: tuple[str, ...] = (
    r"\bwas observed\b", r"\bwere observed\b", r"\bit was observed\b", r"\bwas noticed\b",
    r"\bwas noted\b", r"\bduring (?:the )?(?:routine )?(?:site )?round\b",
    r"\bduring inspection\b", r"\bduring the inspection\b", r"\bunsafe condition\b",
    r"\bnoticed by\b", r"\bobserved by\b", r"\bduring (?:the )?(?:permit )?audit\b",
    r"\bwas checked during\b", r"\bprior to\b", r"\bbefore the lift\b",
    r"\bpre-?job walkdown\b", r"\bpre-lift check\b", r"\bwas seen\b",
)

_MEASUREMENT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("height_m", r"(\d+(?:\.\d+)?)\s*(?:mtr|meter|metre|m)\b\s*(?:height|high|above)?"),
    ("depth_m", r"(?:depth|deep)\s*(?:of\s*)?(?:abt\s*|approx\s*)?(\d+(?:\.\d+)?)\s*(?:mtr|meter|metre|m)\b"),
    ("voltage_v", r"(\d+(?:\.\d+)?)\s*(?:v|volt|volts)\b"),
    ("voltage_kv", r"(\d+(?:\.\d+)?)\s*(?:kv|k\.?v\.?)\b"),
    ("mass_kg", r"(\d+(?:\.\d+)?)\s*(?:kg|kgs|kilogram)\b"),
    ("speed_kmph", r"(\d+(?:\.\d+)?)\s*(?:kmph|km/h|kmh)\b"),
    ("temp_c", r"(\d+(?:\.\d+)?)\s*(?:deg\s*c|°c|degree c)\b"),
    ("noise_db", r"(\d+(?:\.\d+)?)\s*(?:db|dB\(A\)|decibel)\b"),
)


def segment_sentences(text: str) -> tuple[Sentence, ...]:
    """Split into sentences, preserving exact offsets.

    Field reports punctuate badly - missing spaces after full stops, line
    breaks instead of periods - so this is intentionally permissive.
    """
    out: list[Sentence] = []
    start = 0
    idx = 0
    for m in re.finditer(r"[.!?\n]+", text):
        end = m.end()
        if end - start >= 3:
            out.append(Sentence(index=idx, span=Span(start, end)))
            idx += 1
        start = end
    if start < len(text) and len(text) - start >= 3:
        out.append(Sentence(index=idx, span=Span(start, len(text))))
    return tuple(out)


def _norm(text: str) -> str:
    """Casefold and NFKC-normalise for matching, preserving length.

    Length preservation is essential: offsets computed on the normalised string
    must index the ORIGINAL string. NFKC can change length for some characters,
    so any character whose normalisation is not length-1 is left as-is.
    """
    out: list[str] = []
    for ch in text:
        folded = unicodedata.normalize("NFKC", ch).lower()
        out.append(folded if len(folded) == 1 else ch.lower())
    return "".join(out)


def _find_all(haystack: str, needle: str) -> list[tuple[int, int]]:
    """Whole-token-ish literal search. Returns spans in the original indexing."""
    spans: list[tuple[int, int]] = []
    start = 0
    n = len(needle)
    if not n:
        return spans
    while True:
        idx = haystack.find(needle, start)
        if idx == -1:
            return spans
        before_ok = idx == 0 or not haystack[idx - 1].isalnum()
        after = idx + n
        after_ok = after >= len(haystack) or not haystack[after].isalnum()
        if before_ok and after_ok:
            spans.append((idx, after))
        start = idx + 1


def _regex_spans(haystack: str, patterns: tuple[str, ...]) -> list[tuple[int, int, str]]:
    found: list[tuple[int, int, str]] = []
    for pat in patterns:
        for m in re.finditer(pat, haystack, flags=re.IGNORECASE):
            found.append((m.start(), m.end(), m.group(0)))
    return found


def extract(text: str) -> ExtractedFacts:
    """Extract structured facts with exact spans. Decides nothing."""
    lowered = _norm(text)
    facts: list[Fact] = []

    def add(ft: FactType, value: str, start: int, end: int, detail: str | None = None) -> None:
        facts.append(
            Fact(fact_type=ft, value=value, span=Span(start, end), matched_text=text[start:end], detail=detail)
        )

    # Energy trigger phrases
    for source, definition in ENERGY_SOURCES.items():
        for phrase in definition.trigger_phrases:
            for s, e in _find_all(lowered, phrase):
                add(FactType.ENERGY_PHRASE, source.value, s, e, detail=phrase)

    # High-energy cues
    for cue in HIGH_ENERGY_CUES:
        for phrase in cue.phrases:
            for s, e in _find_all(lowered, phrase):
                add(FactType.HIGH_ENERGY_CUE, cue.key, s, e, detail=cue.energy_source.value)

    # Control mentions
    for control in ALL_CONTROLS:
        for phrase in control.phrases:
            for s, e in _find_all(lowered, phrase):
                add(
                    FactType.CONTROL_MENTION,
                    control.key,
                    s,
                    e,
                    detail="direct" if control.is_direct else "indirect",
                )

    # Control status signals
    for status, patterns in _STATUS_PATTERNS:
        for s, e, matched in _regex_spans(lowered, patterns):
            add(FactType.CONTROL_STATUS, status.value, s, e, detail=matched)

    # Injury signals
    for outcome, patterns in _INJURY_PATTERNS:
        for s, e, matched in _regex_spans(lowered, patterns):
            add(FactType.INJURY, outcome.value, s, e, detail=matched)

    # Event vs condition
    for s, e, matched in _regex_spans(lowered, _INCIDENT_MARKERS):
        add(FactType.INCIDENT_MARKER, "incident", s, e, detail=matched)
    for s, e, matched in _regex_spans(lowered, _CONDITION_MARKERS):
        add(FactType.CONDITION_MARKER, "condition", s, e, detail=matched)

    # Life-Saving Rule phrases
    for rule, definition in LIFE_SAVING_RULES.items():
        for phrase in definition.trigger_phrases:
            for s, e in _find_all(lowered, phrase):
                add(FactType.LSR_PHRASE, rule.value, s, e, detail=phrase)

    # Measurements
    for name, pattern in _MEASUREMENT_PATTERNS:
        for m in re.finditer(pattern, lowered, flags=re.IGNORECASE):
            add(FactType.MEASUREMENT, name, m.start(), m.end(), detail=m.group(1))

    facts.sort(key=lambda f: (f.span.start, f.span.end, f.fact_type.value, f.value))
    return ExtractedFacts(text=text, facts=tuple(facts), sentences=segment_sentences(text))
