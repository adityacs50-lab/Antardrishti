"""prahari safety-science domain model.

Pure data and types. Nothing in this package decides anything.

The split is deliberate and is the whole point of the system (see CLAUDE.md):
this package describes WHAT the safety science says - the Energy Wheel, the
1,500 J high-energy threshold, the three-part direct control test, the nine
IOGP Life-Saving Rules. A separate deterministic rule engine consumes facts
extracted from report text and applies these definitions to reach a verdict.
No model in this system ever emits a severity score.
"""

from __future__ import annotations

from prahari.domain.citations import (
    ALL_CITATIONS,
    CITATIONS_BY_KEY,
    Citation,
    SourceTier,
)
from prahari.domain.controls import (
    ALL_CONTROLS,
    CONTROLS_BY_KEY,
    DIRECT_CONTROL_TEST,
    DIRECT_CONTROLS,
    DIRECT_CONTROLS_BY_ENERGY,
    INDIRECT_CONTROLS,
    NON_PROTECTIVE_STATUSES,
    ControlClass,
    ControlDefinition,
    ControlObservation,
    ControlStatus,
    DirectControlTest,
)
from prahari.domain.energy import (
    ENERGY_SOURCES,
    EnergySource,
    EnergySourceDefinition,
)
from prahari.domain.high_energy import (
    CUES_BY_ENERGY,
    CUES_BY_KEY,
    HIGH_ENERGY_CUES,
    HIGH_ENERGY_THRESHOLD_JOULES,
    QUOTED_THRESHOLD_FOOT_POUNDS,
    CueBasis,
    HighEnergyAssessment,
    HighEnergyCue,
)
from prahari.domain.lsr import (
    LIFE_SAVING_RULES,
    LSR_BY_ENERGY,
    LifeSavingRule,
    LifeSavingRuleAssignment,
    LifeSavingRuleDefinition,
    RuleAssignmentRank,
)

__all__ = [
    # citations
    "ALL_CITATIONS",
    "CITATIONS_BY_KEY",
    "Citation",
    "SourceTier",
    # energy wheel
    "ENERGY_SOURCES",
    "EnergySource",
    "EnergySourceDefinition",
    # high energy
    "CUES_BY_ENERGY",
    "CUES_BY_KEY",
    "HIGH_ENERGY_CUES",
    "HIGH_ENERGY_THRESHOLD_JOULES",
    "QUOTED_THRESHOLD_FOOT_POUNDS",
    "CueBasis",
    "HighEnergyAssessment",
    "HighEnergyCue",
    # controls
    "ALL_CONTROLS",
    "CONTROLS_BY_KEY",
    "DIRECT_CONTROLS",
    "DIRECT_CONTROLS_BY_ENERGY",
    "DIRECT_CONTROL_TEST",
    "INDIRECT_CONTROLS",
    "NON_PROTECTIVE_STATUSES",
    "ControlClass",
    "ControlDefinition",
    "ControlObservation",
    "ControlStatus",
    "DirectControlTest",
    # life-saving rules
    "LIFE_SAVING_RULES",
    "LSR_BY_ENERGY",
    "LifeSavingRule",
    "LifeSavingRuleAssignment",
    "LifeSavingRuleDefinition",
    "RuleAssignmentRank",
]
