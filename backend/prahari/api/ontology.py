"""The ontology, served as data - for the Ontology Explorer view.

Everything here is READ from `prahari.domain` (and one rule catalogue that a
test keeps in lock-step with `rules/engine.py`). No vocabulary is duplicated
into the frontend: the browser renders what the engine actually uses, so the
explorer can never describe a rule set the engine does not run.
"""

from __future__ import annotations

from prahari.domain.citations import ALL_CITATIONS
from prahari.domain.classification import CLASSIFICATIONS, SIF_PRECURSOR_CLASSES
from prahari.domain.controls import (
    ALL_CONTROLS,
    DIRECT_CONTROL_TEST,
    PROTECTIVE_STATUSES,
    ControlClass,
    ControlStatus,
)
from prahari.domain.energy import ENERGY_SOURCES
from prahari.domain.high_energy import CUES_BY_ENERGY, HIGH_ENERGY_THRESHOLD_JOULES
from prahari.domain.lsr import LIFE_SAVING_RULES, LSR_BY_ENERGY
from prahari.rules.engine import ENGINE_VERSION

#: What each observed barrier state means. Wording follows the three-part
#: direct control test (EEI HECA): only a verified control protects.
CONTROL_STATUS_MEANING: dict[ControlStatus, str] = {
    ControlStatus.PRESENT_VERIFIED: "Control was in place and the report records it being checked or proven effective.",
    ControlStatus.PRESENT_UNVERIFIED: "Control was mentioned but nobody verified it. Fails limb (b) of the direct control test - not yet a control.",
    ControlStatus.ABSENT: "No control was in place, or none is mentioned. Absence of evidence is never read as adequate.",
    ControlStatus.FAILED: "Control was in place but did not work (sling parted, PRV did not lift, guard broke).",
    ControlStatus.BYPASSED: "Control was deliberately defeated or overridden. Engages the Bypassing Safety Controls rule.",
    ControlStatus.NOT_FOLLOWED: "Control existed but the crew did not use it (harness worn but not tied off, permit not taken).",
    ControlStatus.UNKNOWN: "A control state was signalled but could not be resolved to a specific barrier.",
}

#: Every rule id `rules/engine.py` can emit, with a stable one-line summary.
#: `tests/api/test_ontology.py` fails if the engine gains or loses an id that
#: is not reflected here.
RULE_CATALOGUE: tuple[dict[str, str], ...] = (
    {"id": "R-ENERGY-01", "stage": "Energy", "summary": "Energy source = the Energy Wheel category with the most trigger phrases; ties go to the earliest mention."},
    {"id": "R-HE-01", "stage": "Energy", "summary": f"A published high-energy cue is present, implying a release above {HIGH_ENERGY_THRESHOLD_JOULES} J."},
    {"id": "R-HE-02", "stage": "Energy", "summary": "A measured magnitude meets or exceeds the published threshold for its cue."},
    {"id": "R-HE-03", "stage": "Energy", "summary": "No high-energy cue and no measurement above threshold - treated as low energy."},
    {"id": "R-CTRL-01", "stage": "Barrier", "summary": "Control status comes from the signal in the same sentence as the control; the most degraded direct control governs."},
    {"id": "R-CTRL-02", "stage": "Barrier", "summary": "No direct control mentioned - recorded as ABSENT, never as adequate."},
    {"id": "R-CTRL-03", "stage": "Barrier", "summary": "Direct control named but never verified - PRESENT_UNVERIFIED, which does not protect."},
    {"id": "R-CTRL-04", "stage": "Barrier", "summary": "Only an INDIRECT control was named; it cannot pass the three-part direct control test."},
    {"id": "R-CTRL-05", "stage": "Barrier", "summary": "A control state was signalled without naming the control; the most degraded signal governs."},
    {"id": "R-EFFECT-01", "stage": "Barrier", "summary": "A control protects only if it is DIRECT and PRESENT_VERIFIED."},
    {"id": "R-INJ-01", "stage": "Outcome", "summary": "Injury outcome is the most severe outcome stated in the report."},
    {"id": "R-EVENT-01", "stage": "Outcome", "summary": "Separates an incident (energy was released) from a condition (hazard observed, nothing released)."},
    {"id": "R-INSUF-01", "stage": "Classification", "summary": "No energy source and no control state established - INSUFFICIENT_INFORMATION rather than a guess."},
    {"id": "R-CLASS-01", "stage": "Classification", "summary": "SCL class by table lookup on (high energy, high-energy incident, direct control effective, serious injury)."},
    {"id": "R-LSR-01", "stage": "Life-Saving Rule", "summary": "Primary LSR = the most-cued rule, preferring rules mapped to the energy source."},
    {"id": "R-LSR-02", "stage": "Life-Saving Rule", "summary": "A bypassed control makes Bypassing Safety Controls the governing rule."},
    {"id": "R-LSR-03", "stage": "Life-Saving Rule", "summary": "No rule cued directly - first LSR mapped to the energy source."},
)


def build_ontology() -> dict:
    controls_by_energy: dict[str, list[str]] = {}
    for c in ALL_CONTROLS:
        if c.energy_source is not None and c.control_class is not ControlClass.INDIRECT:
            controls_by_energy.setdefault(c.energy_source.value, []).append(c.key)

    return {
        "version": ENGINE_VERSION,
        "high_energy_threshold_joules": HIGH_ENERGY_THRESHOLD_JOULES,
        "energy_sources": [
            {
                "value": d.source.value,
                "label": d.label,
                "definition": d.definition,
                "trigger_phrases": list(d.trigger_phrases),
                "high_energy_cues": [
                    {"key": c.key, "label": c.label, "basis": c.basis.value}
                    for c in CUES_BY_ENERGY.get(d.source, ())
                ],
                "life_saving_rules": [r.value for r in LSR_BY_ENERGY.get(d.source, ())],
                "direct_controls": controls_by_energy.get(d.source.value, []),
                "citations": [c.key for c in d.citations],
            }
            for d in ENERGY_SOURCES.values()
        ],
        "barrier_states": [
            {
                "value": s.value,
                "protective": s in PROTECTIVE_STATUSES,
                "meaning": CONTROL_STATUS_MEANING[s],
            }
            for s in ControlStatus
        ],
        "direct_control_test": [
            DIRECT_CONTROL_TEST.targets_the_energy_source,
            DIRECT_CONTROL_TEST.mitigates_when_used_properly,
            DIRECT_CONTROL_TEST.survives_unintentional_human_error,
        ],
        "controls": [
            {
                "key": c.key,
                "label": c.label,
                "energy_source": c.energy_source.value if c.energy_source else None,
                "control_class": c.control_class.value,
                "rationale": c.rationale,
                "life_saving_rules": (
                    [r.value for r in LSR_BY_ENERGY.get(c.energy_source, ())]
                    if c.energy_source
                    else []
                ),
            }
            for c in ALL_CONTROLS
        ],
        "life_saving_rules": [
            {
                "value": d.rule.value,
                "short_name": d.short_name,
                "statements": list(d.statements),
                "related_energy_sources": [e.value for e in d.related_energy_sources],
                "trigger_phrases": list(d.trigger_phrases),
                "origin": "IOGP Report 459",
            }
            for d in LIFE_SAVING_RULES.values()
        ],
        "prahari_extensions": [
            {"name": "Secondary Life-Saving Rule", "detail": "IOGP assigns one governing rule per event. prahari also records contributing rules as SECONDARY."},
            {"name": "INSUFFICIENT_INFORMATION class", "detail": "Not an SCL class. Returned when a report is too vague for any honest classification."},
            {"name": "PRESENT_UNVERIFIED barrier state", "detail": "Separates 'mentioned' from 'verified', per limb (b) of the direct control test."},
            {"name": "Indian field vocabulary", "detail": "Trigger phrases drawn from OISD standards and OIL/ONGC field usage, including Hindi/Assamese code-mix."},
        ],
        "classifications": [
            {
                "value": d.classification.value,
                "label": d.label,
                "definition": d.plain_english,
                "precursor": d.classification in SIF_PRECURSOR_CLASSES,
            }
            for d in CLASSIFICATIONS.values()
        ],
        "rules": list(RULE_CATALOGUE),
        "citations": [
            {"key": c.key, "publisher": c.publisher, "title": c.title, "year": c.year, "tier": c.tier.value}
            for c in ALL_CITATIONS
        ],
    }
