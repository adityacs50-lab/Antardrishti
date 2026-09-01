"""The Energy Wheel: ten categories of hazardous energy.

The ten categories are taken verbatim from the Edison Electric Institute
Safety Classification and Learning (SCL) Model, Figure 4: "gravity, motion,
mechanical, electrical, pressure, sound, radiation, biological, chemical, and
temperature".

Trigger phrases are prahari's own contribution: Indian upstream and pipeline
vernacular, drawn from the vocabulary used in OISD E&P standards and in
ONGC/OIL field practice. They are LEXICAL CUES ONLY. A phrase match is a fact
("this string appeared at these character offsets"), never a verdict. The
deterministic rule engine decides what a match means.

Pure data and types. No matching logic, no scoring, no inference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from prahari.domain.citations import (
    EEI_SCL,
    INGAA_HEHC_2024,
    OISD_GDN_182,
    OISD_GDN_226,
    OISD_RP_238,
    OISD_STD_174,
    OISD_STD_190,
    OISD_STD_216,
    OISD_STD_231,
    Citation,
    PRAHARI_MODELLING,
)


class EnergySource(str, Enum):
    """The ten Energy Wheel categories (EEI SCL Model, Figure 4)."""

    GRAVITY = "gravity"
    MOTION = "motion"
    MECHANICAL = "mechanical"
    ELECTRICAL = "electrical"
    PRESSURE = "pressure"
    TEMPERATURE = "temperature"
    CHEMICAL = "chemical"
    BIOLOGICAL = "biological"
    RADIATION = "radiation"
    SOUND = "sound"


@dataclass(frozen=True, slots=True)
class EnergySourceDefinition:
    """Everything the system knows about one Energy Wheel category.

    `trigger_phrases` are lowercase surface forms to look for in report text.
    They carry no weight and no severity - they exist so the extraction layer
    can report *where* in the text an energy type was mentioned, with exact
    character spans, for the rule engine to reason over.
    """

    source: EnergySource
    label: str
    definition: str
    trigger_phrases: tuple[str, ...]
    citations: tuple[Citation, ...] = field(default=(EEI_SCL, PRAHARI_MODELLING))


GRAVITY = EnergySourceDefinition(
    source=EnergySource.GRAVITY,
    label="Gravity",
    definition=(
        "Energy released when a person or an object falls, or when a raised or "
        "suspended mass is released. Includes falls from height, dropped "
        "objects and suspended loads."
    ),
    citations=(EEI_SCL, OISD_STD_190, PRAHARI_MODELLING),
    trigger_phrases=(
        "fell from",
        "fall from height",
        "falling from height",
        "dropped from height",
        "working at height",
        "work at height",
        "scaffold",
        "scaffolding",
        "derrick floor",
        "rig floor",
        "monkey board",
        "racking board",
        "load overhead",
        "overhead load",
        "suspended load",
        "dropped object",
        "falling object",
        "cellar pit",
        "mast",
        "substructure",
        "crown block",
        "travelling block",
        "gin pole",
        "open grating",
        "floor opening",
        "unprotected edge",
        "fall arrest",
        "tie off",
        "safety harness",
        "elevated platform",
        "pipe rack",
        "stairway",
        "ladder",
        "handrail",
        "sling", "casing lowering", "lowering", "lifting", "rigging", "shackle", "crane", "hoist", "load dropped", "winch",
    ),
)

MOTION = EnergySourceDefinition(
    source=EnergySource.MOTION,
    label="Motion",
    definition=(
        "Kinetic energy of a moving vehicle, moving mobile equipment, or a "
        "moving object striking a person. Includes struck-by, run-over, "
        "caught-between and rollover events."
    ),
    citations=(EEI_SCL, OISD_GDN_226, PRAHARI_MODELLING),
    trigger_phrases=(
        "struck by vehicle",
        "run over",
        "ran over",
        "reversing",
        "reversed into",
        "collision",
        "road traffic accident",
        "rta",
        "light vehicle",
        "crew bus",
        "tanker",
        "bowser",
        "trailer",
        "forklift",
        "mobile crane",
        "excavator",
        "dozer",
        "crawler",
        "rolled over",
        "overturned",
        "toppled",
        "skidded",
        "swinging load",
        "swung into",
        "pinned between",
        "caught between",
        "journey management",
        "over speeding",
        "overspeeding",
        "seat belt",
        "right of way",
        "row movement",
    ),
)

MECHANICAL = EnergySourceDefinition(
    source=EnergySource.MECHANICAL,
    label="Mechanical",
    definition=(
        "Energy stored or transmitted by rotating, reciprocating or spring-"
        "loaded machinery. Includes entanglement, crushing and stored "
        "mechanical energy released on disassembly."
    ),
    citations=(EEI_SCL, OISD_STD_190, OISD_STD_231, PRAHARI_MODELLING),
    trigger_phrases=(
        "rotating equipment",
        "rotary table",
        "top drive",
        "drawworks",
        "cathead",
        "spinning chain",
        "power tongs",
        "manual tongs",
        "slips",
        "elevators",
        "mud pump",
        "shale shaker",
        "centrifuge",
        "belt drive",
        "v belt",
        "coupling guard",
        "flywheel",
        "sucker rod",
        "pumping unit",
        "beam pump",
        "walking beam",
        "gearbox",
        "conveyor",
        "auger",
        "grinder wheel",
        "machine guard",
        "guard removed",
        "guard missing",
        "entangled",
        "caught in machinery",
        "pinch point",
        "nip point",
        "crushed hand",
    ),
)

ELECTRICAL = EnergySourceDefinition(
    source=EnergySource.ELECTRICAL,
    label="Electrical",
    definition=(
        "Energy from electrical potential. Includes contact with live "
        "conductors, arc flash and arc blast, and induced or stored charge."
    ),
    citations=(EEI_SCL, OISD_STD_216, PRAHARI_MODELLING),
    trigger_phrases=(
        "electric shock",
        "electrocuted",
        "electrocution",
        "live conductor",
        "live wire",
        "energised",
        "energized",
        "switchgear",
        "motor control centre",
        "mcc panel",
        "busbar",
        "transformer",
        "overhead power line",
        "overhead line",
        "ht line",
        "lt panel",
        "11 kv",
        "33 kv",
        "440 volt",
        "earthing",
        "grounding",
        "arc flash",
        "flashover",
        "short circuit",
        "loto",
        "lock out tag out",
        "electrical isolation",
        "megger",
        "dg set",
        "diesel generator",
        "cable trench",
        "junction box",
    ),
)

PRESSURE = EnergySourceDefinition(
    source=EnergySource.PRESSURE,
    label="Pressure",
    definition=(
        "Energy stored in a compressed gas, a pressurised liquid, or a "
        "pressurised well. Includes loss of well control, line rupture, "
        "trapped pressure released on breaking containment, and stored "
        "hydraulic or pneumatic energy."
    ),
    citations=(EEI_SCL, OISD_STD_174, OISD_RP_238, OISD_GDN_226, PRAHARI_MODELLING),
    trigger_phrases=(
        "pressurised line",
        "pressurized line",
        "hydro test",
        "hydrotest",
        "wellhead",
        "gas release",
        "trapped pressure",
        "residual pressure",
        "blowout",
        "well kick",
        "kick detected",
        "well control",
        "blowout preventer",
        "bop stack",
        "choke manifold",
        "kill line",
        "annulus pressure",
        "casing pressure",
        "shut in pressure",
        "gas cylinder",
        "nitrogen purge",
        "hose burst",
        "whip check",
        "pig launcher",
        "pig receiver",
        "pigging",
        "relief valve",
        "psv lifted",
        "depressurise",
        "depressurize",
        "bleed off",
        "double block and bleed",
        "accumulator",
        "koomey unit",
        "air receiver",
        "flange joint",
        "gasket failure",
    ),
)

TEMPERATURE = EnergySourceDefinition(
    source=EnergySource.TEMPERATURE,
    label="Temperature",
    definition=(
        "Thermal energy from hot or cryogenic substances and surfaces, open "
        "flame, fire and steam. Includes burns, scalds, frostbite and "
        "sustained fire."
    ),
    citations=(EEI_SCL, OISD_GDN_182, PRAHARI_MODELLING),
    trigger_phrases=(
        "hot work",
        "welding",
        "gas cutting",
        "cutting torch",
        "flare stack",
        "flaring",
        "steam out",
        "steam release",
        "live steam",
        "hot oil",
        "hot bitumen",
        "scalded",
        "burn injury",
        "thermal burn",
        "molten",
        "furnace",
        "heater treater",
        "boiler",
        "hot surface",
        "insulation removed",
        "exhaust manifold",
        "cryogenic",
        "lng",
        "frostbite",
        "fire broke out",
        "caught fire",
        "open flame",
        "spark",
        "slag",
        "preheat",
        "hot tapping",
        "heat stress",
    ),
)

CHEMICAL = EnergySourceDefinition(
    source=EnergySource.CHEMICAL,
    label="Chemical",
    definition=(
        "Energy released by chemical reaction, or harm from toxic, corrosive, "
        "flammable or asphyxiant substances. Includes hydrocarbon release, "
        "H2S exposure, corrosive contact and oxygen-deficient atmospheres."
    ),
    citations=(EEI_SCL, OISD_GDN_182, OISD_RP_238, PRAHARI_MODELLING),
    trigger_phrases=(
        "h2s",
        "hydrogen sulphide",
        "hydrogen sulfide",
        "sour gas",
        "sour service",
        "hydrochloric acid",
        "acid job",
        "caustic",
        "corrosive",
        "toxic gas",
        "toxic fumes",
        "vapour cloud",
        "asphyxiation",
        "oxygen deficient",
        "oxygen deficiency",
        "inert atmosphere",
        "nitrogen blanketing",
        "confined space entry",
        "mud chemicals",
        "barite",
        "biocide",
        "methanol",
        "condensate",
        "hydrocarbon release",
        "gas leak",
        "gas detected",
        "lel",
        "chemical splash",
        "chemical spill",
        "msds",
        "sds not available",
        "mercaptan",
        "amine",
        "glycol",
        "corrosion inhibitor",
    ),
)

BIOLOGICAL = EnergySourceDefinition(
    source=EnergySource.BIOLOGICAL,
    label="Biological",
    definition=(
        "Harm from living organisms or biologically active material. In Indian "
        "upstream field operations this is dominated by snake and scorpion "
        "envenomation on remote well pads and rights-of-way, and by "
        "contaminated water and vector exposure at remote camps."
    ),
    citations=(EEI_SCL, PRAHARI_MODELLING),
    trigger_phrases=(
        "snake bite",
        "snakebite",
        "snake",
        "scorpion sting",
        "scorpion",
        "insect bite",
        "bee sting",
        "hornet",
        "wasp nest",
        "stray dog",
        "dog bite",
        "wild animal",
        "mosquito",
        "vector borne",
        "contaminated water",
        "sewage",
        "poor sanitation",
        "food poisoning",
        "canteen hygiene",
        "legionella",
        "cooling tower water",
        "mould growth",
        "fungal",
        "needle stick",
        "sharps injury",
        "blood borne",
        "rodent",
        "vermin",
        "overgrown vegetation",
        "tall grass",
    ),
)

RADIATION = EnergySourceDefinition(
    source=EnergySource.RADIATION,
    label="Radiation",
    definition=(
        "Ionising and non-ionising radiation. In upstream and pipeline work "
        "this is dominated by industrial gamma radiography of welds, "
        "nucleonic/logging sources, NORM scale, and welding arc UV."
    ),
    citations=(EEI_SCL, INGAA_HEHC_2024, PRAHARI_MODELLING),
    trigger_phrases=(
        "radiography",
        "radiographic testing",
        "gamma source",
        "gamma exposure",
        "iridium 192",
        "ir-192",
        "radioactive source",
        "source not retracted",
        "isotope",
        "norm scale",
        "naturally occurring radioactive",
        "lsa scale",
        "nucleonic gauge",
        "density gauge",
        "logging tool",
        "neutron source",
        "aerb",
        "radiation survey",
        "survey meter",
        "dosimeter",
        "tld badge",
        "x-ray",
        "shielding",
        "collimator",
        "welding flash",
        "arc eye",
        "uv exposure",
        "laser",
        "solar radiation",
    ),
)

SOUND = EnergySourceDefinition(
    source=EnergySource.SOUND,
    label="Sound",
    definition=(
        "Acoustic energy capable of causing hearing damage, either as "
        "sustained high noise or as impulse noise. On rigs and compressor "
        "stations this is a chronic-exposure energy rather than an acute one."
    ),
    citations=(EEI_SCL, PRAHARI_MODELLING),
    trigger_phrases=(
        "high noise",
        "noise level",
        "noise exposure",
        "decibel",
        "db(a)",
        "hearing protection",
        "ear plug",
        "ear muff",
        "hearing loss",
        "noise induced hearing loss",
        "audiometry",
        "impulse noise",
        "blast noise",
        "flare noise",
        "steam venting noise",
        "psv lifting noise",
        "gas venting",
        "compressor noise",
        "turbine noise",
        "generator noise",
        "acoustic",
        "sound level meter",
        "noise survey",
        "hearing conservation",
        "jack hammer",
        "pneumatic hammer",
        "perforating gun",
    ),
)


ENERGY_SOURCES: dict[EnergySource, EnergySourceDefinition] = {
    d.source: d
    for d in (
        GRAVITY,
        MOTION,
        MECHANICAL,
        ELECTRICAL,
        PRESSURE,
        TEMPERATURE,
        CHEMICAL,
        BIOLOGICAL,
        RADIATION,
        SOUND,
    )
}
