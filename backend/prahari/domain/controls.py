"""Direct controls, indirect controls, and control status.

The three-part test
-------------------
A control is a DIRECT control only if all three of the following hold. The
wording is taken from the Edison Electric Institute High-Energy Control
Assessment (HECA), principal author Dr. Matthew Hallowell:

  (a) it is specifically targeted to the high-energy source;
  (b) it effectively mitigates exposure to that high-energy source when
      installed, verified, and used properly - that is, a SIF should not occur
      if those conditions are present;
  (c) it remains effective even if there is unintentional human error during
      the work, unrelated to the installation of the control.

Anything failing any one of the three is an INDIRECT control. Indirect controls
are not worthless - they enable and sustain direct controls - but they must
never be counted as the thing standing between a worker and a fatal energy
release. Training, signage, permits-on-paper, supervision, observation
programmes and most general-purpose PPE all fail test (c), because they are
defeated by exactly the ordinary human error they are meant to survive.

A caveat that matters when defending this
-----------------------------------------
EEI notes that many direct controls are only direct as a SYSTEM: a fall-arrest
system is direct only when the engineered anchor, the lanyard, the harness and
a structure that can take the load are all present. One component alone does
not constitute a direct control. `requires_system` records this.

Pure data and types. No evaluation logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from prahari.domain.citations import (
    EEI_HECA,
    EEI_SCL,
    INGAA_HEHC_2024,
    Citation,
    OISD_STD_174,
    OISD_STD_190,
    OISD_STD_216,
    PRAHARI_MODELLING,
)
from prahari.domain.energy import EnergySource


class ControlStatus(str, Enum):
    """The observed condition of a control in a given report.

    Deliberately distinguishes 'we saw it and confirmed it worked' from 'it was
    mentioned'. In SIF precursor work the difference between PRESENT_VERIFIED
    and PRESENT_UNVERIFIED is the difference between a controlled high-energy
    task and a precursor.
    """

    PRESENT_VERIFIED = "present_verified"
    PRESENT_UNVERIFIED = "present_unverified"
    ABSENT = "absent"
    FAILED = "failed"
    BYPASSED = "bypassed"
    NOT_FOLLOWED = "not_followed"
    UNKNOWN = "unknown"


#: Statuses under which a direct control cannot be relied on. Provided as data
#: for the rule engine to consume; this module draws no conclusion from it.
#:
#: PRESENT_UNVERIFIED is deliberately in this set. Limb (b) of the direct
#: control test requires the control to be "installed, VERIFIED, and used
#: properly". A BOP nobody function-tested, an isolation nobody proved dead and
#: a harness nobody inspected are not yet controls - they are precursors. Only
#: PRESENT_VERIFIED is protective.
NON_PROTECTIVE_STATUSES: frozenset[ControlStatus] = frozenset(
    {
        ControlStatus.PRESENT_UNVERIFIED,
        ControlStatus.ABSENT,
        ControlStatus.FAILED,
        ControlStatus.BYPASSED,
        ControlStatus.NOT_FOLLOWED,
        ControlStatus.UNKNOWN,
    }
)

#: The only status under which a direct control actually protects anyone.
PROTECTIVE_STATUSES: frozenset[ControlStatus] = frozenset({ControlStatus.PRESENT_VERIFIED})


class ControlClass(str, Enum):
    """Direct vs indirect, and the two sub-kinds of direct control.

    ABSOLUTE  - completely eliminates high-energy exposure when installed,
                verified and used properly (EEI SCL).
    MITIGATING- reduces energy exposure to below the threshold (EEI SCL).
    INDIRECT  - fails at least one limb of the three-part test.
    """

    DIRECT_ABSOLUTE = "direct_absolute"
    DIRECT_MITIGATING = "direct_mitigating"
    INDIRECT = "indirect"


@dataclass(frozen=True, slots=True)
class DirectControlTest:
    """The three-part test, as data, so it can be quoted in a verdict."""

    targets_the_energy_source: str = (
        "The control is specifically targeted to the high-energy source."
    )
    mitigates_when_used_properly: str = (
        "The control effectively mitigates exposure to the high-energy source "
        "when installed, verified and used properly - a SIF should not occur "
        "if those conditions are present."
    )
    survives_unintentional_human_error: str = (
        "The control remains effective even if there is unintentional human "
        "error during the work, unrelated to the installation of the control."
    )
    citation: Citation = EEI_HECA


DIRECT_CONTROL_TEST = DirectControlTest()


@dataclass(frozen=True, slots=True)
class ControlDefinition:
    """One named control in the inventory."""

    key: str
    label: str
    energy_source: EnergySource | None
    control_class: ControlClass
    rationale: str
    phrases: tuple[str, ...] = ()
    requires_system: bool = False
    citations: tuple[Citation, ...] = field(default=(EEI_HECA,))

    @property
    def is_direct(self) -> bool:
        """True for both direct sub-kinds. A property, not a decision."""
        return self.control_class in (
            ControlClass.DIRECT_ABSOLUTE,
            ControlClass.DIRECT_MITIGATING,
        )


# ==========================================================================
# DIRECT CONTROLS, by energy source
# ==========================================================================

DIRECT_CONTROLS: tuple[ControlDefinition, ...] = (
    # -- GRAVITY ----------------------------------------------------------
    ControlDefinition(
        key="guardrail",
        label="Guardrail / engineered edge protection",
        energy_source=EnergySource.GRAVITY,
        control_class=ControlClass.DIRECT_ABSOLUTE,
        rationale=(
            "A compliant guardrail removes the exposure entirely and keeps "
            "working whether or not the worker is paying attention."
        ),
        phrases=("guardrail", "guard rail", "handrail", "edge protection", "railing" "toe board", "barrier on the platform", "guardrail was provided", "scaffold",),
        citations=(EEI_SCL, INGAA_HEHC_2024),
    ),
    ControlDefinition(
        key="fall_arrest_system",
        label="Fall-arrest system anchored to an engineered anchor point",
        energy_source=EnergySource.GRAVITY,
        control_class=ControlClass.DIRECT_MITIGATING,
        requires_system=True,
        rationale=(
            "Direct only as a complete system: engineered anchor, lanyard or "
            "SRL, harness and a structure able to take the arrest load. The "
            "harness alone is not a direct control."
        ),
        phrases=(
            "fall arrest",
            "full body harness",
            "double lanyard",
            "self retracting",
            "anchor point",
            "tied off",
            "100% tie off", "safety belt", "safety harness", "harness", "life line", "lanyard",),
        citations=(EEI_HECA, EEI_SCL, OISD_STD_190),
    ),
    ControlDefinition(
        key="hole_cover",
        label="Secured floor / hole cover",
        energy_source=EnergySource.GRAVITY,
        control_class=ControlClass.DIRECT_ABSOLUTE,
        rationale="A secured cover removes the opening; it does not depend on attention.",
        phrases=("hole cover", "floor cover", "covered the opening", "grating secured" "cover plate", "grating",),
        citations=(EEI_SCL,),
    ),
    ControlDefinition(
        key="rigging_with_secondary_retention",
        label="Certified rigging with secondary retention / secondary braking",
        energy_source=EnergySource.GRAVITY,
        control_class=ControlClass.DIRECT_MITIGATING,
        requires_system=True,
        rationale=(
            "INGAA lists proper rigging with secondary braking, automatic "
            "brakes and additional securing lines as the direct control for "
            "suspended loads."
        ),
        phrases=(
            "certified sling",
            "secondary retention",
            "secondary braking",
            "automatic brake",
            "securing line",
            "load tested",
            "proper rigging", "sling", "shackle", "rigging", "lift plan", "colour coding", "test certificate", "exclusion zone was maintained",),
        citations=(INGAA_HEHC_2024,),
    ),
    # -- MOTION -----------------------------------------------------------
    ControlDefinition(
        key="cab_protection",
        label="Cab protection: ROPS/FOPS, reinforced cabin, seatbelt restraint",
        energy_source=EnergySource.MOTION,
        control_class=ControlClass.DIRECT_MITIGATING,
        requires_system=True,
        rationale=(
            "INGAA's named direct control for heavy mobile equipment tipping "
            "and rollover: reinforced cabin, brush guards, rollover "
            "protection, seatbelt restraint."
        ),
        phrases=("rops", "fops", "rollover protection", "reinforced cabin", "brush guard" "cab protection", "seat restraint", "rops/fops", "cab guard", "rollover",),
        citations=(INGAA_HEHC_2024,),
    ),
    ControlDefinition(
        key="vehicle_occupant_restraint",
        label="Seatbelt, airbag and rollover frame in a motor vehicle",
        energy_source=EnergySource.MOTION,
        control_class=ControlClass.DIRECT_MITIGATING,
        rationale=(
            "One of the few cases where worn PPE-like equipment is a direct "
            "control: EEI names airbags and seat belts explicitly, because "
            "they function during the event regardless of the error that "
            "caused it."
        ),
        phrases=("seat belt", "seatbelt", "airbag", "rollover frame", "restraint" "occupant restraint",),
        citations=(EEI_SCL, INGAA_HEHC_2024),
    ),
    ControlDefinition(
        key="hard_physical_barrier",
        label="Hard engineered physical barrier separating people from moving equipment",
        energy_source=EnergySource.MOTION,
        control_class=ControlClass.DIRECT_ABSOLUTE,
        rationale=(
            "EEI names hard physical barriers as direct controls. Note the "
            "sharp distinction from soft barricade tape and fencing, which "
            "INGAA classes as 'Other Controls' and which are NOT direct."
        ),
        phrases=("concrete barrier", "jersey barrier", "hard barrier", "crash barrier" "hard barricade",),
        citations=(EEI_SCL, INGAA_HEHC_2024),
    ),
    ControlDefinition(
        key="cribbing_blocking",
        label="Cribbing / blocking against pipe roll",
        energy_source=EnergySource.MOTION,
        control_class=ControlClass.DIRECT_ABSOLUTE,
        rationale="INGAA's named direct control for struck-by from pipe rolling on supports.",
        phrases=("cribbing", "blocking", "chocked", "wedges", "pipe stopper" "chock",),
        citations=(INGAA_HEHC_2024,),
    ),
    # -- MECHANICAL -------------------------------------------------------
    ControlDefinition(
        key="machine_guarding",
        label="Fixed machine guarding",
        energy_source=EnergySource.MECHANICAL,
        control_class=ControlClass.DIRECT_ABSOLUTE,
        rationale=(
            "EEI names machine guarding as a direct control. A fixed guard "
            "keeps the body out of the rotating part regardless of attention."
        ),
        phrases=("machine guard", "guard fitted", "coupling guard", "belt guard", "caging" "guard", "tong guard", "snub line", "hands-off", "hands-free",),
        citations=(EEI_SCL, INGAA_HEHC_2024),
    ),
    ControlDefinition(
        key="mechanical_loto",
        label="Lockout/tagout of stored mechanical energy with verification",
        energy_source=EnergySource.MECHANICAL,
        control_class=ControlClass.DIRECT_ABSOLUTE,
        requires_system=True,
        rationale=(
            "Direct only when the isolation is locked, tagged AND verified at "
            "zero energy. An unverified isolation is PRESENT_UNVERIFIED, not a "
            "working direct control."
        ),
        phrases=("lockout", "loto", "locked and tagged", "zero energy verified", "de-energised" "isolation", "isolated", "brake applied",),
        citations=(EEI_SCL, EEI_HECA),
    ),
    ControlDefinition(
        key="emergency_stop_torque_limiter",
        label="Emergency stop function / torque limiter on rotating equipment",
        energy_source=EnergySource.MECHANICAL,
        control_class=ControlClass.DIRECT_MITIGATING,
        rationale="INGAA names torque limiter devices and emergency stop functions as direct.",
        phrases=("emergency stop", "e-stop", "torque limiter", "kill switch", "chain brake" "load limiter",),
        citations=(INGAA_HEHC_2024,),
    ),
    # -- ELECTRICAL -------------------------------------------------------
    ControlDefinition(
        key="electrical_isolation_verified",
        label="De-energisation and LOTO isolation with verified zero voltage",
        energy_source=EnergySource.ELECTRICAL,
        control_class=ControlClass.DIRECT_ABSOLUTE,
        requires_system=True,
        rationale=(
            "The archetypal direct control. Direct only when isolated, locked, "
            "tagged and PROVED dead at the point of work; the proving step is "
            "what makes it survive human error."
        ),
        phrases=(
            "de-energised",
            "de-energized",
            "isolated and locked",
            "loto applied",
            "tested dead",
            "zero voltage",
            "permit to work electrical", "isolation", "isolated", "shutdown", "racked out", "voltage detector", "authorised electrician",),
        citations=(EEI_SCL, EEI_HECA, OISD_STD_216),
    ),
    ControlDefinition(
        key="insulated_barrier",
        label="Insulated barrier, insulating guard or insulated boom",
        energy_source=EnergySource.ELECTRICAL,
        control_class=ControlClass.DIRECT_MITIGATING,
        rationale=(
            "INGAA names insulated booms, insulating guards and insulated "
            "cable as the direct controls where de-energisation is not "
            "practicable, e.g. live overhead transmission lines."
        ),
        phrases=("insulated boom", "insulating guard", "line cover up", "insulated cable" "insulated",),
        citations=(INGAA_HEHC_2024, EEI_SCL),
    ),
    ControlDefinition(
        key="equipment_earthing",
        label="Equipment earthing / bonding",
        energy_source=EnergySource.ELECTRICAL,
        control_class=ControlClass.DIRECT_MITIGATING,
        rationale="INGAA names equipment grounding as the direct control for welding shock.",
        phrases=("earthing", "earthed", "grounded", "bonding", "elcb", "rcd" "earth",),
        citations=(INGAA_HEHC_2024, OISD_STD_216),
    ),
    # -- PRESSURE ---------------------------------------------------------
    ControlDefinition(
        key="double_block_and_bleed",
        label="Double block and bleed with verified zero pressure",
        energy_source=EnergySource.PRESSURE,
        control_class=ControlClass.DIRECT_ABSOLUTE,
        requires_system=True,
        rationale=(
            "Two isolation barriers plus a proven bleed path. Verification of "
            "zero pressure at the bleed is what makes it survive the error of "
            "a valve passing."
        ),
        phrases=(
            "double block and bleed",
            "dbb",
            "spade fitted",
            "blind fitted",
            "spectacle blind",
            "bled to zero",
            "zero pressure confirmed", "isolation valve", "bleed", "master valve",),
        citations=(EEI_SCL, EEI_HECA),
    ),
    ControlDefinition(
        key="depressurise_and_verify",
        label="Depressurise and verify zero stored energy before breaking containment",
        energy_source=EnergySource.PRESSURE,
        control_class=ControlClass.DIRECT_ABSOLUTE,
        rationale=(
            "Elimination of the energy rather than protection from it. The "
            "verification step is the direct part."
        ),
        phrases=("depressurised", "depressurized", "bled down", "vented to flare", "drained" "cooled",),
        citations=(EEI_SCL,),
    ),
    ControlDefinition(
        key="well_barrier_envelope",
        label="Two tested well barriers (BOP / kill system) per well-control practice",
        energy_source=EnergySource.PRESSURE,
        control_class=ControlClass.DIRECT_ABSOLUTE,
        requires_system=True,
        rationale=(
            "OISD-STD-174 well control and OISD-RP-238 well integrity require "
            "two independent tested barriers. Tested is the operative word: an "
            "untested BOP is PRESENT_UNVERIFIED."
        ),
        phrases=(
            "bop tested",
            "bop function test",
            "pressure tested",
            "two barriers",
            "barrier envelope",
            "kill line",
            "choke manifold", "bop", "well killed", "tested barriers", "barriers were in place", "well was killed", "zero pressure",),
        citations=(OISD_STD_174, PRAHARI_MODELLING),
    ),
    ControlDefinition(
        key="whip_check",
        label="Whip check / hose restraint on pressurised hose connections",
        energy_source=EnergySource.PRESSURE,
        control_class=ControlClass.DIRECT_MITIGATING,
        rationale=(
            "INGAA's named direct control for high-pressure hose connection "
            "failure, repeated across several pipeline tasks."
        ),
        phrases=("whip check", "whipcheck", "hose restraint", "safety pin and tie wire"),
        citations=(INGAA_HEHC_2024,),
    ),
    ControlDefinition(
        key="excavation_support",
        label="Engineered excavation support: shoring, trench box, benching or sloping",
        energy_source=EnergySource.PRESSURE,
        control_class=ControlClass.DIRECT_ABSOLUTE,
        rationale="Both EEI and INGAA name benching, sloping and trench boxes as the direct control.",
        phrases=("trench box", "shoring", "shored", "benching", "sloped", "sheet piling" "sloping", "benched",),
        citations=(EEI_HECA, INGAA_HEHC_2024),
    ),
    # -- TEMPERATURE ------------------------------------------------------
    ControlDefinition(
        key="thermal_insulation_barrier",
        label="Thermal insulation barrier / welding blanket",
        energy_source=EnergySource.TEMPERATURE,
        control_class=ControlClass.DIRECT_MITIGATING,
        rationale=(
            "EEI names thermal insulation barriers as direct. INGAA names "
            "welding blankets and thermal insulated gloves for specific "
            "high-temperature pipeline tasks - a narrow, energy-specific PPE "
            "exception, not a general licence to count PPE."
        ),
        phrases=("welding blanket", "thermal insulation", "lagging", "heat shield", "fire blanket" "insulation", "thermal insulated gloves",),
        citations=(EEI_SCL, INGAA_HEHC_2024),
    ),
    ControlDefinition(
        key="fuel_isolation_and_gas_test",
        label="Flammable isolation plus continuous gas monitoring for hot work",
        energy_source=EnergySource.TEMPERATURE,
        control_class=ControlClass.DIRECT_ABSOLUTE,
        requires_system=True,
        rationale=(
            "Removing or isolating the fuel eliminates the fire energy. "
            "Continuous monitoring, not a single spot gas test, is what makes "
            "it survive a change in conditions."
        ),
        phrases=(
            "gas test",
            "continuous gas monitoring",
            "flammables removed",
            "purged",
            "combustibles removed",
            "fuel isolated", "gas testing", "fire watch", "gas detector", "combustibles", "flammable material",),
        citations=(EEI_SCL, INGAA_HEHC_2024),
    ),
    ControlDefinition(
        key="fixed_fire_suppression",
        label="Automatic fire detection and suppression system",
        energy_source=EnergySource.TEMPERATURE,
        control_class=ControlClass.DIRECT_MITIGATING,
        rationale="INGAA names automatic fire suppression and detection/alarm systems as direct.",
        phrases=("fire suppression", "deluge", "sprinkler", "fire detection", "gas detection system"),
        citations=(INGAA_HEHC_2024,),
    ),
    # -- CHEMICAL ---------------------------------------------------------
    ControlDefinition(
        key="engineered_ventilation",
        label="Engineered forced ventilation of the work space",
        energy_source=EnergySource.CHEMICAL,
        control_class=ControlClass.DIRECT_MITIGATING,
        rationale=(
            "EEI names ventilation and containment as direct controls for "
            "toxic exposure. It works on the atmosphere itself rather than "
            "relying on the worker."
        ),
        phrases=("forced ventilation", "air mover", "eductor", "purged and ventilated", "extraction" "ventilation", "blower",),
        citations=(EEI_HECA, INGAA_HEHC_2024),
    ),
    ControlDefinition(
        key="supplied_air_respiratory_protection",
        label="Supplied-air breathing apparatus with continuous atmosphere monitoring",
        energy_source=EnergySource.CHEMICAL,
        control_class=ControlClass.DIRECT_MITIGATING,
        requires_system=True,
        rationale=(
            "The second narrow PPE exception. SCBA/airline is energy-specific "
            "and functions during the exposure, but only as a system with "
            "monitoring, an attendant and a rescue plan; a cartridge mask in "
            "an IDLH atmosphere is not a direct control."
        ),
        phrases=("scba", "breathing apparatus", "airline respirator", "escape set", "supplied air" "gas monitor", "personal monitor", "personal gas monitor", "standby man", "attendant", "wind sock",),
        citations=(EEI_HECA, PRAHARI_MODELLING),
    ),
    ControlDefinition(
        key="chemical_isolation_and_purge",
        label="Positive isolation and purge of the hydrocarbon or chemical source",
        energy_source=EnergySource.CHEMICAL,
        control_class=ControlClass.DIRECT_ABSOLUTE,
        rationale="Elimination: the substance is not present to be exposed to.",
        phrases=("positive isolation", "purged with nitrogen", "line cleared", "flushed and purged" "blinded",),
        citations=(EEI_SCL,),
    ),
    # -- BIOLOGICAL -------------------------------------------------------
    ControlDefinition(
        key="physical_exclusion_of_fauna",
        label="Physical exclusion: sealed enclosures, cleared vegetation, snake-proof barriers",
        energy_source=EnergySource.BIOLOGICAL,
        control_class=ControlClass.DIRECT_MITIGATING,
        rationale=(
            "A prahari modelling decision. Physical exclusion is the only "
            "biological control that meets limb (c) - it works whether or not "
            "the worker is looking where they step."
        ),
        phrases=("vegetation cleared", "sealed enclosure", "snake guard", "mesh screen", "gaiters" "vegetation", "pit was covered",),
        citations=(PRAHARI_MODELLING,),
    ),
    ControlDefinition(
        key="onsite_antivenom_and_evacuation",
        label="On-site antivenom stock and a tested casualty evacuation plan",
        energy_source=EnergySource.BIOLOGICAL,
        control_class=ControlClass.DIRECT_MITIGATING,
        rationale=(
            "For remote Indian well pads the controlling variable in snakebite "
            "fatality is time to antivenom, so a tested evacuation capability "
            "mitigates the outcome independently of the worker's actions. "
            "prahari modelling decision."
        ),
        phrases=("antivenom", "anti venom", "medevac", "ambulance on site", "evacuation plan tested" "ambulance", "evacuation", "anti-snake venom",),
        citations=(PRAHARI_MODELLING,),
    ),
    # -- RADIATION --------------------------------------------------------
    ControlDefinition(
        key="source_shielding_and_interlock",
        label="Built-in source shielding, collimator and mechanical failsafe",
        energy_source=EnergySource.RADIATION,
        control_class=ControlClass.DIRECT_ABSOLUTE,
        rationale=(
            "INGAA: equipment-specific direct controls are built into all "
            "radiography equipment - lead shielding, mechanical failsafes."
        ),
        phrases=("lead shielding", "collimator", "mechanical failsafe", "interlock", "source shielded" "camera", "shielded position", "crimp", "radiography equipment", "failsafe",),
        citations=(INGAA_HEHC_2024,),
    ),
    ControlDefinition(
        key="radiation_survey_verified",
        label="Post-exposure survey-meter verification that the source is retracted",
        energy_source=EnergySource.RADIATION,
        control_class=ControlClass.DIRECT_MITIGATING,
        rationale=(
            "The survey meter reading is the verification step that catches "
            "the failure mode that kills radiographers: an unretracted source "
            "that nobody noticed."
        ),
        phrases=("survey meter", "radiation survey", "source confirmed retracted", "dose rate checked" "tld badge", "cordon",),
        citations=(INGAA_HEHC_2024, PRAHARI_MODELLING),
    ),
    ControlDefinition(
        key="welding_screen",
        label="Welding curtain / screen and helmet against arc UV",
        energy_source=EnergySource.RADIATION,
        control_class=ControlClass.DIRECT_MITIGATING,
        rationale="INGAA names welding curtains and welding helmets as the direct control for arc flash UV.",
        phrases=("welding curtain", "welding screen", "welding helmet", "arc screen" "welding shield",),
        citations=(INGAA_HEHC_2024,),
    ),
    # -- SOUND ------------------------------------------------------------
    ControlDefinition(
        key="noise_enclosure",
        label="Acoustic enclosure or engineered noise attenuation at source",
        energy_source=EnergySource.SOUND,
        control_class=ControlClass.DIRECT_MITIGATING,
        rationale=(
            "Only source-level attenuation meets limb (c) for noise; hearing "
            "protection depends on being worn correctly and so does not. "
            "prahari modelling decision."
        ),
        phrases=("acoustic enclosure", "silencer", "noise hood", "attenuator", "acoustic lagging" "enclosure",),
        citations=(PRAHARI_MODELLING,),
    ),
)


# ==========================================================================
# INDIRECT CONTROLS - must never be counted as direct
# ==========================================================================

INDIRECT_CONTROLS: tuple[ControlDefinition, ...] = (
    ControlDefinition(
        key="training",
        label="Training, induction or competency certification",
        energy_source=None,
        control_class=ControlClass.INDIRECT,
        rationale="EEI: training is susceptible to unintentional human error. Fails limb (c).",
        phrases=("trained", "training", "induction", "competency", "certified operator", "refresher" "manual handling training",),
        citations=(EEI_SCL, EEI_HECA),
    ),
    ControlDefinition(
        key="toolbox_talk",
        label="Toolbox talk / pre-job meeting / JSA / TBT",
        energy_source=None,
        control_class=ControlClass.INDIRECT,
        rationale=(
            "INGAA: pre-job meetings and JSAs facilitate the deployment of "
            "controls but do not themselves meet the definition of a Direct "
            "Control."
        ),
        phrases=("toolbox talk", "tbt", "pre job meeting", "jsa", "job safety analysis", "pep talk"),
        citations=(INGAA_HEHC_2024,),
    ),
    ControlDefinition(
        key="signage",
        label="Signage, warning signs and labels",
        energy_source=None,
        control_class=ControlClass.INDIRECT,
        rationale="EEI names warning signs among the things that are not direct controls.",
        phrases=("signage", "warning sign", "caution sign", "display board", "notice board"),
        citations=(EEI_SCL, INGAA_HEHC_2024),
    ),
    ControlDefinition(
        key="permit_paperwork_alone",
        label="A permit to work as paperwork, without verified physical isolation",
        energy_source=None,
        control_class=ControlClass.INDIRECT,
        rationale=(
            "A permit authorises and coordinates; it does not stand between a "
            "worker and an energy release. The isolation the permit calls for "
            "may be a direct control - the permit itself is not."
        ),
        phrases=("permit issued", "permit to work", "ptw", "work permit", "clearance obtained"),
        citations=(INGAA_HEHC_2024, PRAHARI_MODELLING),
    ),
    ControlDefinition(
        key="supervision",
        label="Supervision, observation programmes and safety officer presence",
        energy_source=None,
        control_class=ControlClass.INDIRECT,
        rationale="INGAA lists observation programmes among activities that are not Direct Controls.",
        phrases=("supervisor present", "safety officer", "observation", "monitoring by supervisor"),
        citations=(INGAA_HEHC_2024,),
    ),
    ControlDefinition(
        key="spotter",
        label="Spotter / banksman / flagman",
        energy_source=None,
        control_class=ControlClass.INDIRECT,
        rationale=(
            "INGAA explicitly lists spotters as an 'Other Control'. A spotter "
            "is a human watching for error, so it fails limb (c) by "
            "construction."
        ),
        phrases=("spotter", "banksman", "flagman", "signal man", "watchman"),
        citations=(INGAA_HEHC_2024,),
    ),
    ControlDefinition(
        key="exclusion_zone_soft",
        label="Exclusion zone, barricade tape or soft fencing",
        energy_source=None,
        control_class=ControlClass.INDIRECT,
        rationale=(
            "INGAA lists exclusion zones and barriers/fencing as 'Other "
            "Controls'. Note the contrast with a hard engineered physical "
            "barrier, which IS direct - the distinction is whether it stops "
            "the energy or merely marks where it is."
        ),
        phrases=("barricade", "barricading", "caution tape", "cordoned", "exclusion zone", "fencing" "barricaded",),
        citations=(INGAA_HEHC_2024,),
    ),
    ControlDefinition(
        key="procedure_alone",
        label="Written procedure, SOP or method statement",
        energy_source=None,
        control_class=ControlClass.INDIRECT,
        rationale="EEI: rules and procedures are susceptible to unintentional human error.",
        phrases=("procedure", "sop", "method statement", "work instruction", "as per procedure"),
        citations=(EEI_SCL, INGAA_HEHC_2024),
    ),
    ControlDefinition(
        key="general_ppe",
        label="General-purpose PPE: hard hat, gloves, safety boots, coveralls, goggles",
        energy_source=None,
        control_class=ControlClass.INDIRECT,
        rationale=(
            "EEI: most standard non-specialised PPE is not a direct control - "
            "it is not designed to withstand a 1,500 J release. The narrow "
            "exceptions already modelled as direct are seatbelts and airbags, "
            "arc-rated and thermal-specific clothing, welding helmets and "
            "supplied-air respiratory protection."
        ),
        phrases=("hard hat", "helmet", "safety shoes", "safety boots", "gloves", "coverall", "goggles", "ppe worn" "ear muff", "ear plug", "safety shoe", "anti-skid", "repellent", "padding",),
        citations=(EEI_SCL, EEI_HECA),
    ),
    ControlDefinition(
        key="experience_and_care",
        label="Experience, vigilance or an instruction to 'be careful'",
        energy_source=None,
        control_class=ControlClass.INDIRECT,
        rationale=(
            "EEI names experience among the non-controls. 'Be careful' asks "
            "the worker to not make the error that limb (c) assumes they will "
            "make."
        ),
        phrases=("be careful", "experienced worker", "years of experience", "took care", "was cautious", "counselled"),
        citations=(EEI_SCL, PRAHARI_MODELLING),
    ),
    ControlDefinition(
        key="reverse_alarm_and_cameras",
        label="Reverse alarms, cameras and proximity warnings",
        energy_source=None,
        control_class=ControlClass.INDIRECT,
        rationale="INGAA lists cameras and reverse alarms as 'Other Controls', not Direct Controls.",
        phrases=("reverse alarm", "reversing camera", "backup alarm", "proximity alarm", "horn"),
        citations=(INGAA_HEHC_2024,),
    ),
    ControlDefinition(
        key="tagline",
        label="Tagline on a suspended load",
        energy_source=None,
        control_class=ControlClass.INDIRECT,
        rationale=(
            "INGAA lists taglines as 'Other Controls'. A tagline positions a "
            "load; it does not stop it falling."
        ),
        phrases=("tagline", "tag line", "guide rope"),
        citations=(INGAA_HEHC_2024,),
    ),
)


ALL_CONTROLS: tuple[ControlDefinition, ...] = DIRECT_CONTROLS + INDIRECT_CONTROLS

CONTROLS_BY_KEY: dict[str, ControlDefinition] = {c.key: c for c in ALL_CONTROLS}

DIRECT_CONTROLS_BY_ENERGY: dict[EnergySource, tuple[ControlDefinition, ...]] = {
    source: tuple(c for c in DIRECT_CONTROLS if c.energy_source == source)
    for source in EnergySource
}


@dataclass(frozen=True, slots=True)
class ControlObservation:
    """A control mentioned in a report, with its observed status and spans.

    A container populated by the rule engine. `evidence_spans` are exact
    character offsets into the source report text, which is what makes a
    verdict defensible.
    """

    control_key: str
    status: ControlStatus
    evidence_spans: tuple[tuple[int, int], ...] = ()
    note: str | None = None
