"""Synthetic OIL safety report generator with zero-manual-annotation ground truth.

How the labels stay honest
--------------------------
Reports are COMPOSED, never read back. The generator first picks a target SCL
class, then constructs a scenario spec that yields exactly that class through
the published SCL decision table, and only then renders text from the spec. The
ground truth is a property of the spec, not an interpretation of the string. At
no point does anything in this module look at generated text and decide what it
means - that would make the labels exactly as unreliable as the model we are
trying to evaluate.

Every record is self-checked: `derive_classification(spec)` is re-run against
the spec after construction and must equal the requested class, or generation
raises.

The four hard case families the evaluation set exists for
---------------------------------------------------------
1. HIGH POTENTIAL, NO OUTCOME (`psif`, `exposure`). Nobody was scratched and the
   report is boring. Fatal potential was real. A severity model scores these
   near zero. These are the reason the project exists.
2. VISIBLE INJURY, LOW POTENTIAL (`low_severity` with a real injury). Blood, a
   first-aid entry, maybe a lost day - and no fatal potential whatsoever. A
   severity model ranks these above the money cases. Exactly backwards.
3. UNDERDETERMINED (`insufficient_information`). Two vague lines. The correct
   answer is to say so. Labels that the text cannot support are left null here
   on purpose - scoring a model against an unstated fact teaches it to guess.
4. CONTROLLED HIGH ENERGY (`capacity`, `success`). High energy was present and
   the direct control held. Must not be flagged as a precursor, or the system
   cries wolf and the crew stops reading it.

Usage
-----
    python -m prahari.data.generator --n 3000 --seed 42
"""

from __future__ import annotations

import argparse
import json
import re
import random
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from prahari.data import lexicon as lx
from prahari.data.annotation import Annotated, EntityLabel
from prahari.data.scenarios import (
    HIGH_ENERGY_SCENARIOS,
    LOW_ENERGY_SCENARIOS,
    Scenario,
)
from prahari.domain.classification import (
    SCL_DECISION_TABLE,
    InjuryOutcome,
    ReportKind,
    SERIOUS_OUTCOMES,
    SifClassification,
)
from prahari.domain.controls import CONTROLS_BY_KEY, ControlStatus, PROTECTIVE_STATUSES
from prahari.domain.energy import ENERGY_SOURCES, EnergySource
from prahari.domain.lsr import LifeSavingRule
from prahari.ml.extractor import _STATUS_PATTERNS

# --------------------------------------------------------------------------
# Target distribution
# --------------------------------------------------------------------------

#: Deliberately precursor-heavy. The point of the dataset is the classes a
#: severity-ranking model gets wrong, so PSIF + EXPOSURE together are the
#: largest block, and LOW_SEVERITY is large enough that the injury-but-harmless
#: trap is well represented.
CLASS_DISTRIBUTION: dict[SifClassification, float] = {
    SifClassification.PSIF: 0.22,
    SifClassification.EXPOSURE: 0.15,
    SifClassification.LOW_SEVERITY: 0.18,
    SifClassification.CAPACITY: 0.10,
    SifClassification.SUCCESS: 0.10,
    SifClassification.INSUFFICIENT_INFORMATION: 0.12,
    SifClassification.HSIF: 0.08,
    SifClassification.LSIF: 0.05,
}

NON_PROTECTIVE_GENERATED: tuple[ControlStatus, ...] = (
    ControlStatus.ABSENT,
    ControlStatus.PRESENT_UNVERIFIED,
    ControlStatus.NOT_FOLLOWED,
    ControlStatus.BYPASSED,
    ControlStatus.FAILED,
)

#: Which phrase-bank slots suit which scenario, so code-mixed fragments land
#: somewhere semantically sensible rather than at random.
SCENARIO_PHRASE_HINTS: dict[str, tuple[str, ...]] = {
    "wah_derrick": ("no_safety_belt", "was_working", "was_in_hurry"),
    "wah_scaffold": ("no_safety_belt", "condition_bad", "was_working"),
    "dropped_object": ("was_standing_under", "did_not_check"),
    "suspended_load": ("was_standing_under", "condition_bad", "did_not_check"),
    "vehicle_row": ("was_in_hurry", "did_not_check"),
    "mobile_equipment": ("did_not_check", "was_working"),
    "pumping_unit": ("no_permit", "did_not_check", "was_working"),
    "rotary_tongs": ("was_in_hurry", "was_working"),
    "overhead_line": ("no_permit", "did_not_check"),
    "switchgear_loto": ("no_permit", "did_not_check", "was_working"),
    "wellhead_pressure": ("no_permit", "did_not_check", "was_working"),
    "hydrotest": ("no_permit", "condition_bad"),
    "excavation": ("no_permit", "condition_bad", "was_working"),
    "gas_cylinder": ("condition_bad", "did_not_check"),
    "hot_work": ("no_gas_test", "no_permit", "was_in_hurry"),
    "steam_hot_oil": ("did_not_check", "was_working"),
    "h2s_release": ("no_gas_test", "no_permit"),
    "confined_space": ("no_permit", "no_gas_test"),
    "radiography": ("no_permit", "did_not_check"),
    "snakebite_row": ("was_working", "condition_bad"),
    "compressor_noise": ("was_working", "condition_bad"),
}

VAGUE_TEMPLATES: tuple[str, ...] = (
    "Unsafe act observed at {location}. {designation} was careless during the job. Advised.",
    "{designation} was found working in unsafe manner at {installation}. Counselled on the spot.",
    "Unsafe condition noticed at {installation}, {location}. Same has been informed to concerned.",
    "During round at {location} some unsafe practice was seen. Workman was warned.",
    "Housekeeping and safety not proper at {installation}. Advised to maintain.",
    "One {designation} was not following safety norms at {location}. TBT given.",
    "Observation: unsafe act by {designation} at {installation}. Corrected immediately.",
    "Near miss reported from {installation}. No injury. Details awaited.",
    "Minor near miss at {location} during shift. Matter under enquiry.",
    "{designation} did not follow procedure at {installation}. Warning issued.",
    "Unsafe condition at {location}. Needs attention of maintenance.",
    "Safety violation observed at {installation}. Concerned counselled.",
)

VAGUE_TAILS: tuple[str, ...] = (
    "",
    " No further details available.",
    " Report to be followed up.",
    " Nil injury.",
    " Closed.",
)


# --------------------------------------------------------------------------
# Spec and ground truth
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    """The complete generative description of one report.

    Ground truth is derived from these fields alone.
    """

    scenario_key: str
    energy_source: EnergySource | None
    high_energy: bool
    high_energy_incident: bool
    control_status: ControlStatus
    direct_control_key: str
    injury: InjuryOutcome
    report_kind: ReportKind
    primary_lsr: LifeSavingRule | None
    secondary_lsr: tuple[LifeSavingRule, ...]
    is_vague: bool
    style: lx.WritingStyle
    language_mix: lx.LanguageMix

    @property
    def direct_control_effective(self) -> bool:
        """Only a verified control protects anyone. See domain/controls.py."""
        return self.control_status in PROTECTIVE_STATUSES

    @property
    def serious_injury(self) -> bool:
        return self.injury in SERIOUS_OUTCOMES


def derive_classification(spec: ScenarioSpec) -> SifClassification:
    """Ground truth, by lookup in the published SCL decision table.

    This is a table lookup over four booleans, not an interpretation of text.
    """
    if spec.is_vague:
        return SifClassification.INSUFFICIENT_INFORMATION
    return SCL_DECISION_TABLE[
        (
            spec.high_energy,
            spec.high_energy_incident,
            spec.direct_control_effective,
            spec.serious_injury,
        )
    ]


def _pick_style(rng: random.Random) -> lx.WritingStyle:
    return rng.choices(
        (
            lx.WritingStyle.SUPERVISOR_FORMAL,
            lx.WritingStyle.TERSE_TELEGRAPHIC,
            lx.WritingStyle.RAMBLING,
        ),
        weights=(0.45, 0.38, 0.17),
    )[0]


def _pick_language(rng: random.Random) -> lx.LanguageMix:
    return rng.choices(
        (
            lx.LanguageMix.ENGLISH,
            lx.LanguageMix.HINGLISH,
            lx.LanguageMix.HINDI_DEVANAGARI,
            lx.LanguageMix.ASSAMESE_ROMAN,
            lx.LanguageMix.ASSAMESE_SCRIPT,
            lx.LanguageMix.HEAVY_CODE_MIX,
        ),
        weights=(0.34, 0.24, 0.10, 0.13, 0.07, 0.12),
    )[0]


def _pick_scenario(pool: tuple[Scenario, ...], rng: random.Random) -> Scenario:
    """Pick a scenario, balanced across energy sources.

    Uniform choice over scenarios would under-sample radiation and sound (one
    scenario each) against mechanical and pressure (several). For an EVALUATION
    set that is a defect: every energy type needs enough test cases to score.
    Weighting each scenario by the inverse of how many share its energy source
    makes the energy distribution roughly flat within each pool.
    """
    per_energy: Counter = Counter(s.energy_source for s in pool)
    weights = [1.0 / per_energy[s.energy_source] for s in pool]
    return rng.choices(pool, weights=weights)[0]


def build_spec(target: SifClassification, rng: random.Random) -> ScenarioSpec:
    """Construct a spec guaranteed to classify as `target`."""
    if target is SifClassification.INSUFFICIENT_INFORMATION:
        return ScenarioSpec(
            scenario_key="vague",
            energy_source=None,
            high_energy=False,
            high_energy_incident=False,
            control_status=ControlStatus.UNKNOWN,
            direct_control_key="",
            injury=InjuryOutcome.NONE,
            report_kind=rng.choice(list(ReportKind)),
            primary_lsr=None,
            secondary_lsr=(),
            is_vague=True,
            style=lx.WritingStyle.TWO_LINE_VAGUE,
            language_mix=_pick_language(rng),
        )

    high_energy = target not in (SifClassification.LOW_SEVERITY, SifClassification.LSIF)
    pool = HIGH_ENERGY_SCENARIOS if high_energy else LOW_ENERGY_SCENARIOS
    scenario: Scenario = _pick_scenario(pool, rng)

    if target in (SifClassification.EXPOSURE, SifClassification.SUCCESS):
        incident = False
        report_kind = ReportKind.UNSAFE_CONDITION
        injury = InjuryOutcome.NONE
    else:
        incident = True
        report_kind = rng.choices(
            (ReportKind.NEAR_MISS, ReportKind.UNSAFE_ACT),
            weights=(0.65, 0.35),
        )[0]
        if target in (SifClassification.HSIF, SifClassification.LSIF):
            injury = rng.choices(
                (InjuryOutcome.SERIOUS_INJURY, InjuryOutcome.FATALITY),
                weights=(0.85, 0.15),
            )[0]
        elif target is SifClassification.PSIF:
            injury = rng.choices(
                (InjuryOutcome.NONE, InjuryOutcome.FIRST_AID, InjuryOutcome.MINOR_INJURY),
                weights=(0.72, 0.16, 0.12),
            )[0]
        elif target is SifClassification.CAPACITY:
            injury = rng.choices(
                (InjuryOutcome.NONE, InjuryOutcome.FIRST_AID),
                weights=(0.85, 0.15),
            )[0]
        else:  # LOW_SEVERITY - the injury-but-harmless trap lives here
            injury = rng.choices(
                (InjuryOutcome.MINOR_INJURY, InjuryOutcome.FIRST_AID, InjuryOutcome.NONE),
                weights=(0.50, 0.32, 0.18),
            )[0]

    if target in (SifClassification.CAPACITY, SifClassification.SUCCESS):
        control_status = ControlStatus.PRESENT_VERIFIED
    elif target is SifClassification.LOW_SEVERITY and injury is InjuryOutcome.NONE:
        control_status = rng.choice(
            (ControlStatus.PRESENT_VERIFIED,) + NON_PROTECTIVE_GENERATED
        )
    elif not high_energy:
        control_status = rng.choice(
            (ControlStatus.PRESENT_VERIFIED,) + NON_PROTECTIVE_GENERATED
        )
    elif target is SifClassification.EXPOSURE:
        # A condition, not an event. FAILED describes a control giving way,
        # which is a release - it cannot describe a standing condition, so it
        # is excluded here to keep the corpus internally coherent.
        static_states = (
            ControlStatus.ABSENT,
            ControlStatus.PRESENT_UNVERIFIED,
            ControlStatus.NOT_FOLLOWED,
            ControlStatus.BYPASSED,
        )
        control_status = rng.choices(static_states, weights=(0.38, 0.27, 0.20, 0.15))[0]
    else:
        control_status = rng.choices(
            NON_PROTECTIVE_GENERATED, weights=(0.34, 0.22, 0.20, 0.12, 0.12)
        )[0]

    # When a control was deliberately defeated, the governing Life-Saving Rule
    # IS "Bypassing Safety Controls" - that is precisely what the rule covers -
    # and the scenario's own rule drops to secondary. This mirrors how IOGP
    # would assign the rule that, followed, would have prevented the outcome.
    primary_lsr = scenario.primary_lsr
    secondary_lsr = scenario.secondary_lsr
    if control_status is ControlStatus.BYPASSED:
        primary_lsr = LifeSavingRule.BYPASSING_SAFETY_CONTROLS
        secondary_lsr = (scenario.primary_lsr,) + tuple(
            r for r in scenario.secondary_lsr if r is not LifeSavingRule.BYPASSING_SAFETY_CONTROLS
        )

    spec = ScenarioSpec(
        scenario_key=scenario.key,
        energy_source=scenario.energy_source,
        high_energy=high_energy,
        high_energy_incident=incident and high_energy,
        control_status=control_status,
        direct_control_key=scenario.direct_control_key,
        injury=injury,
        report_kind=report_kind,
        primary_lsr=primary_lsr,
        secondary_lsr=secondary_lsr,
        is_vague=False,
        style=_pick_style(rng),
        language_mix=_pick_language(rng),
    )

    got = derive_classification(spec)
    if got is not target:
        raise AssertionError(
            f"spec construction for {target.value} produced {got.value} "
            f"(scenario={scenario.key}, control={control_status.value}, injury={injury.value})"
        )
    return spec


# --------------------------------------------------------------------------
# Surface realisation
# --------------------------------------------------------------------------


def _phrase(slot: str, mix: lx.LanguageMix, rng: random.Random) -> str:
    """Realise a semantic slot in the report's language mix."""
    bank = lx.PHRASE_BANK[slot]
    if mix is lx.LanguageMix.HEAVY_CODE_MIX:
        choice_mix = rng.choice(
            [
                lx.LanguageMix.HINGLISH,
                lx.LanguageMix.HINDI_DEVANAGARI,
                lx.LanguageMix.ASSAMESE_ROMAN,
                lx.LanguageMix.ASSAMESE_SCRIPT,
                lx.LanguageMix.ENGLISH,
            ]
        )
    else:
        choice_mix = mix
    return rng.choice(bank.get(choice_mix, bank[lx.LanguageMix.ENGLISH]))


def _person(rng: random.Random) -> str:
    hon = rng.choice(lx.HONORIFICS)
    name = f"{rng.choice(lx.INITIALS)}. {rng.choice(lx.SURNAMES)}"
    return f"{hon} {name}".strip()


def _installation(rng: random.Random) -> str:
    return rng.choice(lx.INSTALLATION_TEMPLATES).format(
        rig=rng.randint(1, 120),
        small=rng.randint(1, 12),
        well=f"{rng.randint(100, 499)}",
        km=f"{rng.randint(1, 240)}",
    )


def _slots(rng: random.Random) -> dict[str, str]:
    return {
        "person": _person(rng),
        "designation": rng.choice(lx.DESIGNATIONS),
        "installation": _installation(rng),
        "location": rng.choice(lx.LOCATIONS),
        "height": rng.choice(("3", "4", "4.5", "5", "6", "8", "10", "12", "15", "18")),
        "load": rng.choice(("250", "400", "600", "800", "1200", "2500", "4000", "6")),
        "voltage": rng.choice(("415 V", "11 KV", "33 KV", "440 V", "3.3 KV")),
        "depth": rng.choice(("1.5", "1.8", "2", "2.5", "3", "3.5", "4")),
        "temp": rng.choice(("90", "110", "130", "150", "180", "200")),
        "speed": rng.choice(("40", "50", "55", "60", "70", "80")),
        "distance": rng.choice(("2", "3", "4", "5", "6", "8", "10", "12")),
        "tool_wt": rng.choice(("2", "3", "4", "5", "7", "9", "12")),
        "pax": rng.choice(("4", "5", "6", "8", "9", "11", "12")),
    }


def _opener(rng: random.Random) -> str:
    d, mo = rng.randint(1, 28), rng.randint(1, 12)
    y = rng.choice((2025, 2026))
    date = rng.choice(lx.DATE_FORMATS).format(d=d, mo=mo, y=y, y2=y % 100)
    time = rng.choice(lx.TIME_FORMATS).format(h=rng.randint(0, 23), m=rng.choice((0, 15, 30, 45, 10, 20)))
    return rng.choice(lx.REPORT_OPENERS).format(
        date=date, time=time, shift=rng.choice(lx.SHIFTS)
    )


INJURY_CLAUSES: dict[InjuryOutcome, tuple[str, ...]] = {
    InjuryOutcome.NONE: (
        "There was no injury to any personnel.",
        "Fortunately nobody was injured.",
        "No injury and no property damage.",
    ),
    InjuryOutcome.FIRST_AID: (
        "First aid was given at the installation.",
        "Minor first aid case, treated at site.",
        "First aid provided and workman resumed duty.",
    ),
    InjuryOutcome.MINOR_INJURY: (
        "He was shifted to OIL Hospital, {loc} and returned to duty the same day.",
        "Minor injury, dressing done at OIL Hospital and declared fit.",
        "Treated as a minor injury case, one day rest advised.",
    ),
    InjuryOutcome.SERIOUS_INJURY: (
        "He sustained serious injury and was shifted to OIL Hospital, Duliajan and later referred to Dibrugarh.",
        "Serious injury with fracture, admitted in hospital, LTI case.",
        "The injured was evacuated and is under treatment. Reportable injury.",
    ),
    InjuryOutcome.FATALITY: (
        "The workman succumbed to his injuries. Fatal case, statutory intimation given to DGMS.",
        "He was declared brought dead at the hospital. Fatality reported to authorities.",
    ),
}


def _apply_abbreviations(ann: Annotated, rng: random.Random, p: float) -> None:
    for full, short in lx.ABBREVIATION_SUBSTITUTIONS:
        idx = ann.text.lower().find(full)
        if idx != -1 and rng.random() < p:
            ann.splice(idx, idx + len(full), short)


def _apply_typos(ann: Annotated, rng: random.Random, p: float) -> None:
    for correct, wrong in lx.COMMON_MISSPELLINGS:
        idx = ann.text.find(correct)
        if idx != -1 and rng.random() < p:
            ann.splice(idx, idx + len(correct), wrong)

    # Character-level slips, applied right-to-left so earlier offsets hold.
    positions: list[int] = []
    cursor = 0
    for word in ann.text.split(" "):
        if len(word) > 5 and rng.random() < p * 0.12:
            positions.append(cursor + rng.randrange(1, len(word) - 1))
        cursor += len(word) + 1
    for at in sorted(positions, reverse=True):
        if at + 1 > len(ann.text):
            continue
        if rng.random() < 0.5:
            ann.splice(at, at + 1, "")                      # dropped letter
        else:
            ann.splice(at, at, ann.text[at])                 # doubled letter


def _drop_articles(ann: Annotated, rng: random.Random) -> None:
    for article in (" the ", " The ", " a ", " an "):
        while rng.random() < 0.6:
            idx = ann.text.find(article)
            if idx == -1:
                break
            ann.splice(idx, idx + len(article), " ")


def _apply_style_noise(ann: Annotated, style: lx.WritingStyle, rng: random.Random) -> None:
    """Field-report noise. Every edit goes through splice, so gold spans follow."""
    if style is lx.WritingStyle.TERSE_TELEGRAPHIC:
        _drop_articles(ann, rng)
        _apply_abbreviations(ann, rng, 0.75)
        if rng.random() < 0.5:
            ann.text = ann.text.lower()                      # length-preserving
        _apply_typos(ann, rng, 0.35)
    elif style is lx.WritingStyle.SUPERVISOR_FORMAL:
        _apply_abbreviations(ann, rng, 0.4)
        _apply_typos(ann, rng, 0.15)
    else:  # RAMBLING
        _apply_abbreviations(ann, rng, 0.3)
        _apply_typos(ann, rng, 0.28)

    if rng.random() < 0.22:
        idx = ann.text.find(". ")
        if idx != -1:
            ann.splice(idx, idx + 2, ".")
    if rng.random() < 0.15:
        idx = ann.text.find(". ")
        if idx != -1:
            ann.splice(idx, idx + 2, ".  ")
    if rng.random() < 0.12:
        words = ann.text.split(" ")
        if len(words) > 4:
            i = rng.randrange(len(words))
            at = sum(len(w) + 1 for w in words[:i])
            ann.splice(at, at + len(words[i]), words[i].upper())  # length-preserving
    if rng.random() < 0.18 and ann.text:
        ann.splice(0, 1, ann.text[0].lower())


def _mark_slots(ann: Annotated, clause: tuple[int, int], slots: dict[str, str]) -> None:
    """Slot fills are exact gold: the generator put those characters there."""
    for key in ("location", "installation"):
        hit = ann.find(slots[key], clause)
        if hit:
            ann.add(EntityLabel.LOCATION, *hit, provenance="slot")

    # A magnitude is the number PLUS its unit. Without that requirement the
    # slot value "2" matches inside "02.00 hrs" and the model learns that
    # timestamps are magnitude cues.
    units = (" mtr", " meter", " metre", " m ", " kg", " kmph", " km/h", " deg c",
             " volt", " v ", " kv", " ft", " inch", " db", " ppm", " km")
    for key in ("height", "depth", "voltage", "temp", "speed", "load", "distance", "tool_wt"):
        value = slots.get(key)
        if not value:
            continue
        search_from = clause[0]
        for _ in range(3):
            hit = ann.find(value, (search_from, clause[1]))
            if not hit:
                break
            start, end = hit
            before_ok = start == 0 or not ann.text[start - 1].isdigit()
            tail = ann.text[end : end + 16].lower()
            unit = next((u for u in units if tail.startswith(u)), None)
            if before_ok and unit:
                ann.add(EntityLabel.MAGNITUDE_CUE, start, end + len(unit.rstrip()), provenance="slot")
            search_from = end


def render_annotated(spec: ScenarioSpec, rng: random.Random) -> Annotated:
    """Render the report AND record what each character range means.

    Clause roles are ground truth — the generator chose them. Head phrases are
    located by lexicon lookup INSIDE the clause whose role is already known, so
    a miss produces a coarse-but-true label rather than a wrong one.
    """
    slots = _slots(rng)
    mix = spec.language_mix

    if spec.is_vague:
        body = rng.choice(VAGUE_TEMPLATES).format(**slots) + rng.choice(VAGUE_TAILS)
        if mix is not lx.LanguageMix.ENGLISH and rng.random() < 0.55:
            body += " " + _phrase(rng.choice(("was_advised", "no_injury")), mix, rng) + "."
        ann = Annotated(body)
        hit = ann.find(slots["location"])
        if hit:
            ann.add(EntityLabel.LOCATION, *hit, provenance="slot")
        hit = ann.find(slots["installation"])
        if hit:
            ann.add(EntityLabel.LOCATION, *hit, provenance="slot")
        _apply_style_noise(ann, lx.WritingStyle.TERSE_TELEGRAPHIC, rng)
        ann.text = ann.text.strip()
        ann.resolve_overlaps()
        return ann

    from prahari.data.scenarios import SCENARIOS_BY_KEY

    scenario = SCENARIOS_BY_KEY[spec.scenario_key]
    pieces: list[tuple[str, str]] = []  # (role, sentence)

    opener = _opener(rng)
    setup = rng.choice(scenario.setup).format(**slots)
    pieces.append(("setup", f"{opener} {setup}."))

    control = rng.choice(scenario.control[spec.control_status]).format(**slots)
    pieces.append(("control", f"{control.capitalize()}."))

    if spec.high_energy_incident or (not spec.high_energy and spec.injury is not InjuryOutcome.NONE):
        incident = rng.choice(scenario.incident).format(**slots)
        lead = _phrase("suddenly", mix, rng) if rng.random() < 0.3 else ""
        pieces.append(("incident", f"{(lead + ' ' if lead else '')}{incident}.".capitalize()))
    else:
        pieces.append(("incident", rng.choice(scenario.condition).format(**slots).capitalize() + "."))

    injury_clause = rng.choice(INJURY_CLAUSES[spec.injury]).replace("{loc}", slots["location"])
    if spec.injury is InjuryOutcome.NONE and mix is not lx.LanguageMix.ENGLISH and rng.random() < 0.7:
        injury_clause = _phrase("no_injury", mix, rng).capitalize() + "."
    pieces.append(("injury", injury_clause))

    hints = SCENARIO_PHRASE_HINTS.get(spec.scenario_key, ("was_working", "did_not_check"))
    if mix is not lx.LanguageMix.ENGLISH and rng.random() < 0.75:
        pieces.insert(
            rng.randrange(1, len(pieces)),
            ("aside", _phrase(rng.choice(hints), mix, rng).capitalize() + "."),
        )
    if rng.random() < 0.35:
        pieces.append(("action", _phrase(rng.choice(("job_stopped", "informed_supervisor", "was_advised")), mix, rng) + "."))
    if spec.high_energy and spec.injury is InjuryOutcome.NONE and rng.random() < 0.3:
        pieces.append(("action", _phrase("narrow_escape", mix, rng) + "."))
    if spec.style is lx.WritingStyle.RAMBLING:
        pieces.append(("action", rng.choice(lx.ACTION_CLAUSES)))
        if rng.random() < 0.5:
            pieces.append(("action", rng.choice(lx.ACTION_CLAUSES)))
    elif rng.random() < 0.55:
        pieces.append(("action", rng.choice(lx.ACTION_CLAUSES)))

    # Assemble, remembering where each clause landed.
    text_parts: list[str] = []
    bounds: dict[str, list[tuple[int, int]]] = {}
    cursor = 0
    for role, sentence in pieces:
        text_parts.append(sentence)
        bounds.setdefault(role, []).append((cursor, cursor + len(sentence)))
        cursor += len(sentence) + 1

    ann = Annotated(" ".join(text_parts))

    setup_span = bounds["setup"][0]
    control_span = bounds["control"][0]

    _mark_slots(ann, setup_span, slots)
    _mark_slots(ann, control_span, slots)
    for span in bounds.get("incident", []):
        _mark_slots(ann, span, slots)

    # ACTIVITY: the setup clause is, by construction, the description of the
    # work. Marked clause-wide minus the date opener; more specific labels
    # override it in resolve_overlaps().
    activity_start = setup_span[0] + len(_opener_prefix(ann.text, setup_span))
    ann.add(EntityLabel.ACTIVITY, activity_start, setup_span[1] - 1, provenance="clause:setup")

    # ENERGY_SOURCE: head phrases, found only inside clauses whose role the
    # generator already knows describe the hazard.
    energy_def = ENERGY_SOURCES[scenario.energy_source]
    hazard_clauses = [setup_span, *bounds.get("incident", [])]
    for phrase in sorted(energy_def.trigger_phrases, key=len, reverse=True):
        for zone in hazard_clauses:
            hit = ann.find(phrase, zone)
            if hit:
                ann.add(EntityLabel.ENERGY_SOURCE, *hit, provenance="lexicon@hazard")

    # CONTROL_MENTION: the scenario's own direct control, inside its clause.
    control_def = CONTROLS_BY_KEY.get(scenario.direct_control_key)
    if control_def:
        for phrase in sorted(control_def.phrases, key=len, reverse=True):
            hit = ann.find(phrase, control_span)
            if hit:
                ann.add(EntityLabel.CONTROL_MENTION, *hit, provenance="lexicon@control")

    # CONTROL_NEGATION: only where the control is actually degraded. A verified
    # control has no negation, and that absence is itself signal.
    if spec.control_status is not ControlStatus.PRESENT_VERIFIED:
        found = False
        for status, patterns in _STATUS_PATTERNS:
            if status is not spec.control_status:
                continue
            for pattern in patterns:
                match = re.search(pattern, ann.text[control_span[0] : control_span[1]], re.IGNORECASE)
                if match:
                    ann.add(
                        EntityLabel.CONTROL_NEGATION,
                        control_span[0] + match.start(),
                        control_span[0] + match.end(),
                        provenance="regex@control",
                    )
                    found = True
                    break
            if found:
                break
        if not found:
            # True but coarse: the generator knows this clause asserts a
            # degraded control, even when no pattern located the head phrase.
            ann.add(
                EntityLabel.CONTROL_NEGATION,
                control_span[0],
                control_span[1] - 1,
                provenance="clause:control",
            )

    _apply_style_noise(ann, spec.style, rng)
    stripped = ann.text.strip()
    if stripped != ann.text:
        lead = len(ann.text) - len(ann.text.lstrip())
        if lead:
            ann.splice(0, lead, "")
        ann.text = ann.text.rstrip()
    ann.resolve_overlaps()
    return ann


#: A leading date/time/shift preamble, which is not part of the activity.
_OPENER_RE = re.compile(
    r"^.{0,80}?(?:hrs|shift|\d{2}[./-]\d{2}[./-]\d{2,4})\s*[,.\-:]*\s*",
    re.IGNORECASE,
)


def _opener_prefix(text: str, clause: tuple[int, int]) -> str:
    """The date/time preamble at the front of the setup clause, if any."""
    match = _OPENER_RE.match(text[clause[0] : clause[1]])
    return match.group(0) if match else ""


def render(spec: ScenarioSpec, rng: random.Random) -> str:
    """Text only. Kept for callers that do not need the annotation."""
    return render_annotated(spec, rng).text


# --------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------


def _hard_case_kind(spec: ScenarioSpec, label: SifClassification) -> str | None:
    if label is SifClassification.INSUFFICIENT_INFORMATION:
        return "underdetermined"
    if label in (SifClassification.PSIF, SifClassification.EXPOSURE) and spec.injury is InjuryOutcome.NONE:
        return "high_potential_no_outcome"
    if label is SifClassification.LOW_SEVERITY and spec.injury in (
        InjuryOutcome.MINOR_INJURY,
        InjuryOutcome.FIRST_AID,
    ):
        return "visible_injury_low_potential"
    if label in (SifClassification.CAPACITY, SifClassification.SUCCESS):
        return "controlled_high_energy"
    return None


def build_record(index: int, target: SifClassification, rng: random.Random) -> dict:
    spec = build_spec(target, rng)
    label = derive_classification(spec)
    annotated = render_annotated(spec, rng)
    text = annotated.text
    hard = _hard_case_kind(spec, label)

    determinable = not spec.is_vague
    return {
        "report_id": f"OIL-SR-{index:06d}",
        "text": text,
        "report_kind": spec.report_kind.value,
        "writing_style": spec.style.value,
        "language_mix": spec.language_mix.value,
        "labels": {
            "sif_classification": label.value,
            "energy_source": spec.energy_source.value if determinable and spec.energy_source else None,
            "high_energy": spec.high_energy if determinable else None,
            "high_energy_incident": spec.high_energy_incident if determinable else None,
            "control_status": spec.control_status.value if determinable else None,
            "direct_control_key": spec.direct_control_key or None if determinable else None,
            "direct_control_effective": spec.direct_control_effective if determinable else None,
            "injury_outcome": spec.injury.value if determinable else None,
            "primary_lsr": spec.primary_lsr.value if determinable and spec.primary_lsr else None,
            "secondary_lsr": [r.value for r in spec.secondary_lsr] if determinable else [],
        },
        #: Character-level entity spans for training the ML extractor. These
        #: come from what the generator KNOWS it wrote, not from running the
        #: keyword extractor over the output — a model trained on the latter
        #: could only ever imitate the keyword extractor. See data/annotation.py.
        "gold_spans": [sp.as_dict(text) for sp in annotated.spans],
        "meta": {
            "scenario_key": spec.scenario_key,
            "is_hard_case": hard is not None,
            "hard_case_kind": hard,
            "labels_determinable_from_text": determinable,
            "split": None,
        },
    }


def generate(n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    classes = list(CLASS_DISTRIBUTION)
    weights = [CLASS_DISTRIBUTION[c] for c in classes]
    targets = rng.choices(classes, weights=weights, k=n)
    return [build_record(i + 1, t, rng) for i, t in enumerate(targets)]


def stratified_split(
    records: list[dict],
    seed: int,
    ratios: tuple[float, float, float] = (0.70, 0.15, 0.15),
) -> list[dict]:
    """Assign train/val/test, stratified on the SIF classification label."""
    rng = random.Random(seed + 1)
    by_class: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_class[r["labels"]["sif_classification"]].append(r)

    for _, group in sorted(by_class.items()):
        rng.shuffle(group)
        n = len(group)
        n_train = int(round(n * ratios[0]))
        n_val = int(round(n * ratios[1]))
        n_train = min(n_train, n)
        n_val = min(n_val, n - n_train)
        for i, rec in enumerate(group):
            rec["meta"]["split"] = (
                "train" if i < n_train else "val" if i < n_train + n_val else "test"
            )
    return records


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def _bar(count: int, total: int, width: int = 28) -> str:
    filled = int(round(width * count / total)) if total else 0
    return "#" * filled + "." * (width - filled)


def _table(title: str, counter: Counter, total: int) -> str:
    lines = [f"\n{title}", "-" * 74]
    for key, count in counter.most_common():
        lines.append(f"  {str(key):<34} {count:>5}  {100 * count / total:>5.1f}%  {_bar(count, total)}")
    return "\n".join(lines)


def summarise(records: list[dict]) -> str:
    total = len(records)
    out: list[str] = [f"\n{'=' * 74}", f"prahari synthetic report set - {total} records", "=" * 74]

    out.append(_table("SIF classification (ground truth)", Counter(r["labels"]["sif_classification"] for r in records), total))
    out.append(_table("Energy source", Counter(r["labels"]["energy_source"] or "(not determinable)" for r in records), total))
    out.append(_table("Control status", Counter(r["labels"]["control_status"] or "(not determinable)" for r in records), total))
    out.append(_table("Primary Life-Saving Rule", Counter(r["labels"]["primary_lsr"] or "(not determinable)" for r in records), total))
    out.append(_table("Injury outcome", Counter(r["labels"]["injury_outcome"] or "(not determinable)" for r in records), total))
    out.append(_table("Report kind", Counter(r["report_kind"] for r in records), total))
    out.append(_table("Language mix", Counter(r["language_mix"] for r in records), total))
    out.append(_table("Writing style", Counter(r["writing_style"] for r in records), total))
    out.append(_table("Hard cases", Counter(r["meta"]["hard_case_kind"] or "(ordinary)" for r in records), total))

    # split integrity
    split_counts = Counter(r["meta"]["split"] for r in records)
    out.append(_table("Split", split_counts, total))
    out.append("\nPer-split class distribution (stratification check)")
    out.append("-" * 74)
    classes = sorted({r["labels"]["sif_classification"] for r in records})
    header = f"  {'class':<28}" + "".join(f"{s:>12}" for s in ("train", "val", "test"))
    out.append(header)
    for cls in classes:
        row = f"  {cls:<28}"
        for split in ("train", "val", "test"):
            n_split = split_counts[split]
            c = sum(
                1 for r in records
                if r["meta"]["split"] == split and r["labels"]["sif_classification"] == cls
            )
            row += f"{c:>6} {100 * c / n_split if n_split else 0:>5.1f}%"
        out.append(row)

    n_hard = sum(1 for r in records if r["meta"]["is_hard_case"])
    n_money = sum(1 for r in records if r["meta"]["hard_case_kind"] == "high_potential_no_outcome")
    n_trap = sum(1 for r in records if r["meta"]["hard_case_kind"] == "visible_injury_low_potential")
    out.append("\n" + "=" * 74)
    out.append(f"  hard cases                          {n_hard:>5}  ({100 * n_hard / total:.1f}%)")
    out.append(f"  high fatal potential, zero outcome  {n_money:>5}  ({100 * n_money / total:.1f}%)")
    out.append(f"  visible injury, no fatal potential  {n_trap:>5}  ({100 * n_trap / total:.1f}%)")
    out.append(f"  unique scenarios used               {len({r['meta']['scenario_key'] for r in records}):>5}")
    out.append(f"  unique report texts                 {len({r['text'] for r in records}):>5}")
    out.append("=" * 74)
    return "\n".join(out)


def write_jsonl(records: Iterable[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _default_out() -> Path:
    """Repo-root data/ directory, resolved from this file's location."""
    return Path(__file__).resolve().parents[3] / "data" / "synthetic_reports.jsonl"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m prahari.data.generator",
        description="Generate labelled synthetic OIL safety reports for SIF precursor evaluation.",
    )
    parser.add_argument("--n", type=int, default=3000, help="number of records (default 3000)")
    parser.add_argument("--seed", type=int, default=42, help="random seed (default 42)")
    parser.add_argument("--out", type=Path, default=None, help="output .jsonl path")
    parser.add_argument("--samples", type=int, default=0, help="print N example reports")
    parser.add_argument("--no-summary", action="store_true", help="suppress the distribution summary")
    args = parser.parse_args(argv)

    out_path = args.out or _default_out()
    records = generate(args.n, args.seed)
    records = stratified_split(records, args.seed)
    write_jsonl(records, out_path)

    if not args.no_summary:
        print(summarise(records))
    if args.samples:
        print("\n" + "=" * 74 + "\nSAMPLE REPORTS\n" + "=" * 74)
        rng = random.Random(args.seed + 7)
        for rec in rng.sample(records, min(args.samples, len(records))):
            lb = rec["labels"]
            print(f"\n[{rec['report_id']}] {rec['report_kind']} | {rec['language_mix']} | {rec['writing_style']}")
            print(f"  {rec['text']}")
            print(
                f"  -> {lb['sif_classification'].upper()} | energy={lb['energy_source']} | "
                f"control={lb['control_status']} | injury={lb['injury_outcome']} | LSR={lb['primary_lsr']}"
            )
    print(f"\nWrote {len(records)} records to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
