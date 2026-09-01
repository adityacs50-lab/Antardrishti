"""The nine IOGP Life-Saving Rules.

Source: IOGP Report 459, Life-Saving Rules (2018). The nine simplified rules
replaced the earlier eighteen, and were derived by analysing 405 personal-
safety fatalities reported to IOGP between 2008 and 2017 and asking which rule
would have prevented or mitigated each fatal outcome.

The rules are written as first-person "I" statements from the worker's
perspective. That wording is reproduced here because it is what a field crew
in an Indian operating company will actually have seen on a rig-site board,
and quoting it back in a verdict is what makes the verdict recognisable to
them.

On PRIMARY vs SECONDARY - read this before defending it
-------------------------------------------------------
IOGP Report 459's published methodology maps each fatality to the rule that
would have prevented or mitigated it, which is a single, primary assignment.
IOGP does not publish a two-tier primary/secondary scheme. prahari adds
SECONDARY as its own extension, to record contributing rules where a report
plainly engages more than one, and it is tagged as a prahari modelling
decision so nobody claims IOGP authority for it in a pitch or a viva.

Pure data and types. No classification logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from prahari.domain.citations import IOGP_459, Citation, PRAHARI_MODELLING
from prahari.domain.energy import EnergySource


class LifeSavingRule(str, Enum):
    """The nine IOGP Life-Saving Rules (Report 459, 2018)."""

    BYPASSING_SAFETY_CONTROLS = "bypassing_safety_controls"
    CONFINED_SPACE = "confined_space"
    DRIVING = "driving"
    ENERGY_ISOLATION = "energy_isolation"
    HOT_WORK = "hot_work"
    LINE_OF_FIRE = "line_of_fire"
    SAFE_MECHANICAL_LIFTING = "safe_mechanical_lifting"
    WORK_AUTHORISATION = "work_authorisation"
    WORKING_AT_HEIGHT = "working_at_height"


class RuleAssignmentRank(str, Enum):
    """Whether a rule is the governing one for a report or a contributing one.

    PRIMARY   - the rule that, followed, would have prevented or mitigated the
                outcome. This mirrors IOGP Report 459's own methodology.
    SECONDARY - a contributing rule also engaged by the report. A prahari
                extension, not an IOGP construct.
    """

    PRIMARY = "primary"
    SECONDARY = "secondary"


@dataclass(frozen=True, slots=True)
class LifeSavingRuleDefinition:
    """One Life-Saving Rule, with its official wording and lexical cues."""

    rule: LifeSavingRule
    short_name: str
    statements: tuple[str, ...]
    related_energy_sources: tuple[EnergySource, ...]
    trigger_phrases: tuple[str, ...]
    citations: tuple[Citation, ...] = field(default=(IOGP_459,))


BYPASSING_SAFETY_CONTROLS = LifeSavingRuleDefinition(
    rule=LifeSavingRule.BYPASSING_SAFETY_CONTROLS,
    short_name="Obtain authorisation before overriding or disabling safety controls",
    statements=(
        "I understand and use safety-critical equipment and procedures which apply to my task",
        "I obtain authorisation before disabling or overriding safety equipment",
        "I obtain authorisation before deviating from procedures",
        "I obtain authorisation before crossing a barrier",
    ),
    related_energy_sources=(
        EnergySource.MECHANICAL,
        EnergySource.ELECTRICAL,
        EnergySource.PRESSURE,
        EnergySource.RADIATION,
        EnergySource.SOUND,
    ),
    trigger_phrases=(
        "bypassed",
        "overridden",
        "override",
        "disabled the alarm",
        "inhibited",
        "defeated the interlock",
        "jumper",
        "forced the switch",
        "guard removed",
        "crossed the barricade",
        "deviated from procedure",
        "shortcut",
        "car sealed open",
        "trip bypassed",
    ),
)

CONFINED_SPACE = LifeSavingRuleDefinition(
    rule=LifeSavingRule.CONFINED_SPACE,
    short_name="Obtain authorisation before entering a confined space",
    statements=(
        "I confirm energy sources are isolated",
        "I confirm the atmosphere has been tested and is monitored",
        "I check and use my breathing apparatus when required",
        "I confirm there is an attendant standing by",
        "I confirm a rescue plan is in place",
        "I obtain authorisation to enter",
    ),
    related_energy_sources=(EnergySource.CHEMICAL, EnergySource.BIOLOGICAL),
    trigger_phrases=(
        "confined space",
        "entered the tank",
        "vessel entry",
        "mud tank",
        "storage tank",
        "sump",
        "pit entry",
        "manhole",
        "attendant",
        "hole watch",
        "rescue plan",
        "atmosphere tested",
        "gas test before entry",
        "oxygen level",
    ),
)

DRIVING = LifeSavingRuleDefinition(
    rule=LifeSavingRule.DRIVING,
    short_name="Follow safe driving rules",
    statements=(
        "I always wear a seatbelt",
        "I do not exceed the speed limit, and reduce my speed for road conditions",
        "I do not use phones or operate devices while driving",
        "I am fit, rested and fully alert while driving",
        "I follow journey management",
    ),
    related_energy_sources=(EnergySource.MOTION,),
    trigger_phrases=(
        "driving",
        "driver",
        "vehicle",
        "seat belt",
        "seatbelt",
        "over speeding",
        "speed limit",
        "journey management",
        "road traffic accident",
        "rta",
        "ivms",
        "fatigue",
        "night driving",
        "mobile phone while driving",
        "crew bus",
        "light vehicle",
    ),
)

ENERGY_ISOLATION = LifeSavingRuleDefinition(
    rule=LifeSavingRule.ENERGY_ISOLATION,
    short_name="Verify isolation and zero energy before work begins",
    statements=(
        "I have identified all energy sources",
        "I confirm that hazardous energy sources have been isolated, locked, and tagged",
        "I have checked there is zero energy and tested for residual or stored energy",
    ),
    related_energy_sources=(
        EnergySource.ELECTRICAL,
        EnergySource.MECHANICAL,
        EnergySource.PRESSURE,
        EnergySource.CHEMICAL,
        EnergySource.TEMPERATURE,
    ),
    trigger_phrases=(
        "isolation",
        "isolated",
        "loto",
        "lock out tag out",
        "locked and tagged",
        "zero energy",
        "residual energy",
        "stored energy",
        "trapped pressure",
        "de-energised",
        "de-energized",
        "blind fitted",
        "spade fitted",
        "double block and bleed",
        "tested dead",
        "not isolated",
    ),
)

HOT_WORK = LifeSavingRuleDefinition(
    rule=LifeSavingRule.HOT_WORK,
    short_name="Control flammables and ignition sources",
    statements=(
        "I identify and control ignition sources",
        "Before starting any hot work I confirm flammable material has been removed or isolated",
        "Before starting any hot work I obtain authorisation",
        "Before starting hot work in a hazardous area I confirm a gas test has been completed",
        "Before starting hot work in a hazardous area I confirm gas will be monitored continually",
    ),
    related_energy_sources=(EnergySource.TEMPERATURE, EnergySource.CHEMICAL),
    trigger_phrases=(
        "hot work",
        "welding",
        "gas cutting",
        "grinding",
        "cutting torch",
        "spark",
        "ignition source",
        "flammable",
        "gas test",
        "hot work permit",
        "fire watch",
        "combustibles",
        "purging",
        "hot tapping",
    ),
)

LINE_OF_FIRE = LifeSavingRuleDefinition(
    rule=LifeSavingRule.LINE_OF_FIRE,
    short_name="Keep yourself and others out of the line of fire",
    statements=(
        "I position myself to avoid moving objects",
        "I position myself to avoid vehicles",
        "I position myself to avoid pressure releases",
        "I position myself to avoid dropped objects",
        "I establish and obey barriers and exclusion zones",
        "I take action to secure loose objects and report potential dropped objects",
    ),
    related_energy_sources=(
        EnergySource.GRAVITY,
        EnergySource.MOTION,
        EnergySource.MECHANICAL,
        EnergySource.PRESSURE,
        EnergySource.RADIATION,
    ),
    trigger_phrases=(
        "line of fire",
        "struck by",
        "hit by",
        "caught between",
        "pinned",
        "dropped object",
        "falling object",
        "swinging load",
        "under the load",
        "stood under",
        "recoil",
        "whipped",
        "released suddenly",
        "pinch point",
        "exclusion zone",
    ),
)

SAFE_MECHANICAL_LIFTING = LifeSavingRuleDefinition(
    rule=LifeSavingRule.SAFE_MECHANICAL_LIFTING,
    short_name="Plan lifting operations and control the area",
    statements=(
        "I confirm that the equipment and load have been inspected and are fit for purpose",
        "I only operate equipment that I am qualified to use",
        "I establish and obey barriers and exclusion zones",
        "I never walk under a suspended load",
    ),
    related_energy_sources=(EnergySource.GRAVITY, EnergySource.MOTION),
    trigger_phrases=(
        "lifting",
        "lift plan",
        "crane",
        "sling",
        "shackle",
        "rigging",
        "hoisting",
        "suspended load",
        "side boom",
        "winch",
        "spreader bar",
        "swl",
        "load chart",
        "rigger",
        "third party inspection",
        "colour coding",
    ),
)

WORK_AUTHORISATION = LifeSavingRuleDefinition(
    rule=LifeSavingRule.WORK_AUTHORISATION,
    short_name="Work with a valid permit when required",
    statements=(
        "I have confirmed if a permit is required",
        "I am authorised to perform the work",
        "I understand the permit",
        "I have confirmed that hazards are controlled and it is safe to start",
        "I stop and reassess if conditions change",
    ),
    related_energy_sources=(
        EnergySource.ELECTRICAL,
        EnergySource.PRESSURE,
        EnergySource.TEMPERATURE,
        EnergySource.CHEMICAL,
        EnergySource.RADIATION,
        EnergySource.BIOLOGICAL,
        EnergySource.SOUND,
    ),
    trigger_phrases=(
        "permit to work",
        "ptw",
        "work permit",
        "permit expired",
        "no permit",
        "without permit",
        "authorisation",
        "authorization",
        "clearance",
        "simops",
        "simultaneous operations",
        "conditions changed",
        "did not stop the job",
        "toolbox talk not done",
    ),
)

WORKING_AT_HEIGHT = LifeSavingRuleDefinition(
    rule=LifeSavingRule.WORKING_AT_HEIGHT,
    short_name="Protect yourself against a fall when working at height",
    statements=(
        "I inspect my fall protection equipment before use",
        "I secure tools and work materials to prevent dropped objects",
        "I tie off 100% to approved anchor points while outside a protected area",
    ),
    related_energy_sources=(EnergySource.GRAVITY,),
    trigger_phrases=(
        "working at height",
        "work at height",
        "fall protection",
        "harness",
        "lanyard",
        "anchor point",
        "tie off",
        "not tied off",
        "scaffold",
        "monkey board",
        "derrick floor",
        "derrickman",
        "ladder",
        "elevated platform",
        "dropped tool",
        "tool lanyard",
    ),
)


LIFE_SAVING_RULES: dict[LifeSavingRule, LifeSavingRuleDefinition] = {
    d.rule: d
    for d in (
        BYPASSING_SAFETY_CONTROLS,
        CONFINED_SPACE,
        DRIVING,
        ENERGY_ISOLATION,
        HOT_WORK,
        LINE_OF_FIRE,
        SAFE_MECHANICAL_LIFTING,
        WORK_AUTHORISATION,
        WORKING_AT_HEIGHT,
    )
}


#: Which Life-Saving Rules an energy source can engage. Derived from the
#: `related_energy_sources` declared on each rule, kept as an explicit mapping
#: so the rule engine never has to invert it at runtime.
LSR_BY_ENERGY: dict[EnergySource, tuple[LifeSavingRule, ...]] = {
    source: tuple(
        d.rule for d in LIFE_SAVING_RULES.values() if source in d.related_energy_sources
    )
    for source in EnergySource
}


@dataclass(frozen=True, slots=True)
class LifeSavingRuleAssignment:
    """A Life-Saving Rule assigned to one report, with rank and evidence.

    A container. Populated by the rule engine; nothing here decides the rank.
    `evidence_spans` are exact character offsets into the source report.
    """

    rule: LifeSavingRule
    rank: RuleAssignmentRank
    evidence_spans: tuple[tuple[int, int], ...] = ()
    rationale: str | None = None
    citations: tuple[Citation, ...] = field(default=(IOGP_459, PRAHARI_MODELLING))
