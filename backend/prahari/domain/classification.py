"""SCL event classification: the seven classes an incident can receive.

Source: Edison Electric Institute, Safety Classification and Learning (SCL)
Model. The SCL model defines seven incident and observation types, each with an
explicit decision rule over four inputs:

    high energy present?  high-energy incident occurred?
    direct control present?  serious injury sustained?

Verbatim definitions from the SCL Model:

  HSIF          "Incident with a release of high energy where a serious injury
                 was sustained."
  LSIF          "Incident with a release of low energy where a serious injury
                 was sustained."
  PSIF          "Incident with a release of high energy in the absence of a
                 direct control where a serious injury was not sustained."
  Capacity      "Incident with a release of high energy in the presence of a
                 direct control where a serious injury was not sustained."
  Exposure      "Condition where a high-energy hazard was present without a
                 corresponding direct control."
  Success       "Condition where a high-energy hazard was present and had a
                 corresponding direct control."
  Low-Severity  "Low-priority incidents ... did not result in or have the
                 potential to result in a SIF."

Why this matters for prahari
----------------------------
This taxonomy is the reason the system exists. Note what LOW_SEVERITY does: an
injury that actually happened, with real blood and a real lost day, is
LOW_SEVERITY if the energy was low. And PSIF - where nobody was hurt at all -
outranks it. A severity-ranking model trained on outcomes learns exactly the
wrong lesson from that pair. A deterministic table cannot.

Pure data and types. The decision table is data; the rule engine reads it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from prahari.domain.citations import EEI_SCL, Citation, PRAHARI_MODELLING


class SifClassification(str, Enum):
    """The seven SCL classes, plus one prahari extension.

    INSUFFICIENT_INFORMATION is NOT an SCL class. It is prahari's own, added
    because real unsafe-act reports are frequently two vague lines from which
    no honest classification follows. Returning it is the correct answer to
    "worker was careless, advised" - guessing is not.
    """

    HSIF = "hsif"
    LSIF = "lsif"
    PSIF = "psif"
    CAPACITY = "capacity"
    EXPOSURE = "exposure"
    SUCCESS = "success"
    LOW_SEVERITY = "low_severity"
    INSUFFICIENT_INFORMATION = "insufficient_information"


#: The classes that represent a serious injury or fatality that actually
#: happened.
ACTUAL_SIF_CLASSES: frozenset[SifClassification] = frozenset(
    {SifClassification.HSIF, SifClassification.LSIF}
)

#: The classes that represent uncontrolled fatal potential without the
#: outcome - the reports this whole system exists to surface. PSIF is an
#: incident that happened; EXPOSURE is a condition someone walked past.
SIF_PRECURSOR_CLASSES: frozenset[SifClassification] = frozenset(
    {SifClassification.PSIF, SifClassification.EXPOSURE}
)

#: The classes where high energy was present and a direct control held.
CONTROLLED_HIGH_ENERGY_CLASSES: frozenset[SifClassification] = frozenset(
    {SifClassification.CAPACITY, SifClassification.SUCCESS}
)


class InjuryOutcome(str, Enum):
    """What actually happened to a person, independent of energy magnitude.

    Kept deliberately separate from classification. The whole point of the SCL
    model is that these two axes are not the same axis.
    """

    NONE = "none"
    FIRST_AID = "first_aid"
    MINOR_INJURY = "minor_injury"
    SERIOUS_INJURY = "serious_injury"
    FATALITY = "fatality"


#: Outcomes that count as "serious injury sustained" for the SCL decision rule.
SERIOUS_OUTCOMES: frozenset[InjuryOutcome] = frozenset(
    {InjuryOutcome.SERIOUS_INJURY, InjuryOutcome.FATALITY}
)


class ReportKind(str, Enum):
    """The three OIL report types this system ingests.

    The distinction carries real weight in the SCL table: an UNSAFE_CONDITION
    is a condition (Exposure / Success), while an UNSAFE_ACT or NEAR_MISS
    generally involves an actual energy release event (PSIF / Capacity).
    """

    UNSAFE_ACT = "unsafe_act"
    UNSAFE_CONDITION = "unsafe_condition"
    NEAR_MISS = "near_miss"


@dataclass(frozen=True, slots=True)
class ClassificationInputs:
    """The four booleans the SCL decision table is keyed on."""

    high_energy: bool
    high_energy_incident: bool
    direct_control_effective: bool
    serious_injury: bool


#: The SCL decision table, verbatim from the model, as data.
#:
#: Key: (high_energy, high_energy_incident, direct_control_effective,
#:       serious_injury). Where the SCL table marks a field "N/A" (the
#:       low-energy rows), both values map to the same class.
SCL_DECISION_TABLE: dict[tuple[bool, bool, bool, bool], SifClassification] = {
    # High energy = NO -> the incident/control columns are N/A in the SCL table.
    **{
        (False, incident, control, True): SifClassification.LSIF
        for incident in (True, False)
        for control in (True, False)
    },
    **{
        (False, incident, control, False): SifClassification.LOW_SEVERITY
        for incident in (True, False)
        for control in (True, False)
    },
    # High energy = YES, an actual high-energy incident occurred.
    (True, True, False, True): SifClassification.HSIF,
    (True, True, False, False): SifClassification.PSIF,
    (True, True, True, False): SifClassification.CAPACITY,
    # High energy + incident + a control that held + a serious injury is a
    # contradictory state: had the direct control truly held, the injury would
    # not have occurred. The SCL table does not enumerate it. prahari resolves
    # it as HSIF - the injury is evidence the control did not in fact hold.
    (True, True, True, True): SifClassification.HSIF,
    # High energy = YES, no incident - a condition, not an event.
    (True, False, False, False): SifClassification.EXPOSURE,
    (True, False, True, False): SifClassification.SUCCESS,
    # A serious injury with no high-energy incident is contradictory; the
    # injury is itself evidence an energy release occurred.
    (True, False, False, True): SifClassification.HSIF,
    (True, False, True, True): SifClassification.HSIF,
}


@dataclass(frozen=True, slots=True)
class ClassificationDefinition:
    """One SCL class, with its verbatim definition and plain-English gloss."""

    classification: SifClassification
    label: str
    definition: str
    plain_english: str
    citations: tuple[Citation, ...] = field(default=(EEI_SCL,))


CLASSIFICATIONS: dict[SifClassification, ClassificationDefinition] = {
    SifClassification.HSIF: ClassificationDefinition(
        classification=SifClassification.HSIF,
        label="High-energy serious injury or fatality",
        definition=(
            "Incident with a release of high energy where a serious injury was "
            "sustained."
        ),
        plain_english="Someone was badly hurt or killed by a high-energy release.",
    ),
    SifClassification.LSIF: ClassificationDefinition(
        classification=SifClassification.LSIF,
        label="Low-energy serious injury or fatality",
        definition=(
            "Incident with a release of low energy where a serious injury was "
            "sustained."
        ),
        plain_english=(
            "Someone was badly hurt, but not by a high-energy source. Real and "
            "serious, but it is not the failure mode that kills crews "
            "repeatedly."
        ),
    ),
    SifClassification.PSIF: ClassificationDefinition(
        classification=SifClassification.PSIF,
        label="Potential serious injury or fatality",
        definition=(
            "Incident with a release of high energy in the absence of a direct "
            "control where a serious injury was not sustained."
        ),
        plain_english=(
            "High energy got loose with nothing adequate in its way, and by "
            "luck alone nobody was killed. This is the money case."
        ),
    ),
    SifClassification.CAPACITY: ClassificationDefinition(
        classification=SifClassification.CAPACITY,
        label="Capacity",
        definition=(
            "Incident with a release of high energy in the presence of a direct "
            "control where a serious injury was not sustained."
        ),
        plain_english=(
            "High energy got loose and the direct control did its job. This is "
            "a success worth studying, not a defect."
        ),
    ),
    SifClassification.EXPOSURE: ClassificationDefinition(
        classification=SifClassification.EXPOSURE,
        label="Exposure",
        definition=(
            "Condition where a high-energy hazard was present without a "
            "corresponding direct control."
        ),
        plain_english=(
            "Nothing happened, but a high-energy hazard was sitting there "
            "uncontrolled. The other money case."
        ),
    ),
    SifClassification.SUCCESS: ClassificationDefinition(
        classification=SifClassification.SUCCESS,
        label="Success",
        definition=(
            "Condition where a high-energy hazard was present and had a "
            "corresponding direct control."
        ),
        plain_english="The hazard was there and it was properly controlled.",
    ),
    SifClassification.LOW_SEVERITY: ClassificationDefinition(
        classification=SifClassification.LOW_SEVERITY,
        label="Low severity",
        definition=(
            "Low-priority incidents that did not result in, or have the "
            "potential to result in, a SIF."
        ),
        plain_english=(
            "No fatal potential. A cut hand or a twisted ankle lands here even "
            "though it hurt, because the energy could never have killed anyone."
        ),
    ),
    SifClassification.INSUFFICIENT_INFORMATION: ClassificationDefinition(
        classification=SifClassification.INSUFFICIENT_INFORMATION,
        label="Insufficient information",
        definition=(
            "The report does not contain enough information to determine energy "
            "magnitude or control state. Not an SCL class - a prahari addition."
        ),
        plain_english=(
            "The report says too little to judge. Saying so is the honest "
            "answer; guessing is not."
        ),
        citations=(PRAHARI_MODELLING,),
    ),
}
