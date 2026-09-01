"""The high-energy threshold and the magnitude cues that imply crossing it.

The number
---------
A hazard is "high-energy" when the energy that could be released exceeds
**1,500 joules**. This figure is not ours. It comes from the energy-based
safety research programme led by Dr. Matthew Hallowell and published by the
Edison Electric Institute: hazards with more than 1,500 joules of physical
energy are the ones most likely to produce a serious injury or fatality.

A note on units, because a safety professional will ask
-------------------------------------------------------
Some documents in this literature quote the threshold as "1500 Joules or
approximately 500 ft-lb" (INGAA 2024), and the EEI SCL Model text says
"more than 500 ft-lbs of physical energy". Those two statements are not
numerically equal: 500 ft-lbf is about 678 J, and 1,500 J is about 1,106
ft-lbf. The joule figure is the one consistently used as the definition in the
primary source (EEI HECA), so prahari uses 1,500 J and records the discrepancy
rather than hiding it. See docs/DOMAIN.md.

What this module is
-------------------
A lookup table of observable cues that imply the threshold has been crossed,
so that an analyst never has to compute joules by hand. Each cue records the
energy type it belongs to, the published magnitude that defines it, the
rationale, and a citation.

Pure data and types. Nothing here decides anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from prahari.domain.citations import (
    EEI_HECA,
    EEI_SCL,
    INGAA_HEHC_2024,
    Citation,
    PRAHARI_MODELLING,
)
from prahari.domain.energy import EnergySource

#: The high-energy threshold, in joules (EEI HECA, principal author Hallowell).
HIGH_ENERGY_THRESHOLD_JOULES: int = 1500

#: The foot-pound figure quoted alongside it in parts of the literature.
#: Retained only so the discrepancy is visible and documented, never for maths.
QUOTED_THRESHOLD_FOOT_POUNDS: int = 500


class CueBasis(str, Enum):
    """How a cue establishes that the threshold is crossed.

    MEASURED_MAGNITUDE - a published numeric threshold (height, voltage,
                         temperature, speed, depth, mass).
    CATEGORICAL        - the literature treats the presence of this hazard as
                         exceeding the threshold outright, with no measurement
                         needed (steam release, arc flash, explosion).
    COMPUTED           - energy must be computed case by case from a formula;
                         the cue only flags that a computation is owed.
    """

    MEASURED_MAGNITUDE = "measured_magnitude"
    CATEGORICAL = "categorical"
    COMPUTED = "computed"


@dataclass(frozen=True, slots=True)
class HighEnergyCue:
    """One observable condition implying release would exceed 1,500 J.

    `phrases` are lexical surface forms only, for span extraction. The
    numeric fields carry the published magnitude so that a rule can be written
    against a number the extraction layer pulled out of the text, rather than
    against a phrase match alone.
    """

    key: str
    energy_source: EnergySource
    label: str
    basis: CueBasis
    rationale: str
    phrases: tuple[str, ...]
    threshold_value: float | None = None
    threshold_unit: str | None = None
    imperial_equivalent: str | None = None
    citations: tuple[Citation, ...] = field(default=(EEI_HECA,))


HIGH_ENERGY_CUES: tuple[HighEnergyCue, ...] = (
    # -- GRAVITY ----------------------------------------------------------
    HighEnergyCue(
        key="fall_from_elevation",
        energy_source=EnergySource.GRAVITY,
        label="Fall from elevation",
        basis=CueBasis.MEASURED_MAGNITUDE,
        threshold_value=1.2,
        threshold_unit="m",
        imperial_equivalent="4 ft",
        rationale=(
            "EEI SCL/HECA set the fall-from-height high-energy threshold at "
            "4 feet of elevation, measured from the ground surface to the "
            "bottom of the feet. Note that many Indian and international "
            "programmes trigger fall protection at 1.8 m (6 ft) instead; "
            "prahari records the lower, more conservative 1.2 m figure as the "
            "energy threshold and treats 1.8 m as a second cue."
        ),
        phrases=(
            "working at height",
            "fell from a height",
            "fall from elevation",
            "from the derrick floor",
            "from the monkey board",
            "from the mast",
            "scaffold platform",
            "elevated platform",
            "above ground level", "at height", "derrick floor", "rig floor", "monkey board", "racking board", "scaffold", "platform at", "mtr height", "from the platform", "open grating", "floor opening", "unprotected edge", "went over the open edge", "fell to the ground",),
        citations=(EEI_SCL, EEI_HECA),
    ),
    HighEnergyCue(
        key="fall_above_1p8m",
        energy_source=EnergySource.GRAVITY,
        label="Fall from more than 1.8 m",
        basis=CueBasis.MEASURED_MAGNITUDE,
        threshold_value=1.8,
        threshold_unit="m",
        imperial_equivalent="6 ft",
        rationale=(
            "The 6 ft / 1.8 m fall-protection trigger used in construction "
            "practice. A 90 kg person falling 1.8 m releases roughly 1,590 J, "
            "which is unambiguously above the 1,500 J threshold, so any fall "
            "reported above this height is high-energy on the arithmetic "
            "alone."
        ),
        phrases=(
            "1.8 m",
            "6 feet",
            "two metres",
            "first floor level",
        ),
        citations=(EEI_HECA, PRAHARI_MODELLING),
    ),
    HighEnergyCue(
        key="suspended_load",
        energy_source=EnergySource.GRAVITY,
        label="Suspended load",
        basis=CueBasis.MEASURED_MAGNITUDE,
        threshold_value=227.0,
        threshold_unit="kg",
        imperial_equivalent="500 lb, raised more than 1 ft",
        rationale=(
            "EEI HECA: more than 500 lbs of load higher than 1 foot off the "
            "ground exceeds the threshold. Effectively every rigged lift on a "
            "drilling or pipeline spread qualifies."
        ),
        phrases=(
            "suspended load",
            "load overhead",
            "under the load",
            "crane lift",
            "rigging",
            "sling",
            "side boom",
            "casing string",
            "drill collar", "lifting of", "lowering", "lifting operation", "crane", "hoisting", "winch", "load was", "casing joints", "bop stack", "pipe section", "suspended",),
        citations=(EEI_HECA, INGAA_HEHC_2024),
    ),
    # -- MOTION -----------------------------------------------------------
    HighEnergyCue(
        key="motor_vehicle_speed",
        energy_source=EnergySource.MOTION,
        label="Motor vehicle at or above 30 mph",
        basis=CueBasis.MEASURED_MAGNITUDE,
        threshold_value=48.0,
        threshold_unit="km/h",
        imperial_equivalent="30 mph",
        rationale=(
            "EEI HECA sets 30 miles per hour as the motor-vehicle high-energy "
            "threshold."
        ),
        phrases=(
            "highway speed",
            "on the highway",
            "national highway",
            "30 mph",
            "50 kmph",
            "60 kmph",
            "80 kmph",
            "head on collision", "crew bus", "light vehicle", "pickup", "field road", "tanker",),
        citations=(EEI_HECA, EEI_SCL),
    ),
    HighEnergyCue(
        key="mobile_equipment_in_motion",
        energy_source=EnergySource.MOTION,
        label="Heavy mobile equipment in motion",
        basis=CueBasis.CATEGORICAL,
        rationale=(
            "EEI HECA treats mobile equipment as exceeding the threshold "
            "whenever the equipment or vehicle is in motion, without a speed "
            "measurement, because of its mass."
        ),
        phrases=(
            "equipment was moving",
            "while reversing",
            "while backing up",
            "excavator swing",
            "dozer",
            "side boom moving",
            "forklift moving",
            "vehicle in motion", "excavator", "forklift", "skid steer", "heavy mobile equipment", "crawler", "boom",),
        citations=(EEI_HECA, INGAA_HEHC_2024),
    ),
    # -- MECHANICAL -------------------------------------------------------
    HighEnergyCue(
        key="heavy_rotating_equipment",
        energy_source=EnergySource.MECHANICAL,
        label="Heavy rotating equipment",
        basis=CueBasis.CATEGORICAL,
        rationale=(
            "EEI HECA: heavy rotating equipment beyond powered hand tools "
            "typically exceeds the high-energy threshold."
        ),
        phrases=(
            "rotary table",
            "top drive",
            "drawworks",
            "mud pump",
            "spinning chain",
            "power tongs",
            "pumping unit",
            "walking beam",
            "belt drive",
            "auger",
            "reamer", "sucker rod", "counterweight", "shale shaker", "conveyor", "belt of pumping", "tripping operation", "grinder", "machinery",),
        citations=(EEI_HECA, INGAA_HEHC_2024),
    ),
    # -- ELECTRICAL -------------------------------------------------------
    HighEnergyCue(
        key="voltage_at_or_above_50v",
        energy_source=EnergySource.ELECTRICAL,
        label="Electrical contact at or above 50 volts",
        basis=CueBasis.MEASURED_MAGNITUDE,
        threshold_value=50.0,
        threshold_unit="V",
        rationale=(
            "EEI SCL/HECA: 50 volts is sufficient to result in serious injury "
            "or death, so any contact at or above 50 V is high-energy."
        ),
        phrases=(
            "240 volt",
            "415 volt",
            "440 volt",
            "11 kv",
            "33 kv",
            "ht line",
            "overhead power line",
            "live conductor",
            "switchgear",
            "busbar", "electrical", "mcc panel", "substation", "feeder", "electric shock", "electrocut", "transformer", "panel", "conductor", "cable termination", "starter",),
        citations=(EEI_SCL, EEI_HECA, INGAA_HEHC_2024),
    ),
    HighEnergyCue(
        key="arc_flash",
        energy_source=EnergySource.ELECTRICAL,
        label="Arc flash",
        basis=CueBasis.CATEGORICAL,
        rationale="EEI HECA: any arc flash exceeds the high-energy threshold.",
        phrases=("arc flash", "flashover", "arc blast", "short circuit blast", "arc", "flash",),
        citations=(EEI_HECA,),
    ),
    # -- PRESSURE ---------------------------------------------------------
    HighEnergyCue(
        key="pressurised_system",
        energy_source=EnergySource.PRESSURE,
        label="Pressurised system or vessel",
        basis=CueBasis.COMPUTED,
        rationale=(
            "EEI SCL requires stored energy in a pressure vessel to be "
            "computed per case. In upstream practice, wellhead, flowline, "
            "hydrotest and cylinder pressures are routinely orders of "
            "magnitude above 1,500 J, so presence of a pressurised system is "
            "treated as a cue that a computation is owed and, absent contrary "
            "evidence, that the threshold is crossed."
        ),
        phrases=(
            "pressurised line",
            "pressurized line",
            "hydro test",
            "wellhead",
            "trapped pressure",
            "gas release",
            "blowout",
            "well kick",
            "gas cylinder",
            "hose burst",
            "psv lifted",
            "pig launcher",
            "flange joint", "annulus", "casing pressure", "christmas tree", "flowline", "separator", "bop", "choke manifold", "kill line", "pressure testing", "pressurisation", "test pressure", "regulator", "cylinder", "compressed", "blind flange", "gland packing", "well ", "under pressure", "psv", "steam line",),
        citations=(EEI_SCL, INGAA_HEHC_2024),
    ),
    HighEnergyCue(
        key="excavation_depth",
        energy_source=EnergySource.PRESSURE,
        label="Unsupported excavation deeper than 1.5 m",
        basis=CueBasis.MEASURED_MAGNITUDE,
        threshold_value=1.5,
        threshold_unit="m",
        imperial_equivalent="5 ft",
        rationale=(
            "EEI HECA: unsupported soil exceeding 5 feet of height exceeds the "
            "threshold. Soil pressure rises by roughly 40 pounds per square "
            "foot per foot of depth, so a collapse at this depth is capable of "
            "fatal crushing and asphyxiation."
        ),
        phrases=(
            "trench",
            "excavation",
            "bell hole",
            "unsupported soil",
            "shoring",
            "trench box",
            "benching",
            "cave in",
            "collapse of trench", "soil", "spoil heap",),
        citations=(EEI_HECA, EEI_SCL, INGAA_HEHC_2024),
    ),
    # -- TEMPERATURE ------------------------------------------------------
    HighEnergyCue(
        key="temperature_at_or_above_65c",
        energy_source=EnergySource.TEMPERATURE,
        label="Substance or surface at or above 65 C",
        basis=CueBasis.MEASURED_MAGNITUDE,
        threshold_value=65.0,
        threshold_unit="C",
        imperial_equivalent="150 F",
        rationale=(
            "EEI HECA: substances at or above 150 degrees Fahrenheit "
            "(65.6 C) typically cause third-degree burns on two seconds of "
            "contact."
        ),
        phrases=(
            "hot oil",
            "hot surface",
            "hot bitumen",
            "molten",
            "scalded",
            "heater treater",
            "boiler",
            "exhaust manifold",
            "hot joint",
            "preheat", "hot work", "welding", "gas cutting", "cutting torch", "torch", "hot line", "burn", "spatter", "flame", "steam", "insulation was missing", "deg c",),
        citations=(EEI_HECA, EEI_SCL),
    ),
    HighEnergyCue(
        key="steam_release",
        energy_source=EnergySource.TEMPERATURE,
        label="Steam release",
        basis=CueBasis.CATEGORICAL,
        rationale=(
            "EEI SCL: any circumstance with the release of steam exceeds the "
            "high-energy threshold."
        ),
        phrases=("steam release", "steam out", "live steam", "steam leak", "steam",),
        citations=(EEI_SCL, EEI_HECA),
    ),
    HighEnergyCue(
        key="sustained_fire",
        energy_source=EnergySource.TEMPERATURE,
        label="Fire with a sustained fuel source",
        basis=CueBasis.CATEGORICAL,
        rationale=(
            "EEI HECA treats fire with a sustained source of fuel as "
            "categorically high-energy."
        ),
        phrases=(
            "caught fire",
            "fire broke out",
            "sustained fire",
            "jet fire",
            "pool fire",
            "flash fire", "fire", "ignited", "sparks", "flammable", "hydrocarbon vapour",),
        citations=(EEI_HECA, INGAA_HEHC_2024),
    ),
    HighEnergyCue(
        key="explosion",
        energy_source=EnergySource.TEMPERATURE,
        label="Explosion",
        basis=CueBasis.CATEGORICAL,
        rationale="EEI HECA: most incidents described as an explosion exceed the threshold.",
        phrases=("explosion", "exploded", "blast", "detonation", "bleve", "vapour cloud explosion", "flashback", "blew out", "blew off",),
        citations=(EEI_HECA,),
    ),
    # -- CHEMICAL ---------------------------------------------------------
    HighEnergyCue(
        key="idlh_or_corrosive_or_oxygen_deficient",
        energy_source=EnergySource.CHEMICAL,
        label="IDLH, corrosive or oxygen-deficient exposure",
        basis=CueBasis.MEASURED_MAGNITUDE,
        rationale=(
            "EEI SCL uses IDLH values published by NIOSH/CDC, plus exposures "
            "reducing oxygen below 16 percent, plus corrosive exposures at "
            "pH below 2 or above 12.5. H2S in Indian sour fields is the "
            "dominant case: IDLH is 100 ppm."
        ),
        phrases=(
            "h2s",
            "hydrogen sulphide",
            "sour gas",
            "idlh",
            "oxygen deficient",
            "oxygen below",
            "confined space",
            "toxic gas",
            "hydrochloric acid",
            "caustic",
            "corrosive",
            "ppm", "sour service", "gas release", "separator drain", "draining", "vessel", "tank", "manhole", "scba", "breathing apparatus", "atmosphere", "suffocated", "giddy", "chemical", "acid", "fumes",),
        citations=(EEI_SCL, EEI_HECA),
    ),
    # -- RADIATION --------------------------------------------------------
    HighEnergyCue(
        key="unshielded_ionising_source",
        energy_source=EnergySource.RADIATION,
        label="Unshielded or unaccounted ionising source",
        basis=CueBasis.CATEGORICAL,
        rationale=(
            "EEI SCL groups ionising radiation exposure with the "
            "categorically high-energy hazards. In pipeline and well work the "
            "governing case is industrial gamma radiography where the source "
            "fails to retract into its shielded position."
        ),
        phrases=(
            "gamma source",
            "source not retracted",
            "radiography",
            "iridium 192",
            "radioactive source",
            "survey meter",
            "collimator",
            "unshielded", "ir-192", "ndt", "exposure", "guide tube", "weld joints", "cordon", "tld",),
        citations=(EEI_SCL, INGAA_HEHC_2024),
    ),
    # -- BIOLOGICAL -------------------------------------------------------
    HighEnergyCue(
        key="envenomation_or_infectious_exposure",
        energy_source=EnergySource.BIOLOGICAL,
        label="Envenomation or life-threatening infectious exposure",
        basis=CueBasis.CATEGORICAL,
        rationale=(
            "Biological harm is not a joule quantity, so the 1,500 J test does "
            "not apply directly. prahari treats a biological exposure as "
            "high-consequence where the credible outcome is a fatality - "
            "notably venomous snakebite on remote Indian well pads, where "
            "evacuation time to antivenom is the controlling factor. This is a "
            "prahari modelling decision, flagged as such, not an EEI threshold."
        ),
        phrases=(
            "snake bite",
            "snakebite",
            "scorpion sting",
            "envenomation",
            "anaphylaxis",
            "unconscious after bite", "snake", "scorpion", "row", "vegetation", "overgrown", "valve pit", "waist high", "line walking", "bitten",),
        citations=(PRAHARI_MODELLING,),
    ),
    # -- SOUND ------------------------------------------------------------
    HighEnergyCue(
        key="impulse_or_sustained_high_noise",
        energy_source=EnergySource.SOUND,
        label="Impulse or sustained high noise",
        basis=CueBasis.MEASURED_MAGNITUDE,
        threshold_value=85.0,
        threshold_unit="dB(A)",
        rationale=(
            "Acoustic energy at occupational levels does not reach 1,500 J of "
            "mechanical energy, and hearing loss is not a SIF under most "
            "definitions. prahari carries sound for completeness of the Energy "
            "Wheel and flags it as chronic-exposure, not SIF-precursor, unless "
            "an impulse event accompanies another energy release. This is a "
            "prahari modelling decision, flagged as such."
        ),
        phrases=(
            "high noise",
            "85 db",
            "90 db",
            "impulse noise",
            "blast noise",
            "hearing loss", "noise", "compressor", "dg set", "acoustic", "ear muff", "decibel", "venting", "silencer",),
        citations=(PRAHARI_MODELLING,),
    ),
)

CUES_BY_ENERGY: dict[EnergySource, tuple[HighEnergyCue, ...]] = {
    source: tuple(c for c in HIGH_ENERGY_CUES if c.energy_source == source)
    for source in EnergySource
}

CUES_BY_KEY: dict[str, HighEnergyCue] = {c.key: c for c in HIGH_ENERGY_CUES}


@dataclass(frozen=True, slots=True)
class HighEnergyAssessment:
    """The record of whether a described hazard crossed the 1,500 J threshold.

    This is a CONTAINER, not a calculator. It is populated by the rule engine
    after it has reasoned over extracted facts; nothing in this module fills it
    in. `matched_cue_keys` and `evidence_spans` exist so the verdict remains
    traceable to the exact characters of the source report.
    """

    energy_source: EnergySource
    is_high_energy: bool
    matched_cue_keys: tuple[str, ...]
    evidence_spans: tuple[tuple[int, int], ...]
    estimated_joules: float | None = None
    threshold_joules: int = HIGH_ENERGY_THRESHOLD_JOULES
    rationale: str | None = None
