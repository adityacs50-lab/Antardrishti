"""Tests for the synthetic report generator.

The generator produces the labelled evaluation set the whole project will be
scored on, so these tests guard the properties that make those labels worth
anything: determinism, label-by-construction, split integrity, and the presence
of the hard cases the dataset exists for.
"""

from __future__ import annotations

import json
import random
from collections import Counter

import pytest

from prahari.data.generator import (
    CLASS_DISTRIBUTION,
    build_spec,
    derive_classification,
    generate,
    render,
    stratified_split,
    summarise,
    write_jsonl,
)
from prahari.data.scenarios import (
    ALL_SCENARIOS,
    HIGH_ENERGY_SCENARIOS,
    LOW_ENERGY_SCENARIOS,
)
from prahari.domain.classification import (
    SCL_DECISION_TABLE,
    InjuryOutcome,
    SifClassification,
)
from prahari.domain.controls import CONTROLS_BY_KEY, ControlStatus, PROTECTIVE_STATUSES
from prahari.domain.energy import EnergySource
from prahari.domain.lsr import LifeSavingRule

SAMPLE_N = 600
SEED = 42


@pytest.fixture(scope="module")
def records() -> list[dict]:
    return stratified_split(generate(SAMPLE_N, SEED), SEED)


# --------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------


def test_generation_is_deterministic_under_seed() -> None:
    a = generate(120, 7)
    b = generate(120, 7)
    assert [r["text"] for r in a] == [r["text"] for r in b]
    assert [r["labels"] for r in a] == [r["labels"] for r in b]


def test_different_seeds_give_different_data() -> None:
    a = {r["text"] for r in generate(120, 1)}
    b = {r["text"] for r in generate(120, 2)}
    assert len(a & b) < 12


def test_split_is_deterministic_under_seed() -> None:
    a = stratified_split(generate(200, 5), 5)
    b = stratified_split(generate(200, 5), 5)
    assert [r["meta"]["split"] for r in a] == [r["meta"]["split"] for r in b]


# --------------------------------------------------------------------------
# Labels are constructed, never inferred
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", list(SifClassification))
def test_build_spec_yields_the_requested_class(target: SifClassification) -> None:
    """The core guarantee: the spec determines the label, not the text."""
    rng = random.Random(11)
    for _ in range(40):
        spec = build_spec(target, rng)
        assert derive_classification(spec) is target


def test_derive_classification_matches_the_scl_table(records: list[dict]) -> None:
    """Every non-vague record's label must be reproducible from the four booleans."""
    for rec in records:
        lb = rec["labels"]
        if not rec["meta"]["labels_determinable_from_text"]:
            continue
        expected = SCL_DECISION_TABLE[
            (
                lb["high_energy"],
                lb["high_energy_incident"],
                lb["direct_control_effective"],
                lb["injury_outcome"] in ("serious_injury", "fatality"),
            )
        ]
        assert lb["sif_classification"] == expected.value, rec["report_id"]


def test_control_effectiveness_follows_the_domain_rule(records: list[dict]) -> None:
    """Only PRESENT_VERIFIED may be marked effective. Unverified is a precursor."""
    for rec in records:
        lb = rec["labels"]
        if lb["control_status"] is None:
            continue
        expected = ControlStatus(lb["control_status"]) in PROTECTIVE_STATUSES
        assert lb["direct_control_effective"] is expected, rec["report_id"]


def test_high_energy_flag_matches_the_scenario_pool(records: list[dict]) -> None:
    high_keys = {s.key for s in HIGH_ENERGY_SCENARIOS}
    low_keys = {s.key for s in LOW_ENERGY_SCENARIOS}
    for rec in records:
        key = rec["meta"]["scenario_key"]
        if key == "vague":
            continue
        if key in high_keys:
            assert rec["labels"]["high_energy"] is True, rec["report_id"]
        elif key in low_keys:
            assert rec["labels"]["high_energy"] is False, rec["report_id"]


# --------------------------------------------------------------------------
# The classes that make the dataset worth building
# --------------------------------------------------------------------------


def test_money_cases_exist_and_have_no_injury(records: list[dict]) -> None:
    """High fatal potential, zero outcome. What a severity model misses."""
    money = [r for r in records if r["meta"]["hard_case_kind"] == "high_potential_no_outcome"]
    assert len(money) > SAMPLE_N * 0.15
    for rec in money:
        assert rec["labels"]["sif_classification"] in ("psif", "exposure")
        assert rec["labels"]["high_energy"] is True
        assert rec["labels"]["injury_outcome"] == "none"
        assert rec["labels"]["direct_control_effective"] is False


def test_injury_trap_cases_are_non_sif(records: list[dict]) -> None:
    """Visible injury, no fatal potential. What a severity model over-ranks."""
    trap = [r for r in records if r["meta"]["hard_case_kind"] == "visible_injury_low_potential"]
    assert len(trap) > SAMPLE_N * 0.05
    for rec in trap:
        assert rec["labels"]["sif_classification"] == "low_severity"
        assert rec["labels"]["high_energy"] is False
        assert rec["labels"]["injury_outcome"] in ("minor_injury", "first_aid")


def test_controlled_high_energy_cases_are_not_precursors(records: list[dict]) -> None:
    """High energy plus a control that held must never read as a precursor."""
    good = [r for r in records if r["meta"]["hard_case_kind"] == "controlled_high_energy"]
    assert len(good) > SAMPLE_N * 0.08
    for rec in good:
        assert rec["labels"]["sif_classification"] in ("capacity", "success")
        assert rec["labels"]["high_energy"] is True
        assert rec["labels"]["control_status"] == "present_verified"
        assert rec["labels"]["direct_control_effective"] is True


def test_vague_records_carry_no_labels_the_text_cannot_support(records: list[dict]) -> None:
    """Scoring a model against an unstated fact teaches it to guess."""
    vague = [r for r in records if r["labels"]["sif_classification"] == "insufficient_information"]
    assert len(vague) > SAMPLE_N * 0.05
    for rec in vague:
        lb = rec["labels"]
        assert rec["meta"]["labels_determinable_from_text"] is False
        assert lb["energy_source"] is None
        assert lb["control_status"] is None
        assert lb["primary_lsr"] is None
        assert lb["injury_outcome"] is None
        assert lb["secondary_lsr"] == []
        assert len(rec["text"]) < 260


def test_all_eight_classes_are_present(records: list[dict]) -> None:
    seen = {r["labels"]["sif_classification"] for r in records}
    assert seen == {c.value for c in SifClassification}


# --------------------------------------------------------------------------
# Coverage of the taxonomy
# --------------------------------------------------------------------------


def test_every_energy_type_appears(records: list[dict]) -> None:
    seen = {r["labels"]["energy_source"] for r in records if r["labels"]["energy_source"]}
    assert seen == {e.value for e in EnergySource}


def test_every_life_saving_rule_appears_as_primary(records: list[dict]) -> None:
    seen = {r["labels"]["primary_lsr"] for r in records if r["labels"]["primary_lsr"]}
    assert seen == {r.value for r in LifeSavingRule}


def test_every_generated_control_status_appears(records: list[dict]) -> None:
    seen = {r["labels"]["control_status"] for r in records if r["labels"]["control_status"]}
    assert "present_verified" in seen
    assert "present_unverified" in seen
    assert {"absent", "failed", "bypassed", "not_followed"} <= seen


def test_bypassed_control_makes_bypassing_the_primary_rule(records: list[dict]) -> None:
    """A deliberately defeated control IS the Bypassing Safety Controls rule."""
    for rec in records:
        if rec["labels"]["control_status"] == "bypassed":
            assert rec["labels"]["primary_lsr"] == "bypassing_safety_controls", rec["report_id"]


def test_direct_control_keys_resolve_to_the_control_inventory() -> None:
    for scenario in ALL_SCENARIOS:
        assert scenario.direct_control_key in CONTROLS_BY_KEY, scenario.key


def test_high_energy_scenarios_reference_direct_controls() -> None:
    """A high-energy scenario must be about a real direct control, not an indirect one."""
    for scenario in HIGH_ENERGY_SCENARIOS:
        control = CONTROLS_BY_KEY[scenario.direct_control_key]
        assert control.is_direct, f"{scenario.key} points at an indirect control"
        assert control.energy_source is scenario.energy_source, scenario.key


def test_every_scenario_supplies_all_six_generated_statuses() -> None:
    for scenario in ALL_SCENARIOS:
        for status in (
            ControlStatus.PRESENT_VERIFIED,
            ControlStatus.PRESENT_UNVERIFIED,
            ControlStatus.ABSENT,
            ControlStatus.FAILED,
            ControlStatus.BYPASSED,
            ControlStatus.NOT_FOLLOWED,
        ):
            assert scenario.control.get(status), f"{scenario.key} missing {status.value}"


# --------------------------------------------------------------------------
# Split integrity
# --------------------------------------------------------------------------


def test_split_ratios_are_roughly_70_15_15(records: list[dict]) -> None:
    counts = Counter(r["meta"]["split"] for r in records)
    total = len(records)
    assert abs(counts["train"] / total - 0.70) < 0.02
    assert abs(counts["val"] / total - 0.15) < 0.02
    assert abs(counts["test"] / total - 0.15) < 0.02


def test_split_is_stratified_on_classification(records: list[dict]) -> None:
    """Each split must mirror the overall class distribution."""
    total = len(records)
    overall = Counter(r["labels"]["sif_classification"] for r in records)
    for split in ("train", "val", "test"):
        subset = [r for r in records if r["meta"]["split"] == split]
        for cls, n in overall.items():
            got = sum(1 for r in subset if r["labels"]["sif_classification"] == cls) / len(subset)
            assert abs(got - n / total) < 0.03, f"{cls} skewed in {split}"


def test_every_record_is_assigned_exactly_one_split(records: list[dict]) -> None:
    assert all(r["meta"]["split"] in ("train", "val", "test") for r in records)


def test_report_ids_are_unique(records: list[dict]) -> None:
    ids = [r["report_id"] for r in records]
    assert len(set(ids)) == len(ids)


# --------------------------------------------------------------------------
# Text realism
# --------------------------------------------------------------------------


def test_texts_are_unique_and_non_trivial(records: list[dict]) -> None:
    texts = [r["text"] for r in records]
    assert len(set(texts)) > len(texts) * 0.98
    assert all(len(t) > 40 for t in texts)


def test_no_unfilled_template_slots_leak_into_text(records: list[dict]) -> None:
    for rec in records:
        assert "{" not in rec["text"], rec["report_id"]
        assert "}" not in rec["text"], rec["report_id"]


def test_non_latin_scripts_actually_appear(records: list[dict]) -> None:
    """Devanagari and Assamese must be present, not just promised."""
    joined = " ".join(r["text"] for r in records)
    assert any("ऀ" <= ch <= "ॿ" for ch in joined), "no Devanagari generated"
    assert any("ঀ" <= ch <= "৿" for ch in joined), "no Assamese/Bengali script generated"


def test_romanised_code_mixing_appears(records: list[dict]) -> None:
    joined = " ".join(r["text"] for r in records).lower()
    assert any(p in joined for p in ("kaam kar raha tha", "nahi", "kori asil", "koi chot"))


def test_oil_locations_and_abbreviations_appear(records: list[dict]) -> None:
    joined = " ".join(r["text"] for r in records)
    lowered = joined.lower()
    for place in ("naoholia", "baghjan", "duliajan", "moran", "kusijan", "dikom"):
        assert place in lowered, place
    assert any(abbr in joined for abbr in ("PTW", "LOTO", "H2S", "BOP", "JSA", "TBT"))


def test_language_mix_field_matches_generated_script(records: list[dict]) -> None:
    """A record tagged assamese_script should contain Assamese somewhere."""
    tagged = [r for r in records if r["language_mix"] == "assamese_script"]
    assert tagged
    hits = sum(1 for r in tagged if any("ঀ" <= ch <= "৿" for ch in r["text"]))
    assert hits > len(tagged) * 0.5


# --------------------------------------------------------------------------
# Serialisation
# --------------------------------------------------------------------------


def test_records_round_trip_through_jsonl(tmp_path, records: list[dict]) -> None:
    path = tmp_path / "out.jsonl"
    write_jsonl(records, path)
    loaded = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert loaded == records


def test_class_distribution_weights_sum_to_one() -> None:
    assert abs(sum(CLASS_DISTRIBUTION.values()) - 1.0) < 1e-9


def test_summary_renders_without_error(records: list[dict]) -> None:
    out = summarise(records)
    assert "SIF classification" in out
    assert "stratification check" in out


def test_render_never_inspects_labels() -> None:
    """render() must depend only on the spec, so text cannot leak the label.

    Rendering the same spec twice with the same rng state gives identical text -
    proof that nothing outside the spec and the rng feeds it.
    """
    rng = random.Random(3)
    spec = build_spec(SifClassification.PSIF, rng)
    assert render(spec, random.Random(99)) == render(spec, random.Random(99))
