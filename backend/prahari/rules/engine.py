"""The deterministic rule engine. This is what decides.

No model output reaches this file. The engine consumes structured facts with
character spans and applies NAMED rules, each of which records what it
concluded, why, and the exact spans that made it conclude that. The verdict is
reconstructible by a human reading the rule firings alone.

Two conventions that a safety professional will want explained:

MOST-DEGRADED-WINS. If a report contains signals for more than one control
state, the worst one governs. "Harness was inspected but he did not tie off"
resolves to NOT_FOLLOWED, not PRESENT_VERIFIED. Optimistic resolution would let
a single reassuring phrase clear a genuinely uncontrolled job.

ABSENCE OF EVIDENCE IS NOT A CONTROL. Where a high-energy hazard is established
but no direct control is mentioned at all, the engine records ABSENT, not
"probably fine". This is the SCL convention and it is deliberately
conservative: it produces false precursors, never false clears.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prahari.domain.citations import EEI_HECA, EEI_SCL, IOGP_459, PRAHARI_MODELLING
from prahari.domain.classification import (
    SCL_DECISION_TABLE,
    SERIOUS_OUTCOMES,
    InjuryOutcome,
    SifClassification,
)
from prahari.domain.controls import CONTROLS_BY_KEY, ControlStatus, PROTECTIVE_STATUSES
from prahari.domain.energy import EnergySource
from prahari.domain.high_energy import CUES_BY_KEY, HIGH_ENERGY_THRESHOLD_JOULES
from prahari.domain.lsr import LSR_BY_ENERGY, LifeSavingRule
from prahari.ml import extract_facts
from prahari.ml.extractor import ExtractedFacts, FactType, Span

ENGINE_VERSION = "engine-v0.1"

#: Worst state wins. See MOST-DEGRADED-WINS above.
_STATUS_SEVERITY: dict[ControlStatus, int] = {
    ControlStatus.BYPASSED: 6,
    ControlStatus.FAILED: 5,
    ControlStatus.NOT_FOLLOWED: 4,
    ControlStatus.ABSENT: 3,
    ControlStatus.PRESENT_UNVERIFIED: 2,
    ControlStatus.PRESENT_VERIFIED: 1,
    ControlStatus.UNKNOWN: 0,
}

_INJURY_SEVERITY: dict[InjuryOutcome, int] = {
    InjuryOutcome.FATALITY: 5,
    InjuryOutcome.SERIOUS_INJURY: 4,
    InjuryOutcome.MINOR_INJURY: 3,
    InjuryOutcome.FIRST_AID: 2,
    InjuryOutcome.NONE: 1,
}

#: measurement name -> (cue key, threshold, comparison unit note)
_MEASUREMENT_THRESHOLDS: dict[str, tuple[str, float]] = {
    "height_m": ("fall_from_elevation", 1.2),
    "depth_m": ("excavation_depth", 1.5),
    "voltage_v": ("voltage_at_or_above_50v", 50.0),
    "voltage_kv": ("voltage_at_or_above_50v", 0.05),
    "mass_kg": ("suspended_load", 227.0),
    "speed_kmph": ("motor_vehicle_speed", 48.0),
    "temp_c": ("temperature_at_or_above_65c", 65.0),
}


@dataclass(frozen=True, slots=True)
class RuleFiring:
    """One named rule that fired, with the evidence that made it fire."""

    rule_id: str
    description: str
    conclusion: str
    spans: tuple[Span, ...]
    citation_key: str


@dataclass(frozen=True, slots=True)
class SifVerdict:
    """The engine's answer. Every field is traceable through `fired_rules`."""

    classification: SifClassification
    energy_source: EnergySource | None
    high_energy: bool
    high_energy_incident: bool
    control_status: ControlStatus
    direct_control_key: str | None
    direct_control_effective: bool
    injury_outcome: InjuryOutcome
    primary_lsr: LifeSavingRule | None
    secondary_lsr: tuple[LifeSavingRule, ...]
    fired_rules: tuple[RuleFiring, ...]
    evidence_completeness: float
    engine_version: str = ENGINE_VERSION

    @property
    def is_precursor(self) -> bool:
        return self.classification in (SifClassification.PSIF, SifClassification.EXPOSURE)

    @property
    def all_spans(self) -> tuple[Span, ...]:
        seen: dict[tuple[int, int], Span] = {}
        for firing in self.fired_rules:
            for sp in firing.spans:
                seen[(sp.start, sp.end)] = sp
        return tuple(sorted(seen.values(), key=lambda s: (s.start, s.end)))


def _spans(facts: ExtractedFacts, fact_type: FactType, value: str | None = None) -> tuple[Span, ...]:
    return tuple(
        f.span for f in facts.of_type(fact_type) if value is None or f.value == value
    )


def evaluate(facts: ExtractedFacts) -> SifVerdict:
    """Apply the rules. Deterministic; identical facts give identical verdicts."""
    fired: list[RuleFiring] = []

    # -- R-ENERGY-01 -------------------------------------------------------
    energy_facts = facts.of_type(FactType.ENERGY_PHRASE)
    energy_source: EnergySource | None = None
    if energy_facts:
        counts: dict[str, int] = {}
        first_at: dict[str, int] = {}
        for f in energy_facts:
            counts[f.value] = counts.get(f.value, 0) + 1
            first_at.setdefault(f.value, f.span.start)
        best = max(counts, key=lambda v: (counts[v], -first_at[v]))
        energy_source = EnergySource(best)
        fired.append(
            RuleFiring(
                rule_id="R-ENERGY-01",
                description=(
                    "Energy source is the Energy Wheel category with the most trigger "
                    "phrases in the report; ties broken by earliest mention."
                ),
                conclusion=f"energy_source={best}",
                spans=_spans(facts, FactType.ENERGY_PHRASE, best),
                citation_key=EEI_SCL.key,
            )
        )

    # -- R-HE-01 / R-HE-02 -------------------------------------------------
    high_energy = False
    he_spans: list[Span] = []
    cue_facts = facts.of_type(FactType.HIGH_ENERGY_CUE)
    if cue_facts:
        high_energy = True
        he_spans.extend(f.span for f in cue_facts)
        fired.append(
            RuleFiring(
                rule_id="R-HE-01",
                description=(
                    f"A published high-energy cue was present, implying a release "
                    f"above the {HIGH_ENERGY_THRESHOLD_JOULES} J threshold."
                ),
                conclusion="high_energy=True",
                spans=tuple(f.span for f in cue_facts),
                citation_key=EEI_HECA.key,
            )
        )

    for f in facts.of_type(FactType.MEASUREMENT):
        mapping = _MEASUREMENT_THRESHOLDS.get(f.value)
        if not mapping or f.detail is None:
            continue
        cue_key, threshold = mapping
        try:
            magnitude = float(f.detail)
        except ValueError:
            continue
        if magnitude >= threshold:
            high_energy = True
            he_spans.append(f.span)
            cue = CUES_BY_KEY[cue_key]
            fired.append(
                RuleFiring(
                    rule_id="R-HE-02",
                    description=(
                        f"Measured magnitude {magnitude} met or exceeded the published "
                        f"threshold {threshold} {cue.threshold_unit or ''} for '{cue.label}'."
                    ),
                    conclusion="high_energy=True",
                    spans=(f.span,),
                    citation_key=EEI_HECA.key,
                )
            )

    if not high_energy:
        fired.append(
            RuleFiring(
                rule_id="R-HE-03",
                description=(
                    "No high-energy cue phrase and no measurement above a published "
                    "threshold were found, so the hazard is treated as low energy."
                ),
                conclusion="high_energy=False",
                spans=(),
                citation_key=EEI_HECA.key,
            )
        )

    # -- R-CTRL-01 / R-CTRL-02 / R-CTRL-03 --------------------------------
    # Status signals are attributed to the control named in the SAME sentence.
    # Report-wide "most degraded wins" was too blunt: a negation anywhere in a
    # long report would condemn a control that a different sentence verified.
    status_facts = facts.of_type(FactType.CONTROL_STATUS)
    control_mentions = facts.of_type(FactType.CONTROL_MENTION)
    direct_mentions = tuple(m for m in control_mentions if m.detail == "direct")

    paired: list[tuple[str, ControlStatus, tuple[Span, ...]]] = []
    for mention in control_mentions:
        sent = facts.sentence_index_of(mention.span)
        if sent < 0:
            continue
        same = [f for f in status_facts if facts.sentence_index_of(f.span) == sent]
        if not same:
            continue
        worst_here = max(same, key=lambda f: _STATUS_SEVERITY[ControlStatus(f.value)])
        paired.append(
            (
                mention.value,
                ControlStatus(worst_here.value),
                (mention.span,) + tuple(f.span for f in same if f.value == worst_here.value),
            )
        )

    direct_pairs = [p for p in paired if CONTROLS_BY_KEY[p[0]].is_direct]
    chosen_pairs = direct_pairs or paired

    direct_control_key: str | None = None
    if chosen_pairs:
        # Most degraded among the controls actually described.
        control_key, control_status, status_spans = max(
            chosen_pairs, key=lambda p: _STATUS_SEVERITY[p[1]]
        )
        direct_control_key = control_key
        fired.append(
            RuleFiring(
                rule_id="R-CTRL-01",
                description=(
                    "Control status is taken from the status signal in the same "
                    "sentence as the control it describes. Where a report describes "
                    "several controls, the most degraded direct control governs."
                ),
                conclusion=f"control_status={control_status.value} for '{control_key}'",
                spans=status_spans,
                citation_key=EEI_HECA.key,
            )
        )
    elif direct_mentions:
        direct_control_key = direct_mentions[0].value
        control_status = ControlStatus.PRESENT_UNVERIFIED
        fired.append(
            RuleFiring(
                rule_id="R-CTRL-03",
                description=(
                    "A direct control was named but the report records no verification "
                    "of it. Limb (b) of the direct control test requires the control to "
                    "be installed, VERIFIED and used properly."
                ),
                conclusion="control_status=present_unverified",
                spans=tuple(m.span for m in direct_mentions),
                citation_key=EEI_HECA.key,
            )
        )
    elif status_facts:
        worst = max(status_facts, key=lambda f: _STATUS_SEVERITY[ControlStatus(f.value)])
        control_status = ControlStatus(worst.value)
        direct_control_key = control_mentions[0].value if control_mentions else None
        fired.append(
            RuleFiring(
                rule_id="R-CTRL-05",
                description=(
                    "A control state was signalled without naming the control. The most "
                    "degraded signal governs."
                ),
                conclusion=f"control_status={control_status.value}",
                spans=_spans(facts, FactType.CONTROL_STATUS, worst.value),
                citation_key=EEI_HECA.key,
            )
        )
    else:
        control_status = ControlStatus.ABSENT
        fired.append(
            RuleFiring(
                rule_id="R-CTRL-02",
                description=(
                    "No direct control was mentioned. Absence of evidence of a control "
                    "is recorded as ABSENT, never as adequate."
                ),
                conclusion="control_status=absent",
                spans=(),
                citation_key=EEI_SCL.key,
            )
        )

    control_is_direct = bool(direct_control_key) and CONTROLS_BY_KEY[direct_control_key].is_direct
    if direct_control_key and not control_is_direct:
        fired.append(
            RuleFiring(
                rule_id="R-CTRL-04",
                description=(
                    f"The only control named ('{CONTROLS_BY_KEY[direct_control_key].label}') "
                    "is an INDIRECT control and cannot satisfy the three-part direct "
                    "control test. It does not count towards protection."
                ),
                conclusion="direct_control_present=False",
                spans=tuple(m.span for m in control_mentions if m.value == direct_control_key),
                citation_key=EEI_SCL.key,
            )
        )

    effective = control_status in PROTECTIVE_STATUSES and control_is_direct
    fired.append(
        RuleFiring(
            rule_id="R-EFFECT-01",
            description=(
                "A control protects only when it is a DIRECT control AND its status is "
                "PRESENT_VERIFIED. Unverified, absent, failed, bypassed and not-followed "
                "all mean unprotected."
            ),
            conclusion=f"direct_control_effective={effective}",
            spans=tuple(m.span for m in direct_mentions),
            citation_key=EEI_HECA.key,
        )
    )

    # -- R-INJ-01 ----------------------------------------------------------
    injury_facts = facts.of_type(FactType.INJURY)
    if injury_facts:
        worst_inj = max(injury_facts, key=lambda f: _INJURY_SEVERITY[InjuryOutcome(f.value)])
        injury = InjuryOutcome(worst_inj.value)
        inj_spans = _spans(facts, FactType.INJURY, worst_inj.value)
    else:
        injury = InjuryOutcome.NONE
        inj_spans = ()
    fired.append(
        RuleFiring(
            rule_id="R-INJ-01",
            description="Injury outcome is the most severe outcome stated in the report.",
            conclusion=f"injury_outcome={injury.value}",
            spans=inj_spans,
            citation_key=EEI_SCL.key,
        )
    )

    # -- R-EVENT-01 --------------------------------------------------------
    # A control clause that describes the control giving way ("the sling
    # parted") reads like an event but is a description of the control state,
    # not proof that energy reached anyone. So release markers are only counted
    # when they appear OUTSIDE the sentence that established the control state.
    incident_facts = facts.of_type(FactType.INCIDENT_MARKER)
    condition_facts = facts.of_type(FactType.CONDITION_MARKER)
    # Exclude only markers that ARE the control-state phrase, not everything in
    # the same sentence. "The sling parted and the load dropped from 4 mtr"
    # states both a control failure and a real release in one sentence;
    # discarding the whole sentence loses the release and mis-reads a genuine
    # PSIF as a mere Exposure.
    status_spans = [
        sp
        for firing in fired
        if firing.rule_id.startswith("R-CTRL")
        for sp in firing.spans
    ]

    def _overlaps_status(span: Span) -> bool:
        return any(span.start < sp.end and sp.start < span.end for sp in status_spans)

    independent_incidents = tuple(f for f in incident_facts if not _overlaps_status(f.span))
    serious = injury in SERIOUS_OUTCOMES

    if serious:
        event_occurred, reason = True, "a serious injury was sustained, so energy reached a person"
    elif independent_incidents and not condition_facts:
        event_occurred, reason = True, "an energy release is described outside the control clause"
    elif independent_incidents and len(independent_incidents) > len(condition_facts):
        event_occurred, reason = True, "release markers outweigh observation markers"
    elif condition_facts:
        event_occurred, reason = False, "the report describes a standing condition, not a release"
    else:
        event_occurred = bool(independent_incidents)
        reason = "no observation marker present" if event_occurred else "no release described"

    high_energy_incident = high_energy and event_occurred
    fired.append(
        RuleFiring(
            rule_id="R-EVENT-01",
            description=(
                "The SCL table distinguishes an incident (a release) from a condition "
                f"(a hazard observed). Here {reason}."
            ),
            conclusion=f"high_energy_incident={high_energy_incident}",
            spans=tuple(f.span for f in (independent_incidents if event_occurred else condition_facts)),
            citation_key=EEI_SCL.key,
        )
    )

    # -- Completeness ------------------------------------------------------
    slots_found = sum(
        (
            energy_source is not None,
            bool(cue_facts or facts.of_type(FactType.MEASUREMENT)),
            bool(status_facts or control_mentions),
            bool(incident_facts or condition_facts or injury_facts),
        )
    )
    completeness = round(slots_found / 4.0, 4)

    # -- R-INSUF-01 --------------------------------------------------------
    # A low-energy report does not need an identified energy source: the SCL
    # table marks the incident and control columns "N/A" on its low-energy rows,
    # so an injury outcome alone determines LSIF vs LOW_SEVERITY. Insufficiency
    # is therefore only declared when the report establishes essentially nothing.
    real_injury = [f for f in injury_facts if f.value != InjuryOutcome.NONE.value]
    establishes_nothing = (
        energy_source is None
        and not cue_facts
        and not facts.of_type(FactType.MEASUREMENT)
        and not direct_mentions
        and not real_injury
    )
    if establishes_nothing:
        fired.append(
            RuleFiring(
                rule_id="R-INSUF-01",
                description=(
                    "The report does not establish an energy source and a control state, "
                    "so no SCL class follows from it. Saying so is the correct answer; "
                    "guessing is not."
                ),
                conclusion="classification=insufficient_information",
                spans=(),
                citation_key=PRAHARI_MODELLING.key,
            )
        )
        return SifVerdict(
            classification=SifClassification.INSUFFICIENT_INFORMATION,
            energy_source=energy_source,
            high_energy=high_energy,
            high_energy_incident=high_energy_incident,
            control_status=ControlStatus.UNKNOWN,
            direct_control_key=direct_control_key,
            direct_control_effective=False,
            injury_outcome=injury,
            primary_lsr=None,
            secondary_lsr=(),
            fired_rules=tuple(fired),
            evidence_completeness=completeness,
        )

    # -- R-CLASS-01 --------------------------------------------------------
    classification = SCL_DECISION_TABLE[(high_energy, high_energy_incident, effective, serious)]
    fired.append(
        RuleFiring(
            rule_id="R-CLASS-01",
            description=(
                "SCL classification by table lookup on (high energy, high-energy "
                f"incident, direct control effective, serious injury) = "
                f"({high_energy}, {high_energy_incident}, {effective}, {serious})."
            ),
            conclusion=f"classification={classification.value}",
            spans=tuple(he_spans) + inj_spans,
            citation_key=EEI_SCL.key,
        )
    )

    # -- R-LSR-01 / R-LSR-02 ----------------------------------------------
    lsr_facts = facts.of_type(FactType.LSR_PHRASE)
    primary_lsr: LifeSavingRule | None = None
    lsr_spans: tuple[Span, ...] = ()
    if control_status is ControlStatus.BYPASSED:
        primary_lsr = LifeSavingRule.BYPASSING_SAFETY_CONTROLS
        lsr_spans = _spans(facts, FactType.CONTROL_STATUS, ControlStatus.BYPASSED.value)
        fired.append(
            RuleFiring(
                rule_id="R-LSR-02",
                description=(
                    "A control that was deliberately defeated engages the Bypassing "
                    "Safety Controls rule as the governing rule; the activity's own "
                    "rule becomes secondary."
                ),
                conclusion=f"primary_lsr={primary_lsr.value}",
                spans=lsr_spans,
                citation_key=IOGP_459.key,
            )
        )
    elif lsr_facts:
        counts = {}
        for f in lsr_facts:
            counts[f.value] = counts.get(f.value, 0) + 1
        allowed = {r.value for r in LSR_BY_ENERGY.get(energy_source, ())} if energy_source else set()
        ranked = sorted(counts, key=lambda v: (v in allowed, counts[v]), reverse=True)
        primary_lsr = LifeSavingRule(ranked[0])
        lsr_spans = _spans(facts, FactType.LSR_PHRASE, ranked[0])
        fired.append(
            RuleFiring(
                rule_id="R-LSR-01",
                description=(
                    "Primary Life-Saving Rule is the most-cued rule, preferring rules "
                    "the Energy Wheel maps to this energy source."
                ),
                conclusion=f"primary_lsr={primary_lsr.value}",
                spans=lsr_spans,
                citation_key=IOGP_459.key,
            )
        )
    elif energy_source is not None and LSR_BY_ENERGY.get(energy_source):
        primary_lsr = LSR_BY_ENERGY[energy_source][0]
        fired.append(
            RuleFiring(
                rule_id="R-LSR-03",
                description=(
                    "No rule was cued directly, so the first Life-Saving Rule mapped to "
                    "the identified energy source is used."
                ),
                conclusion=f"primary_lsr={primary_lsr.value}",
                spans=(),
                citation_key=IOGP_459.key,
            )
        )

    secondary: tuple[LifeSavingRule, ...] = ()
    if energy_source is not None:
        secondary = tuple(
            r for r in LSR_BY_ENERGY.get(energy_source, ()) if r is not primary_lsr
        )[:3]

    return SifVerdict(
        classification=classification,
        energy_source=energy_source,
        high_energy=high_energy,
        high_energy_incident=high_energy_incident,
        control_status=control_status,
        direct_control_key=direct_control_key,
        direct_control_effective=effective,
        injury_outcome=injury,
        primary_lsr=primary_lsr,
        secondary_lsr=secondary,
        fired_rules=tuple(fired),
        evidence_completeness=completeness,
    )


def analyse(text: str) -> tuple[ExtractedFacts, SifVerdict]:
    """Extract then decide. The only entry point the API needs.

    Which extractor runs is decided in `prahari.ml`; the rules below are
    identical either way. Nothing in this module knows or cares whether a
    transformer or a phrase list produced the facts.
    """
    facts = extract_facts(text)
    return facts, evaluate(facts)
