"""Internal-consistency tests for the safety-science taxonomy.

These are not tests of detection quality - there is no detection yet. They are
structural guards: if someone adds an energy type, a cue, a control or a rule
and forgets to wire it up, these fail loudly rather than letting a silently
incomplete taxonomy reach the rule engine.
"""

from __future__ import annotations

import pytest

from prahari.domain import (
    ALL_CITATIONS,
    ALL_CONTROLS,
    CUES_BY_ENERGY,
    DIRECT_CONTROLS,
    DIRECT_CONTROLS_BY_ENERGY,
    ENERGY_SOURCES,
    HIGH_ENERGY_CUES,
    HIGH_ENERGY_THRESHOLD_JOULES,
    INDIRECT_CONTROLS,
    LIFE_SAVING_RULES,
    LSR_BY_ENERGY,
    ControlClass,
    CueBasis,
    EnergySource,
    LifeSavingRule,
    SourceTier,
)


# --------------------------------------------------------------------------
# Energy Wheel completeness
# --------------------------------------------------------------------------


def test_energy_wheel_has_exactly_ten_categories() -> None:
    """The EEI SCL Model energy wheel has ten categories, no more, no fewer."""
    assert len(EnergySource) == 10
    assert len(ENERGY_SOURCES) == 10


def test_every_energy_source_enum_member_has_a_definition() -> None:
    for source in EnergySource:
        assert source in ENERGY_SOURCES, f"{source} has no EnergySourceDefinition"


def test_energy_definition_keys_match_their_enum_member() -> None:
    for source, definition in ENERGY_SOURCES.items():
        assert definition.source is source


@pytest.mark.parametrize("source", list(EnergySource))
def test_every_energy_source_has_trigger_phrases(source: EnergySource) -> None:
    """No energy type may ship with an empty cue list - it would be invisible."""
    phrases = ENERGY_SOURCES[source].trigger_phrases
    assert len(phrases) >= 15, f"{source.value} has only {len(phrases)} trigger phrases"


@pytest.mark.parametrize("source", list(EnergySource))
def test_energy_source_has_label_and_definition(source: EnergySource) -> None:
    definition = ENERGY_SOURCES[source]
    assert definition.label.strip()
    assert len(definition.definition.strip()) > 40


@pytest.mark.parametrize("source", list(EnergySource))
def test_trigger_phrases_are_lowercase_and_unique(source: EnergySource) -> None:
    phrases = ENERGY_SOURCES[source].trigger_phrases
    assert all(p == p.lower() for p in phrases), f"{source.value} has non-lowercase phrases"
    assert all(p.strip() == p for p in phrases), f"{source.value} has untrimmed phrases"
    assert len(set(phrases)) == len(phrases), f"{source.value} has duplicate phrases"


@pytest.mark.parametrize("source", list(EnergySource))
def test_every_energy_source_is_cited(source: EnergySource) -> None:
    assert ENERGY_SOURCES[source].citations, f"{source.value} has no citation"


# --------------------------------------------------------------------------
# High-energy threshold and cues
# --------------------------------------------------------------------------


def test_high_energy_threshold_is_1500_joules() -> None:
    """The number from the primary source. Changing it changes every verdict."""
    assert HIGH_ENERGY_THRESHOLD_JOULES == 1500


@pytest.mark.parametrize("source", list(EnergySource))
def test_every_energy_source_has_at_least_one_high_energy_cue(
    source: EnergySource,
) -> None:
    assert CUES_BY_ENERGY[source], f"{source.value} has no high-energy cue"


def test_cue_keys_are_unique() -> None:
    keys = [c.key for c in HIGH_ENERGY_CUES]
    assert len(set(keys)) == len(keys)


@pytest.mark.parametrize("cue", HIGH_ENERGY_CUES, ids=lambda c: c.key)
def test_every_cue_has_phrases_rationale_and_citation(cue) -> None:
    assert cue.phrases, f"{cue.key} has no phrases"
    assert len(cue.rationale.strip()) > 40, f"{cue.key} has a thin rationale"
    assert cue.citations, f"{cue.key} has no citation"


@pytest.mark.parametrize("cue", HIGH_ENERGY_CUES, ids=lambda c: c.key)
def test_measured_cues_carry_a_number_and_a_unit(cue) -> None:
    """A MEASURED_MAGNITUDE cue without a number is a category error."""
    if cue.basis is CueBasis.MEASURED_MAGNITUDE and cue.threshold_value is not None:
        assert cue.threshold_unit, f"{cue.key} has a value but no unit"


@pytest.mark.parametrize("cue", HIGH_ENERGY_CUES, ids=lambda c: c.key)
def test_categorical_cues_carry_no_spurious_number(cue) -> None:
    if cue.basis is CueBasis.CATEGORICAL:
        assert cue.threshold_value is None, f"{cue.key} is categorical but has a magnitude"


def test_key_published_magnitudes_match_the_literature() -> None:
    """Guards the specific numbers a safety professional will check."""
    from prahari.domain.high_energy import CUES_BY_KEY

    assert CUES_BY_KEY["voltage_at_or_above_50v"].threshold_value == 50.0
    assert CUES_BY_KEY["temperature_at_or_above_65c"].threshold_value == 65.0
    assert CUES_BY_KEY["excavation_depth"].threshold_value == 1.5
    assert CUES_BY_KEY["motor_vehicle_speed"].threshold_value == 48.0
    assert CUES_BY_KEY["fall_from_elevation"].threshold_value == 1.2
    assert CUES_BY_KEY["fall_above_1p8m"].threshold_value == 1.8


# --------------------------------------------------------------------------
# Controls
# --------------------------------------------------------------------------


@pytest.mark.parametrize("source", list(EnergySource))
def test_every_energy_source_has_at_least_one_direct_control(
    source: EnergySource,
) -> None:
    assert DIRECT_CONTROLS_BY_ENERGY[source], f"{source.value} has no direct control"


def test_control_keys_are_unique_across_direct_and_indirect() -> None:
    keys = [c.key for c in ALL_CONTROLS]
    assert len(set(keys)) == len(keys)


def test_direct_controls_are_classified_direct() -> None:
    for control in DIRECT_CONTROLS:
        assert control.is_direct, f"{control.key} is in DIRECT_CONTROLS but not classed direct"
        assert control.energy_source is not None, f"{control.key} must target an energy source"


def test_indirect_controls_are_classified_indirect() -> None:
    """The core design guard: nothing in the indirect list may leak into direct."""
    for control in INDIRECT_CONTROLS:
        assert control.control_class is ControlClass.INDIRECT
        assert not control.is_direct, f"{control.key} must never count as a direct control"


def test_the_named_indirect_controls_are_present_and_indirect() -> None:
    """Training, signage, permits, supervision and general PPE must be indirect.

    This is the single most abusable place in the model. If one of these ever
    becomes a direct control, the engine will start clearing genuinely
    uncontrolled high-energy work.
    """
    from prahari.domain.controls import CONTROLS_BY_KEY

    must_be_indirect = (
        "training",
        "toolbox_talk",
        "signage",
        "permit_paperwork_alone",
        "supervision",
        "spotter",
        "exclusion_zone_soft",
        "procedure_alone",
        "general_ppe",
        "experience_and_care",
    )
    for key in must_be_indirect:
        assert key in CONTROLS_BY_KEY, f"{key} missing from the control inventory"
        assert CONTROLS_BY_KEY[key].control_class is ControlClass.INDIRECT


@pytest.mark.parametrize("control", ALL_CONTROLS, ids=lambda c: c.key)
def test_every_control_has_rationale_phrases_and_citation(control) -> None:
    assert len(control.rationale.strip()) > 30, f"{control.key} has a thin rationale"
    assert control.phrases, f"{control.key} has no phrases"
    assert control.citations, f"{control.key} has no citation"


def test_control_status_covers_the_seven_required_states() -> None:
    from prahari.domain.controls import ControlStatus

    expected = {
        "PRESENT_VERIFIED",
        "PRESENT_UNVERIFIED",
        "ABSENT",
        "FAILED",
        "BYPASSED",
        "NOT_FOLLOWED",
        "UNKNOWN",
    }
    assert {s.name for s in ControlStatus} == expected


def test_verified_presence_is_the_only_protective_status() -> None:
    """Everything except PRESENT_VERIFIED must be treated as not-protective.

    PRESENT_UNVERIFIED is deliberately in the non-protective set, because limb
    (b) of the direct control test requires the control to be "installed,
    VERIFIED, and used properly". An unverified isolation is exactly the SIF
    precursor this system exists to find.
    """
    from prahari.domain.controls import (
        NON_PROTECTIVE_STATUSES,
        PROTECTIVE_STATUSES,
        ControlStatus,
    )

    assert ControlStatus.PRESENT_VERIFIED not in NON_PROTECTIVE_STATUSES
    assert ControlStatus.PRESENT_UNVERIFIED in NON_PROTECTIVE_STATUSES
    assert len(NON_PROTECTIVE_STATUSES) == 6
    assert PROTECTIVE_STATUSES == {ControlStatus.PRESENT_VERIFIED}
    assert not (PROTECTIVE_STATUSES & NON_PROTECTIVE_STATUSES)
    assert len(PROTECTIVE_STATUSES | NON_PROTECTIVE_STATUSES) == len(ControlStatus)


def test_direct_control_test_states_all_three_limbs() -> None:
    from prahari.domain.controls import DIRECT_CONTROL_TEST

    assert DIRECT_CONTROL_TEST.targets_the_energy_source
    assert DIRECT_CONTROL_TEST.mitigates_when_used_properly
    assert DIRECT_CONTROL_TEST.survives_unintentional_human_error
    assert DIRECT_CONTROL_TEST.citation.key == "EEI_HECA"


# --------------------------------------------------------------------------
# Life-Saving Rules
# --------------------------------------------------------------------------


def test_there_are_exactly_nine_life_saving_rules() -> None:
    assert len(LifeSavingRule) == 9
    assert len(LIFE_SAVING_RULES) == 9


def test_the_nine_rules_are_the_iogp_nine() -> None:
    assert {r.name for r in LifeSavingRule} == {
        "BYPASSING_SAFETY_CONTROLS",
        "CONFINED_SPACE",
        "DRIVING",
        "ENERGY_ISOLATION",
        "HOT_WORK",
        "LINE_OF_FIRE",
        "SAFE_MECHANICAL_LIFTING",
        "WORK_AUTHORISATION",
        "WORKING_AT_HEIGHT",
    }


@pytest.mark.parametrize("rule", list(LifeSavingRule))
def test_every_rule_has_short_name_statements_and_phrases(rule: LifeSavingRule) -> None:
    definition = LIFE_SAVING_RULES[rule]
    assert definition.short_name.strip()
    assert definition.statements, f"{rule.value} has no 'I' statements"
    assert all(s.strip().startswith(("I ", "Before ")) for s in definition.statements), (
        f"{rule.value} statements should be IOGP first-person wording"
    )
    assert len(definition.trigger_phrases) >= 10
    assert definition.citations


@pytest.mark.parametrize("source", list(EnergySource))
def test_every_energy_source_maps_to_at_least_one_life_saving_rule(
    source: EnergySource,
) -> None:
    """The requirement that ties the two taxonomies together."""
    assert LSR_BY_ENERGY[source], f"{source.value} maps to no Life-Saving Rule"


def test_every_life_saving_rule_is_reachable_from_some_energy_source() -> None:
    """No orphan rules: each of the nine must be reachable from the wheel."""
    reachable = {rule for rules in LSR_BY_ENERGY.values() for rule in rules}
    missing = set(LifeSavingRule) - reachable
    assert not missing, f"unreachable Life-Saving Rules: {sorted(r.value for r in missing)}"


def test_rule_assignment_supports_primary_and_secondary() -> None:
    from prahari.domain.lsr import RuleAssignmentRank

    assert {r.name for r in RuleAssignmentRank} == {"PRIMARY", "SECONDARY"}


def test_rule_related_energy_sources_are_valid_members() -> None:
    for rule, definition in LIFE_SAVING_RULES.items():
        assert definition.related_energy_sources, f"{rule.value} maps to no energy source"
        for source in definition.related_energy_sources:
            assert isinstance(source, EnergySource)


# --------------------------------------------------------------------------
# Citations
# --------------------------------------------------------------------------


def test_citation_keys_are_unique() -> None:
    keys = [c.key for c in ALL_CITATIONS]
    assert len(set(keys)) == len(keys)


def test_external_citations_carry_a_publisher_and_title() -> None:
    for citation in ALL_CITATIONS:
        assert citation.publisher.strip()
        assert citation.title.strip()
        if citation.tier is not SourceTier.PRAHARI_CHOICE:
            assert citation.url, f"{citation.key} is an external source with no URL"


def test_prahari_modelling_choices_are_distinguishable_from_real_sources() -> None:
    """Anything we invented must be visibly tagged, never dressed as literature."""
    from prahari.domain.citations import PRAHARI_MODELLING

    assert PRAHARI_MODELLING.tier is SourceTier.PRAHARI_CHOICE
    externals = [c for c in ALL_CITATIONS if c.tier is not SourceTier.PRAHARI_CHOICE]
    assert len(externals) >= 10


# --------------------------------------------------------------------------
# The design principle itself
# --------------------------------------------------------------------------


def test_domain_model_exposes_no_severity_score() -> None:
    """CLAUDE.md: no model, and no part of this package, emits a severity score.

    The domain layer must not even provide a place to put one.
    """
    import prahari.domain as domain

    banned = ("severity", "score", "risk_level", "probability", "confidence")
    exported = [name.lower() for name in domain.__all__]
    offenders = [n for n in exported if any(b in n for b in banned)]
    assert not offenders, f"domain must not expose a severity/score concept: {offenders}"
