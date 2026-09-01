"""The demo runbook, as a test.

DEMO.md tells a presenter exactly what will appear on screen, sentence by
sentence. That makes its claims load-bearing: a lexicon tweak that quietly
turns Step 2 from `psif` into `exposure` would not fail anything else in the
suite, and would be discovered on stage.

So the three reports and their expected verdicts are pinned here. If one of
these fails, DEMO.md is wrong and must be updated before presenting.
"""

from __future__ import annotations

import pytest

from prahari.rules.engine import analyse

# -- verbatim from DEMO.md and the Live Analysis dropdown -------------------

STEP_1_LOW_ENERGY_INJURY = (
    "On 03.07.2026, Sri R. Das (fitter) was cutting GI sheet at the workshop, "
    "Duliajan. Hand gloves were not worn while doing the job. The blade slipped "
    "and he sustained a cut on the left index finger. First aid was given at the "
    "installation and he resumed duty."
)

STEP_2_UNCONTROLLED_ENERGY = (
    "On 28.08.2026 at abt 1115 hrs, Sri B. Gogoi (fitter) was attending the belt "
    "of the pumping unit at Well No. 214, Moran. The machine guard was missing "
    "from the drive and the unit was not isolated at the panel. The belt started "
    "on auto while he was still inside the guard area. There was no injury to any "
    "personnel. Job stopped and area barricaded."
)

STEP_3_CODE_MIXED = (
    "Rig no 33 Duliajan t kaam kori asil, casing lowering job cholise. Load "
    "approx 2500 kg abut 4 mtr height t thakil. Sling ka condition kharab tha aur "
    "koi secondary retention nahi tha. हठात् the sling parted and the load dropped "
    "from abt 4 mtr. কোনো আঘাত হোৱা নাই. supervisor k koisilo, kaam bondho kora hol."
)


def test_step_1_visible_injury_is_not_a_sif() -> None:
    """The setup: a real injury that the system deliberately ranks low."""
    _, verdict = analyse(STEP_1_LOW_ENERGY_INJURY)
    assert verdict.classification.value == "low_severity"
    assert verdict.high_energy is False
    assert verdict.injury_outcome.value in ("minor_injury", "first_aid")


def test_step_2_nobody_hurt_is_a_precursor() -> None:
    """The payoff. If this regresses, the demo has no argument left."""
    facts, verdict = analyse(STEP_2_UNCONTROLLED_ENERGY)
    assert verdict.classification.value == "psif"
    assert verdict.energy_source is not None
    assert verdict.energy_source.value == "mechanical"
    assert verdict.high_energy is True
    assert verdict.control_status.value == "absent"
    assert verdict.direct_control_key == "machine_guarding"
    assert verdict.primary_lsr is not None
    assert verdict.primary_lsr.value == "energy_isolation"
    assert verdict.injury_outcome.value == "none", "the point is that nobody was hurt"


def test_step_2_is_visibly_traceable_on_screen() -> None:
    """DEMO.md points at the highlights and the rule trace. Both must exist."""
    _, verdict = analyse(STEP_2_UNCONTROLLED_ENERGY)
    assert len(verdict.fired_rules) >= 6
    assert any(f.rule_id == "R-CLASS-01" for f in verdict.fired_rules)
    assert any(f.rule_id.startswith("R-CTRL") for f in verdict.fired_rules)
    assert len(verdict.all_spans) >= 10, "too few highlights to point at"


def test_step_2_and_step_3_agree_on_the_barrier() -> None:
    """Step 3's headline is 'machine guarding, absent'. Step 2 must name it."""
    _, verdict = analyse(STEP_2_UNCONTROLLED_ENERGY)
    from prahari.domain.controls import CONTROLS_BY_KEY

    control = CONTROLS_BY_KEY[verdict.direct_control_key or ""]
    assert control.label == "Fixed machine guarding"
    assert control.is_direct, "the demo's barrier must be a DIRECT control"


def test_code_mixed_report_still_classifies() -> None:
    """Devanagari and Assamese mid-sentence must not break extraction."""
    _, verdict = analyse(STEP_3_CODE_MIXED)
    assert verdict.classification.value in ("psif", "exposure", "hsif")
    assert verdict.energy_source is not None
    assert verdict.primary_lsr is not None


@pytest.mark.parametrize(
    "text", [STEP_1_LOW_ENERGY_INJURY, STEP_2_UNCONTROLLED_ENERGY, STEP_3_CODE_MIXED]
)
def test_every_demo_span_indexes_its_own_text(text: str) -> None:
    """A highlight that points at the wrong characters is worse than none."""
    facts, verdict = analyse(text)
    for span in verdict.all_spans:
        assert 0 <= span.start < span.end <= len(text)
        assert text[span.start : span.end].strip()


def test_the_demo_ordering_makes_its_point() -> None:
    """Step 1 must rank BELOW Step 2, or the whole narrative inverts."""
    from prahari.api.service import triage_rank

    _, low = analyse(STEP_1_LOW_ENERGY_INJURY)
    _, precursor = analyse(STEP_2_UNCONTROLLED_ENERGY)
    assert triage_rank(precursor) > triage_rank(low), (
        "the bleeding finger outranked the uncontrolled machine — "
        "that is the exact inversion this product exists to fix"
    )
