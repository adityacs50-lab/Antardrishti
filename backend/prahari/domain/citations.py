"""Citation registry for the prahari safety-science domain model.

Every definition in this package carries a `Citation` so that a verdict, a
threshold, or a taxonomy choice can be defended to a safety professional by
pointing at a real, published source rather than at our own opinion.

Pure data. No logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SourceTier(str, Enum):
    """How much evidentiary weight a source carries.

    PEER_REVIEWED  - published in a peer-reviewed journal or an equivalent
                     scientific venue.
    INDUSTRY_STD   - a standard, recommended practice or report published by a
                     recognised industry body or regulator.
    INDUSTRY_GUIDE - a working inventory, guidance note or trade publication
                     from a recognised industry body.
    PRAHARI_CHOICE - a modelling decision made by this project. NOT an external
                     citation. Used deliberately and sparingly so that anything
                     we invented is visibly distinguishable from anything the
                     literature actually says.
    """

    PEER_REVIEWED = "peer_reviewed"
    INDUSTRY_STD = "industry_standard"
    INDUSTRY_GUIDE = "industry_guidance"
    PRAHARI_CHOICE = "prahari_modelling_choice"


@dataclass(frozen=True, slots=True)
class Citation:
    """A single traceable source."""

    key: str
    publisher: str
    title: str
    tier: SourceTier
    year: int | None = None
    identifier: str | None = None
    url: str | None = None
    note: str | None = None

    def short(self) -> str:
        """Human-readable one-liner, e.g. 'IOGP Report 459 (2018)'."""
        bits = [self.publisher]
        if self.identifier:
            bits.append(self.identifier)
        label = " ".join(bits)
        return f"{label} ({self.year})" if self.year else label


# --------------------------------------------------------------------------
# Energy-based safety / SIF science
# --------------------------------------------------------------------------

EEI_HECA = Citation(
    key="EEI_HECA",
    publisher="Edison Electric Institute",
    title="High-Energy Control Assessments (HECA)",
    tier=SourceTier.INDUSTRY_STD,
    identifier="EEI-HECA",
    url="https://www.eei.org/-/media/Project/EEI/Documents/Issues-and-Policy/Power-to-Prevent-SIF/EEI-HECA.pdf",
    note=(
        "Principal author Dr. Matthew Hallowell. Source of the 1,500 J "
        "high-energy threshold and the three-part direct control test."
    ),
)

EEI_SCL = Citation(
    key="EEI_SCL",
    publisher="Edison Electric Institute",
    title="Safety Classification and Learning (SCL) Model",
    tier=SourceTier.INDUSTRY_STD,
    identifier="EEI SCL Model",
    url="https://www.eei.org/-/media/Project/EEI/Documents/Issues-and-Policy/Power-to-Prevent-SIF/eeiSCLmodel.pdf",
    note=(
        "Source of the ten-category energy wheel and the per-energy magnitude "
        "thresholds (4 ft, 30 mph, 50 V, 150 F, 5 ft trench, 500 lb load)."
    ),
)

HALLOWELL_PSJ_2023 = Citation(
    key="HALLOWELL_PSJ_2023",
    publisher="American Society of Safety Professionals",
    title="Safety Metrics (Professional Safety Journal, peer-reviewed)",
    tier=SourceTier.PEER_REVIEWED,
    year=2023,
    url="https://www.assp.org/docs/default-source/psj-articles/f1hallowell_0523.pdf",
    note="Peer-reviewed treatment of the high-energy / direct-control model.",
)

INGAA_HEHC_2024 = Citation(
    key="INGAA_HEHC_2024",
    publisher="Interstate Natural Gas Association of America",
    title="Pipeline Construction High-Energy Hazards and Controls Inventory",
    tier=SourceTier.INDUSTRY_GUIDE,
    year=2024,
    url="https://ingaa.org/wp-content/uploads/2024/11/2024_High-Energy-Hazards-and-Controls-Inventory.pdf",
    note=(
        "Oil & gas pipeline application of the model. Source of many "
        "energy-specific direct control examples and of the explicit "
        "'Other Controls' (non-direct) list."
    ),
)

# --------------------------------------------------------------------------
# Life-Saving Rules
# --------------------------------------------------------------------------

IOGP_459 = Citation(
    key="IOGP_459",
    publisher="International Association of Oil & Gas Producers",
    title="IOGP Life-Saving Rules",
    tier=SourceTier.INDUSTRY_STD,
    year=2018,
    identifier="Report 459",
    url="https://www.iogp.org/bookstore/product/life-saving-rules/",
    note=(
        "The nine simplified Life-Saving Rules, derived from analysis of 405 "
        "personal-safety fatalities reported 2008-2017."
    ),
)

# --------------------------------------------------------------------------
# Indian upstream regulatory vocabulary
# --------------------------------------------------------------------------

OISD_STD_174 = Citation(
    key="OISD_STD_174",
    publisher="Oil Industry Safety Directorate (India)",
    title="Well Control",
    tier=SourceTier.INDUSTRY_STD,
    identifier="OISD-STD-174",
    url="https://www.oisd.gov.in/en-in/Exploration_&_Production",
    note="Statutory as included in OMR 2017. Source of Indian well-control vocabulary.",
)

OISD_STD_190 = Citation(
    key="OISD_STD_190",
    publisher="Oil Industry Safety Directorate (India)",
    title="Safety in Derrick Floor Operations (Onshore and Offshore Drilling Rigs)",
    tier=SourceTier.INDUSTRY_STD,
    identifier="OISD-STD-190",
    url="https://www.oisd.gov.in/en-in/Exploration_&_Production",
    note="Source of Indian derrick-floor and drilling-crew vocabulary.",
)

OISD_GDN_182 = Citation(
    key="OISD_GDN_182",
    publisher="Oil Industry Safety Directorate (India)",
    title="Safe Practices for Workover and Well Stimulation Operations",
    tier=SourceTier.INDUSTRY_STD,
    identifier="OISD-GDN-182",
    url="https://www.oisd.gov.in/en-in/Exploration_&_Production",
)

OISD_STD_216 = Citation(
    key="OISD_STD_216",
    publisher="Oil Industry Safety Directorate (India)",
    title="Electrical Safety in Onshore Drilling & Workover Rigs",
    tier=SourceTier.INDUSTRY_STD,
    identifier="OISD-STD-216",
    url="https://www.oisd.gov.in/en-in/Exploration_&_Production",
)

OISD_STD_231 = Citation(
    key="OISD_STD_231",
    publisher="Oil Industry Safety Directorate (India)",
    title="Sucker Rod Pumping Units",
    tier=SourceTier.INDUSTRY_STD,
    identifier="OISD-STD-231",
    url="https://www.oisd.gov.in/en-in/Exploration_&_Production",
)

OISD_RP_238 = Citation(
    key="OISD_RP_238",
    publisher="Oil Industry Safety Directorate (India)",
    title="Well Integrity",
    tier=SourceTier.INDUSTRY_STD,
    identifier="OISD-RP-238",
    url="https://www.oisd.gov.in/en-in/Exploration_&_Production",
)

OISD_GDN_226 = Citation(
    key="OISD_GDN_226",
    publisher="Oil Industry Safety Directorate (India)",
    title="Natural Gas Transmission Pipelines and City Gas Distribution Networks",
    tier=SourceTier.INDUSTRY_STD,
    identifier="OISD-GDN-226",
    url="https://www.oisd.gov.in/en-in/Exploration_&_Production",
)

# --------------------------------------------------------------------------
# Explicit modelling choices (NOT external citations)
# --------------------------------------------------------------------------

PRAHARI_MODELLING = Citation(
    key="PRAHARI_MODELLING",
    publisher="prahari",
    title="prahari modelling decision (no external source)",
    tier=SourceTier.PRAHARI_CHOICE,
    note=(
        "Marks anything this project decided rather than took from the "
        "literature - notably the Indian-vernacular trigger phrase lists and "
        "the SECONDARY Life-Saving Rule designation."
    ),
)


ALL_CITATIONS: tuple[Citation, ...] = (
    EEI_HECA,
    EEI_SCL,
    HALLOWELL_PSJ_2023,
    INGAA_HEHC_2024,
    IOGP_459,
    OISD_STD_174,
    OISD_STD_190,
    OISD_GDN_182,
    OISD_STD_216,
    OISD_STD_231,
    OISD_RP_238,
    OISD_GDN_226,
    PRAHARI_MODELLING,
)

CITATIONS_BY_KEY: dict[str, Citation] = {c.key: c for c in ALL_CITATIONS}
