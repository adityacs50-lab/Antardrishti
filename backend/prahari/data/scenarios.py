"""Scenario templates for synthetic OIL report generation.

A scenario binds an activity to an energy source, the direct control that
matters for it, and the Life-Saving Rule it engages. Text clauses are grouped
by what they assert, so the generator can compose a report and know exactly
what ground truth it just wrote - the labels come from the scenario spec, never
from reading the generated text back.

Two pools:

HIGH_ENERGY_SCENARIOS  work where a release would exceed 1,500 J. These
                       produce HSIF / PSIF / CAPACITY / EXPOSURE / SUCCESS.
LOW_ENERGY_SCENARIOS   work where it would not. These produce LOW_SEVERITY and
                       LSIF, and they are the trap: several of them describe a
                       visible, bleeding, lost-time injury that is still not a
                       SIF, because the energy could never have killed anyone.

Slots available in every clause: {person} {designation} {installation}
{location} {height} {load} {voltage} {depth} {temp} {speed} {distance}
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prahari.domain.controls import ControlStatus
from prahari.domain.energy import EnergySource
from prahari.domain.lsr import LifeSavingRule as LSR


@dataclass(frozen=True, slots=True)
class Scenario:
    """One kind of work, with everything needed to write a report about it."""

    key: str
    activity: str
    energy_source: EnergySource
    is_high_energy: bool
    direct_control_key: str
    primary_lsr: LSR
    secondary_lsr: tuple[LSR, ...]
    #: How the hazard/setup is described.
    setup: tuple[str, ...]
    #: What happened when the energy actually got loose (high_energy_incident).
    incident: tuple[str, ...]
    #: An observation with no release - a condition, not an event.
    condition: tuple[str, ...]
    #: Per-status descriptions of the direct control.
    control: dict[ControlStatus, tuple[str, ...]] = field(default_factory=dict)


# Reusable control-clause fragments keyed by the control being described.
def _ctrl(
    verified: tuple[str, ...],
    unverified: tuple[str, ...],
    absent: tuple[str, ...],
    failed: tuple[str, ...],
    bypassed: tuple[str, ...],
    not_followed: tuple[str, ...],
) -> dict[ControlStatus, tuple[str, ...]]:
    return {
        ControlStatus.PRESENT_VERIFIED: verified,
        ControlStatus.PRESENT_UNVERIFIED: unverified,
        ControlStatus.ABSENT: absent,
        ControlStatus.FAILED: failed,
        ControlStatus.BYPASSED: bypassed,
        ControlStatus.NOT_FOLLOWED: not_followed,
    }


HIGH_ENERGY_SCENARIOS: tuple[Scenario, ...] = (
    # ---------------- GRAVITY ----------------
    Scenario(
        key="wah_derrick",
        activity="working at height on derrick floor / monkey board",
        energy_source=EnergySource.GRAVITY,
        is_high_energy=True,
        direct_control_key="fall_arrest_system",
        primary_lsr=LSR.WORKING_AT_HEIGHT,
        secondary_lsr=(LSR.WORK_AUTHORISATION,),
        setup=(
            "{person} ({designation}) was working at monkey board at approx {height} mtr height at {installation}",
            "{designation} {person} climbed to the monkey board for racking pipe at {installation}",
            "WAH job was in progress at derrick, height abt {height} mtr, {installation}",
        ),
        incident=(
            "he lost balance and slipped from the board",
            "his foot slipped from the grating and he fell {height} mtr",
            "he slipped while shifting position on the board",
        ),
        condition=(
            "it was observed during site round",
            "noticed by safety officer during inspection",
            "same was observed by shift in-charge",
        ),
        control=_ctrl(
            verified=(
                "full body harness was worn and double lanyard was anchored to the certified anchor point, checked by TP before start",
                "100% tie off was maintained to approved anchor point and harness was inspected before use",
            ),
            unverified=(
                "harness was worn but anchor point was not checked and no pre-use inspection record was available",
                "he was wearing harness however lanyard was hooked to a pipe, anchor point not certified",
            ),
            absent=(
                "he was not wearing safety belt",
                "no fall arrest arrangement was provided at the location",
                "harness was lying at the doghouse, not worn",
            ),
            failed=(
                "the lanyard hook opened under load and harness stitching gave way",
                "anchor point pulled out from the structure",
            ),
            bypassed=(
                "he had unhooked the lanyard to move across and did not re-hook",
                "harness was worn but hook was deliberately kept open for faster movement",
            ),
            not_followed=(
                "harness was available at site but he did not tie off",
                "fall protection was provided but not used by the workman",
            ),
        ),
    ),
    Scenario(
        key="wah_scaffold",
        activity="working from scaffold / elevated platform",
        energy_source=EnergySource.GRAVITY,
        is_high_energy=True,
        direct_control_key="guardrail",
        primary_lsr=LSR.WORKING_AT_HEIGHT,
        secondary_lsr=(LSR.BYPASSING_SAFETY_CONTROLS,),
        setup=(
            "painting job was going on from scaffold at {height} mtr height at {installation}",
            "{designation} {person} was working from scaffold platform, height {height} mtr, {location}",
            "insulation work in progress from elevated platform at {height} mtr, {installation}",
        ),
        incident=(
            "one plank tilted and he fell to the ground",
            "the platform gave way on one side",
            "he stepped back and went over the open edge",
        ),
        condition=(
            "the arrangement was observed during inspection",
            "same was noticed during scaffold inspection round",
        ),
        control=_ctrl(
            verified=(
                "scaffold was erected by trained scaffolder, guardrail and toe board provided on all sides, green tag displayed",
                "double guardrail was in place and the scaffold was inspected and tagged the same morning",
            ),
            unverified=(
                "guardrail was there but scaffold tag was not displayed and no inspection record found",
                "handrail was fitted however scaffold was not certified by competent person",
            ),
            absent=(
                "no guardrail or handrail was provided on the platform",
                "scaffold was without any edge protection",
            ),
            failed=("guardrail was fitted but it was loose and gave way under his weight",),
            bypassed=("one side of the guardrail had been removed for material shifting and not restored",),
            not_followed=("guardrail was provided but workman was leaning outside it to reach the pipe",),
        ),
    ),
    Scenario(
        key="dropped_object",
        activity="dropped object from height",
        energy_source=EnergySource.GRAVITY,
        is_high_energy=True,
        direct_control_key="hole_cover",
        primary_lsr=LSR.LINE_OF_FIRE,
        secondary_lsr=(LSR.WORKING_AT_HEIGHT,),
        setup=(
            "one pipe wrench of abt {tool_wt} kg was kept at derrick floor level near open grating at {installation}",
            "material was being shifted at {height} mtr level above the working area at {installation}",
            "tools were kept on the platform at {height} mtr at {location}",
        ),
        incident=(
            "the tool fell from {height} mtr and landed near {designation} who was standing below",
            "it dropped through the opening and hit the deck close to two workmen",
            "a spanner fell down and struck the handrail before landing at the crew's feet",
        ),
        condition=(
            "the unsecured tools were observed during the round",
            "the open floor opening was noticed by the safety officer",
        ),
        control=_ctrl(
            verified=(
                "floor opening was covered with secured steel cover and area below was barricaded, tools were tethered",
                "hole cover was bolted in place and drop zone was barricaded with hard barrier",
            ),
            unverified=(
                "a cover was placed over the opening but it was not secured or checked",
                "cover was there however nobody had verified whether it was fixed",
            ),
            absent=(
                "the floor opening was left open without any cover",
                "no tool tethering or barricading was done below",
            ),
            failed=("the cover plate slipped when the tool struck it",),
            bypassed=("hole cover had been lifted for cable pulling and left aside",),
            not_followed=("cover was available near the opening but was not placed by the crew",),
        ),
    ),
    Scenario(
        key="suspended_load",
        activity="crane / side boom lifting operation",
        energy_source=EnergySource.GRAVITY,
        is_high_energy=True,
        direct_control_key="rigging_with_secondary_retention",
        primary_lsr=LSR.SAFE_MECHANICAL_LIFTING,
        secondary_lsr=(LSR.LINE_OF_FIRE,),
        setup=(
            "casing joints of abt {load} kg were being lowered by crane at {installation}",
            "lifting of BOP stack was in progress at {installation}, load approx {load} kg",
            "pipe section was being shifted by side boom at ROW, {location}",
        ),
        incident=(
            "the sling parted and the load dropped from abt {height} mtr",
            "the load swung and struck the structure",
            "one shackle opened and the load slipped from the sling",
        ),
        condition=(
            "the rigging arrangement was observed before the lift",
            "condition of the sling was noticed during pre-lift check",
        ),
        control=_ctrl(
            verified=(
                "lift plan was in place, slings were colour coded and third party tested, secondary retention was used and exclusion zone was maintained by rigger",
                "certified slings with valid test certificate were used along with secondary braking on the winch, area was cleared",
            ),
            unverified=(
                "slings were used but colour coding was not visible and test certificate was not available at site",
                "rigging appeared adequate however no pre-lift inspection was recorded",
            ),
            absent=(
                "no secondary retention was used and slings were not certified",
                "lifting was done without any lift plan or certified rigging",
            ),
            failed=(
                "the sling parted during the lift",
                "the winch brake did not hold and load ran down",
            ),
            bypassed=("the load limiter on the crane had been overridden to complete the lift",),
            not_followed=(
                "exclusion zone was marked but {designation} entered below the suspended load",
                "two helpers were standing under the load despite barricading",
            ),
        ),
    ),
    # ---------------- MOTION ----------------
    Scenario(
        key="vehicle_row",
        activity="light vehicle movement on ROW / field road",
        energy_source=EnergySource.MOTION,
        is_high_energy=True,
        direct_control_key="vehicle_occupant_restraint",
        primary_lsr=LSR.DRIVING,
        secondary_lsr=(LSR.LINE_OF_FIRE,),
        setup=(
            "crew bus was carrying {pax} personnel from {location} to {installation} at abt {speed} kmph",
            "light vehicle was proceeding on ROW near {location} at approx {speed} kmph",
            "pickup was returning from {installation} on the field road",
        ),
        incident=(
            "the vehicle skidded on the wet road and went off the embankment",
            "it collided with a stationary tanker at the turning",
            "driver lost control and the vehicle overturned on the side slope",
        ),
        condition=(
            "the condition was observed during journey management check",
            "noticed at the gate during vehicle inspection",
        ),
        control=_ctrl(
            verified=(
                "all occupants were wearing seat belts, IVMS was functional and journey management plan was approved",
                "seat belt was worn by driver and all passengers, vehicle had valid fitness and IVMS was working",
            ),
            unverified=(
                "seat belts were available but IVMS data was not checked and journey plan was not verified",
                "driver said belt was worn however no IVMS record could be produced",
            ),
            absent=(
                "seat belts were not worn by the occupants",
                "the vehicle was not fitted with working seat belts in the rear",
            ),
            failed=("the seat belt buckle did not latch during the impact",),
            bypassed=("IVMS had been disconnected by the driver to avoid over-speed recording",),
            not_followed=("seat belt was available but driver was not wearing it",),
        ),
    ),
    Scenario(
        key="mobile_equipment",
        activity="heavy mobile equipment movement",
        energy_source=EnergySource.MOTION,
        is_high_energy=True,
        direct_control_key="cab_protection",
        primary_lsr=LSR.DRIVING,
        secondary_lsr=(LSR.LINE_OF_FIRE,),
        setup=(
            "excavator was working near the trench at {installation}",
            "dozer was moving on the ROW at {location} for site preparation",
            "forklift was shifting material at the stores yard, {location}",
        ),
        incident=(
            "while reversing, the machine came within {distance} ft of {designation} who was behind it",
            "the machine started tipping on the soft edge",
            "the swing of the boom passed just over the workman's head",
        ),
        condition=(
            "the working arrangement was observed by the supervisor",
            "same was noticed during the equipment inspection round",
        ),
        control=_ctrl(
            verified=(
                "the machine was fitted with ROPS/FOPS, operator was wearing seat restraint and a hard barrier separated the pedestrian walkway",
                "cab protection and rollover protection were in place and verified, pedestrian route was hard barricaded",
            ),
            unverified=(
                "ROPS was fitted but the seat restraint was not checked and no inspection record was available",
                "cab guard was present however its condition was not verified",
            ),
            absent=(
                "no separation was provided between the machine and the ground crew",
                "the machine had no rollover protection fitted",
            ),
            failed=("the seat restraint was found broken after the incident",),
            bypassed=("the reverse interlock had been disabled by the operator",),
            not_followed=("the operator was not wearing the seat restraint provided in the cab",),
        ),
    ),
    # ---------------- MECHANICAL ----------------
    Scenario(
        key="pumping_unit",
        activity="sucker rod pumping unit maintenance",
        energy_source=EnergySource.MECHANICAL,
        is_high_energy=True,
        direct_control_key="mechanical_loto",
        primary_lsr=LSR.ENERGY_ISOLATION,
        secondary_lsr=(LSR.LINE_OF_FIRE, LSR.BYPASSING_SAFETY_CONTROLS),
        setup=(
            "{designation} {person} went to attend the belt of pumping unit at Well No. {installation}, {location}",
            "greasing job of sucker rod pumping unit was taken up at {installation}",
            "belt changing of the pumping unit was in progress at {location}",
        ),
        incident=(
            "the unit started on auto and the walking beam moved while he was near the crank",
            "the belt caught his sleeve as the unit cycled",
            "the counterweight rotated while he was still inside the guard area",
        ),
        condition=(
            "the condition was observed during the routine round",
            "noticed by the field supervisor during inspection",
        ),
        control=_ctrl(
            verified=(
                "the unit was isolated at the panel, locked and tagged, brake applied and zero energy was verified before the job",
                "LOTO was applied by the authorised person, prime mover isolated and stored energy in the counterweight was released and checked",
            ),
            unverified=(
                "the switch was put off but no lock or tag was applied and zero energy was not verified",
                "isolation was claimed by the operator however nobody verified it at the panel",
            ),
            absent=(
                "the unit was not isolated and no LOTO was applied",
                "no energy isolation was carried out before starting the job",
            ),
            failed=("the brake did not hold and the counterweight rotated under gravity",),
            bypassed=("the auto-start timer had been left in service and the isolation switch was bridged",),
            not_followed=("LOTO kit was available at the installation but the crew did not use it",),
        ),
    ),
    Scenario(
        key="rotary_tongs",
        activity="tripping / making up connection with power tongs",
        energy_source=EnergySource.MECHANICAL,
        is_high_energy=True,
        direct_control_key="machine_guarding",
        primary_lsr=LSR.LINE_OF_FIRE,
        secondary_lsr=(LSR.BYPASSING_SAFETY_CONTROLS,),
        setup=(
            "tripping operation was going on at {installation}, power tongs in use at derrick floor",
            "making up of connection was in progress with spinning chain at {installation}",
            "{designation} {person} was operating power tongs during round trip at {location}",
        ),
        incident=(
            "the tong jaw slipped and the tong swung across the floor",
            "his glove got caught in the spinning chain",
            "the tail rope whipped back across the floor",
        ),
        condition=("the arrangement was observed by the tool pusher during the trip",),
        control=_ctrl(
            verified=(
                "tong guard was in place, snub line was properly anchored and hands-off procedure was followed with a verified stand-back position",
                "machine guard was fitted and checked and the crew maintained the hands-free position throughout",
            ),
            unverified=("guard was fitted but its fixing was not checked before the trip",),
            absent=("the tong guard was missing and no snub line was rigged",),
            failed=("the snub line anchor gave way when the tong torqued up",),
            bypassed=("the guard had been removed to speed up the connections and was not replaced",),
            not_followed=("guard was in place but the floorman kept his hand inside the danger zone",),
        ),
    ),
    # ---------------- ELECTRICAL ----------------
    Scenario(
        key="overhead_line",
        activity="working near live overhead power line",
        energy_source=EnergySource.ELECTRICAL,
        is_high_energy=True,
        direct_control_key="insulated_barrier",
        primary_lsr=LSR.ENERGY_ISOLATION,
        secondary_lsr=(LSR.WORK_AUTHORISATION, LSR.LINE_OF_FIRE),
        setup=(
            "crane was operating below the {voltage} overhead line at {installation}",
            "a {voltage} HT line was passing over the work location at {location}",
            "rig mast was being raised near the {voltage} overhead line at {installation}",
        ),
        incident=(
            "the boom came within {distance} ft of the live conductor and flashover occurred",
            "the mast touched the line and there was an arc",
            "the load line brushed against the conductor",
        ),
        condition=(
            "the proximity was observed before the lift",
            "the clearance was noticed during the pre-job walkdown",
        ),
        control=_ctrl(
            verified=(
                "the line was de-energised, isolated, locked and tested dead before the work and line cover-up was installed",
                "shutdown was taken from the grid, isolation verified and proved dead at the point of work",
            ),
            unverified=(
                "shutdown was said to be taken but the line was not proved dead at site",
                "isolation was informed over phone however no test for dead was carried out",
            ),
            absent=(
                "the line was live and no insulated barrier or clearance control was provided",
                "no isolation was taken and no goal post or line cover-up was installed",
            ),
            failed=("the insulating guard slipped from the conductor during the operation",),
            bypassed=("the crane height limiter had been overridden by the operator",),
            not_followed=("the marked no-go clearance was not maintained by the crane operator",),
        ),
    ),
    Scenario(
        key="switchgear_loto",
        activity="electrical maintenance on switchgear / MCC panel",
        energy_source=EnergySource.ELECTRICAL,
        is_high_energy=True,
        direct_control_key="electrical_isolation_verified",
        primary_lsr=LSR.ENERGY_ISOLATION,
        secondary_lsr=(LSR.WORK_AUTHORISATION,),
        setup=(
            "{designation} {person} opened the MCC panel for attending the starter at {installation}",
            "cable termination work was taken up in the {voltage} panel at {installation}",
            "maintenance of switchgear was in progress at {location} substation",
        ),
        incident=(
            "he received a shock while working inside the panel",
            "an arc occurred when the spanner bridged the busbar",
            "the feeder was found live when he touched the terminal",
        ),
        condition=(
            "the condition of the panel was observed during inspection",
            "the isolation status was checked during the safety round",
        ),
        control=_ctrl(
            verified=(
                "the feeder was isolated, racked out, locked and tagged and proved dead with a tested voltage detector before starting",
                "LOTO was applied by the authorised electrician and zero voltage was confirmed at the point of work",
            ),
            unverified=(
                "the breaker was switched off but no lock/tag was applied and the circuit was not proved dead",
                "isolation was done however the tester itself was not proved before and after",
            ),
            absent=(
                "no electrical isolation was carried out before opening the panel",
                "the panel was worked upon in live condition without any isolation",
            ),
            failed=("the isolator was found to be passing and the feeder remained live despite being switched off",),
            bypassed=("the panel interlock had been defeated to keep the adjacent feeder in service",),
            not_followed=("isolation was available but the electrician worked on an adjacent live feeder",),
        ),
    ),
    # ---------------- PRESSURE ----------------
    Scenario(
        key="wellhead_pressure",
        activity="wellhead / christmas tree job with well pressure",
        energy_source=EnergySource.PRESSURE,
        is_high_energy=True,
        direct_control_key="double_block_and_bleed",
        primary_lsr=LSR.ENERGY_ISOLATION,
        secondary_lsr=(LSR.LINE_OF_FIRE, LSR.WORK_AUTHORISATION),
        setup=(
            "gland packing of the wellhead valve was to be attended at Well {installation}, {location}",
            "job was taken up on the christmas tree at {installation} with annulus pressure showing",
            "flowline joint of the wellhead was being opened at {installation}",
        ),
        incident=(
            "on loosening the bolts, trapped pressure released and gas came out with force",
            "the joint blew out and the workman was thrown back",
            "there was a sudden gas release from the annulus",
        ),
        condition=(
            "casing pressure was observed during the routine check",
            "the pressure gauge reading was noticed during the round",
        ),
        control=_ctrl(
            verified=(
                "double block and bleed was applied, the line was bled to zero and zero pressure was confirmed at the bleed point before breaking the joint",
                "well was killed, two tested barriers were in place and zero pressure was verified before the job",
            ),
            unverified=(
                "the valve was closed but the line was not bled and zero pressure was not confirmed",
                "isolation was claimed however the bleed valve was never opened to check",
            ),
            absent=(
                "no isolation was done and the joint was opened with the well under pressure",
                "no double block and bleed arrangement was available on the line",
            ),
            failed=(
                "the master valve was passing and pressure built up again after bleeding",
                "the isolation valve did not hold and pressure was retained downstream",
            ),
            bypassed=("the PSV had been gagged to stop it lifting during the operation",),
            not_followed=("bleed procedure was in the permit but the crew broke the joint without bleeding",),
        ),
    ),
    Scenario(
        key="hydrotest",
        activity="hydrotest / pressure testing of line",
        energy_source=EnergySource.PRESSURE,
        is_high_energy=True,
        direct_control_key="excavation_support",
        primary_lsr=LSR.LINE_OF_FIRE,
        secondary_lsr=(LSR.WORK_AUTHORISATION, LSR.BYPASSING_SAFETY_CONTROLS),
        setup=(
            "hydro test of the {distance} inch pipeline section was in progress at ROW {location}",
            "pressure testing of the flowline was going on at {installation}",
            "hydrotest was being carried out on the newly laid section near {location}",
        ),
        incident=(
            "the test joint failed and the blind flange flew off",
            "the hose connection detached under pressure and whipped across the trench",
            "the end cap gave way during pressurisation",
        ),
        condition=("the test set up was observed prior to pressurisation",),
        control=_ctrl(
            verified=(
                "whip checks were fitted on all hose connections, exclusion zone was hard barricaded and pressure was monitored by a calibrated gauge",
                "test manifold was rated and certified, whip checks in place and no personnel were in the test area",
            ),
            unverified=(
                "whip checks were fitted but the pressure gauge calibration was not checked",
                "arrangement looked in order however no pre-test verification was recorded",
            ),
            absent=(
                "no whip check was provided on the hose connections",
                "no barricading or restraint was provided during the test",
            ),
            failed=("the whip check wire snapped when the hose detached",),
            bypassed=("the relief valve on the test pump had been isolated to reach the test pressure faster",),
            not_followed=("exclusion zone was marked but two workmen remained inside during pressurisation",),
        ),
    ),
    Scenario(
        key="excavation",
        activity="excavation / bell hole work",
        energy_source=EnergySource.PRESSURE,
        is_high_energy=True,
        direct_control_key="excavation_support",
        primary_lsr=LSR.WORK_AUTHORISATION,
        secondary_lsr=(LSR.LINE_OF_FIRE,),
        setup=(
            "bell hole of {depth} mtr depth was excavated for pipeline repair at ROW {location}",
            "{designation} {person} entered the trench of abt {depth} mtr depth at {installation}",
            "excavation of {depth} mtr was in progress for foundation work at {location}",
        ),
        incident=(
            "one side of the trench collapsed while he was inside",
            "soil from the edge slid down and buried him up to the waist",
            "the wall caved in near the spoil heap",
        ),
        condition=(
            "the trench was observed during inspection",
            "the excavation was noticed during the ROW round",
        ),
        control=_ctrl(
            verified=(
                "the trench was properly benched and a trench box was used, ladder access was provided and the excavation was inspected daily by the competent person",
                "sloping was done as per soil condition and shoring was installed and verified before entry",
            ),
            unverified=(
                "some sloping was done but no inspection was carried out by a competent person",
                "trench box was at site however it was not installed or checked",
            ),
            absent=(
                "the trench was vertical without any shoring, benching or sloping",
                "no excavation support was provided at {depth} mtr depth",
            ),
            failed=("the shoring gave way under the load of the spoil heap kept at the edge",),
            bypassed=("the trench box had been removed to allow the welding job and entry continued",),
            not_followed=("shoring was installed but the workman entered the unsupported end of the trench",),
        ),
    ),
    Scenario(
        key="gas_cylinder",
        activity="handling of gas cylinders",
        energy_source=EnergySource.PRESSURE,
        is_high_energy=True,
        direct_control_key="whip_check",
        primary_lsr=LSR.HOT_WORK,
        secondary_lsr=(LSR.LINE_OF_FIRE,),
        setup=(
            "oxygen and DA cylinders were being shifted at {installation}",
            "gas cutting set was rigged up at {location} with cylinders on the trolley",
            "cylinders were kept near the working area at {installation}",
        ),
        incident=(
            "one cylinder toppled and the valve struck the floor",
            "the hose detached from the regulator under pressure",
            "flashback occurred at the torch and travelled towards the hose",
        ),
        condition=("the cylinder storage arrangement was observed during the round",),
        control=_ctrl(
            verified=(
                "cylinders were secured upright in the trolley with chain, valve caps in place, flashback arrestors fitted at both ends and hoses checked",
                "cylinders were properly restrained and flashback arrestor and hose clamps were verified before the job",
            ),
            unverified=("cylinders were in the trolley but the chain and flashback arrestor were not checked",),
            absent=(
                "cylinders were kept loose in horizontal position without any restraint",
                "no flashback arrestor was fitted on the hoses",
            ),
            failed=("the hose clamp gave way and the hose came off the regulator",),
            bypassed=("the flashback arrestor had been removed as it was restricting the flow",),
            not_followed=("trolley chain was available but cylinders were not secured by the crew",),
        ),
    ),
    # ---------------- TEMPERATURE ----------------
    Scenario(
        key="hot_work",
        activity="hot work / welding in hazardous area",
        energy_source=EnergySource.TEMPERATURE,
        is_high_energy=True,
        direct_control_key="fuel_isolation_and_gas_test",
        primary_lsr=LSR.HOT_WORK,
        secondary_lsr=(LSR.WORK_AUTHORISATION,),
        setup=(
            "welding job was taken up on the flowline at {installation}, {location}",
            "hot work was in progress near the separator at GGS, {location}",
            "{designation} {person} started gas cutting on the pipe support at {installation}",
        ),
        incident=(
            "there was a flash fire when the sparks reached the hydrocarbon vapour",
            "the residual gas in the line ignited",
            "sparks fell on the oily rags below and a fire started",
        ),
        condition=(
            "the hot work arrangement was observed by the safety officer",
            "same was noticed during the permit audit",
        ),
        control=_ctrl(
            verified=(
                "the line was isolated and purged, gas test was done and continuous gas monitoring was maintained, combustibles were removed and fire watch was posted",
                "hot work permit was live, gas test showed 0% LEL and continuous monitoring plus fire watch were in place throughout",
            ),
            unverified=(
                "one gas test was done in the morning but no continuous monitoring was maintained during the job",
                "gas test was recorded on the permit however the detector calibration was not checked",
            ),
            absent=(
                "gas test was not done and no fire watch was provided",
                "no purging or isolation of the line was done before starting hot work",
            ),
            failed=("the gas detector was found defective and was reading zero throughout",),
            bypassed=("the gas detector had been switched off as it was alarming repeatedly",),
            not_followed=(
                "hot work permit conditions were not followed and combustibles were not removed from the area",
            ),
        ),
    ),
    Scenario(
        key="steam_hot_oil",
        activity="steam / hot oil line work",
        energy_source=EnergySource.TEMPERATURE,
        is_high_energy=True,
        direct_control_key="thermal_insulation_barrier",
        primary_lsr=LSR.ENERGY_ISOLATION,
        secondary_lsr=(LSR.LINE_OF_FIRE,),
        setup=(
            "steam line valve was being attended at {installation}, line temp abt {temp} deg C",
            "hot oil circulation was going on at {installation} and the joint was to be attended",
            "{designation} {person} went to attend the leak on the hot line at {location}",
        ),
        incident=(
            "steam released from the joint and he received burn on the forearm",
            "hot oil sprayed out when the joint was loosened",
            "he came in contact with the uninsulated hot surface",
        ),
        condition=("the missing insulation was observed during the round",),
        control=_ctrl(
            verified=(
                "the line was isolated, drained and cooled, insulation was intact on the adjacent sections and temperature was checked before the job",
                "thermal insulation and a physical barrier were in place and verified, line was drained and cooled to ambient",
            ),
            unverified=("line was said to be drained but temperature was not checked before the job",),
            absent=(
                "the insulation was missing from the line and no barrier was provided",
                "the line was neither drained nor cooled before starting",
            ),
            failed=("the isolation valve was passing and hot fluid continued to reach the joint",),
            bypassed=("the temperature trip had been bypassed to keep the heater in service",),
            not_followed=("insulation gloves were provided but not used while handling the hot line",),
        ),
    ),
    # ---------------- CHEMICAL ----------------
    Scenario(
        key="h2s_release",
        activity="work in sour service / H2S area",
        energy_source=EnergySource.CHEMICAL,
        is_high_energy=True,
        direct_control_key="supplied_air_respiratory_protection",
        primary_lsr=LSR.WORK_AUTHORISATION,
        secondary_lsr=(LSR.CONFINED_SPACE, LSR.ENERGY_ISOLATION),
        setup=(
            "{designation} {person} was attending the separator drain at GGS, {location}, sour service area",
            "job was going on near the sour gas line at {installation}",
            "draining of the vessel was taken up at {installation} where H2S is known to be present",
        ),
        incident=(
            "H2S was released during draining and the fixed detector alarmed at high level",
            "he felt giddy and had to be pulled out of the area by the standby man",
            "gas release occurred and the area detector went into high-high alarm",
        ),
        condition=(
            "the working arrangement in the sour area was observed",
            "the gas detection status was checked during the round",
        ),
        control=_ctrl(
            verified=(
                "personal H2S monitor was worn and bump tested, SCBA was available and checked, wind sock was visible and a standby man was posted",
                "supplied air BA was used with a trained attendant and continuous monitoring, escape sets were checked before entry",
            ),
            unverified=(
                "a personal gas monitor was worn but it was not bump tested and calibration was overdue",
                "SCBA set was kept at the location however it was not checked before the job",
            ),
            absent=(
                "no personal gas monitor or breathing apparatus was provided for the job",
                "no gas detection was available at the work location",
            ),
            failed=("the personal monitor did not alarm and was later found defective",),
            bypassed=("the fixed detector at that point had been inhibited in the DCS during the shutdown",),
            not_followed=("SCBA was available at site but the workman entered the area without wearing it",),
        ),
    ),
    Scenario(
        key="confined_space",
        activity="confined space entry into tank / vessel",
        energy_source=EnergySource.CHEMICAL,
        is_high_energy=True,
        direct_control_key="engineered_ventilation",
        primary_lsr=LSR.CONFINED_SPACE,
        secondary_lsr=(LSR.WORK_AUTHORISATION, LSR.ENERGY_ISOLATION),
        setup=(
            "cleaning of the storage tank was taken up at {installation}, {location}",
            "{designation} {person} entered the mud tank for cleaning at {installation}",
            "inspection inside the vessel was to be carried out at {location}",
        ),
        incident=(
            "he became unconscious inside and had to be rescued by the standby man",
            "oxygen level dropped inside and he felt suffocated",
            "he was found collapsed inside the tank by the attendant",
        ),
        condition=(
            "the entry arrangement was observed by the safety officer",
            "the confined space entry was noticed during the audit",
        ),
        control=_ctrl(
            verified=(
                "the vessel was isolated and blinded, forced ventilation was running, atmosphere was tested and continuously monitored, attendant was posted and rescue plan was in place with entry permit",
                "positive isolation was done, eductor ventilation was running and O2 and LEL were monitored continuously with a standby man at the manhole",
            ),
            unverified=(
                "gas test was done once before entry but no continuous monitoring or ventilation was running",
                "entry permit was issued however isolation of the inlet line was not verified",
            ),
            absent=(
                "no ventilation, no gas testing and no attendant were provided for the entry",
                "entry was made without any permit or atmosphere testing",
            ),
            failed=("the blower stopped during the job and nobody noticed",),
            bypassed=("the inlet valve had been opened by the field operator while entry was in progress",),
            not_followed=("attendant was posted but he left the manhole to attend another job",),
        ),
    ),
    # ---------------- RADIATION ----------------
    Scenario(
        key="radiography",
        activity="industrial gamma radiography of welds",
        energy_source=EnergySource.RADIATION,
        is_high_energy=True,
        direct_control_key="source_shielding_and_interlock",
        primary_lsr=LSR.WORK_AUTHORISATION,
        secondary_lsr=(LSR.LINE_OF_FIRE, LSR.BYPASSING_SAFETY_CONTROLS),
        setup=(
            "radiography of the pipeline weld joints was in progress at ROW {location} using Ir-192 source",
            "gamma radiography was being carried out at {installation} during night shift",
            "NDT crew was doing radiography of the tie-in joint at {location}",
        ),
        incident=(
            "the source did not retract fully into the camera and remained exposed",
            "the crimp came loose and the source stayed in the guide tube",
            "welding crew entered the cordoned area while the source was exposed",
        ),
        condition=(
            "the radiography arrangement was observed by the safety officer",
            "the cordoning was checked during the night round",
        ),
        control=_ctrl(
            verified=(
                "the source was fully retracted and confirmed by survey meter after each exposure, area was cordoned to the calculated boundary and radiographers wore TLD badges",
                "survey meter reading was taken after every shot and the shielded position of the source was verified before approaching",
            ),
            unverified=(
                "survey meter was available but reading was not taken after the exposure",
                "the source was assumed to be retracted without any survey meter verification",
            ),
            absent=(
                "no survey meter was used and the area was not cordoned",
                "no radiation monitoring was done during the exposure",
            ),
            failed=("the survey meter battery was dead and it showed no reading during the exposure",),
            bypassed=("the camera interlock had been defeated as the crank was jamming",),
            not_followed=("cordon was established but two welders entered inside during the exposure",),
        ),
    ),
    # ---------------- BIOLOGICAL ----------------
    Scenario(
        key="snakebite_row",
        activity="ROW / well pad work in overgrown area",
        energy_source=EnergySource.BIOLOGICAL,
        is_high_energy=True,
        direct_control_key="onsite_antivenom_and_evacuation",
        primary_lsr=LSR.WORK_AUTHORISATION,
        secondary_lsr=(LSR.CONFINED_SPACE,),
        setup=(
            "{designation} {person} was working in the overgrown ROW at {location} where grass was waist high",
            "line walking was being done at the ROW near {location} through thick vegetation",
            "valve pit at the remote well pad {installation} was full of overgrowth",
        ),
        incident=(
            "he was bitten on the ankle by a snake while stepping into the grass",
            "a snake was found inside the valve pit as he put his hand in",
            "he was bitten while clearing the vegetation by hand",
        ),
        condition=(
            "the overgrown condition of the location was observed during the round",
            "the vegetation at the well pad was noticed during inspection",
        ),
        control=_ctrl(
            verified=(
                "vegetation had been cleared, the pit was covered, gaiters were provided and anti-venom stock and a tested casualty evacuation plan were confirmed for the location",
                "the area was cleared and maintained, ambulance and anti-snake venom availability at the nearest OIL hospital was verified before the job",
            ),
            unverified=(
                "the site was said to have been cleared but nobody verified the anti-venom availability or evacuation time",
                "medevac plan existed on paper but it had never been tested for this remote location",
            ),
            absent=(
                "no vegetation clearing was done and no evacuation arrangement was available at this remote location",
                "no anti-venom or ambulance arrangement was available and the location is {distance} km from the nearest hospital",
            ),
            failed=("the ambulance was not available when called and the casualty had to be shifted by pickup",),
            bypassed=("the buddy system for remote work had been dispensed with to cover more joints in the shift",),
            not_followed=("gaiters were issued to the crew but were not worn during the line walk",),
        ),
    ),
    # ---------------- SOUND ----------------
    Scenario(
        key="compressor_noise",
        activity="work near gas compressor / DG set",
        energy_source=EnergySource.SOUND,
        is_high_energy=True,
        direct_control_key="noise_enclosure",
        primary_lsr=LSR.WORK_AUTHORISATION,
        secondary_lsr=(LSR.BYPASSING_SAFETY_CONTROLS,),
        setup=(
            "{designation} {person} was working near the gas compressor at {installation} where noise level is abt 95 dB",
            "maintenance was going on beside the DG set at {location}, noise level high",
            "crew was working in the compressor shed at {installation} for full shift",
        ),
        incident=(
            "the PSV lifted and there was a loud impulse noise close to the crew",
            "the crew remained exposed to the high noise for the entire shift",
            "gas was vented to atmosphere producing very high noise near the workmen",
        ),
        condition=(
            "the noise level at the location was observed during the survey",
            "the acoustic condition was noticed during the round",
        ),
        control=_ctrl(
            verified=(
                "acoustic enclosure was intact, noise survey was current and exposure time was limited as per the survey",
                "the silencer and acoustic hood were in place and a recent noise survey confirmed levels within limit at the working position",
            ),
            unverified=("acoustic enclosure was there but no noise survey had been done for a long time",),
            absent=(
                "the acoustic enclosure panels were missing and no noise survey was available",
                "no engineering noise control was provided at the location",
            ),
            failed=("the silencer was found damaged and noise levels were much above the survey value",),
            bypassed=("the enclosure doors had been kept open for ventilation, defeating the acoustic control",),
            not_followed=("ear muffs were provided but the crew were not wearing them",),
        ),
    ),
)


LOW_ENERGY_SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        key="hand_tool_cut",
        activity="hand tool use in workshop",
        energy_source=EnergySource.MECHANICAL,
        is_high_energy=False,
        direct_control_key="general_ppe",
        primary_lsr=LSR.LINE_OF_FIRE,
        secondary_lsr=(),
        setup=(
            "{designation} {person} was cutting GI sheet at the workshop, {location}",
            "{person} was using a hacksaw for cutting a small pipe piece at {installation}",
            "deburring of a small fitting was being done by hand file at the workshop",
        ),
        incident=(
            "the blade slipped and he sustained a cut on the left index finger",
            "the sheet edge cut his palm while handling",
            "he got a small cut on the thumb from the burr",
        ),
        condition=("the tool condition was observed at the workshop",),
        control=_ctrl(
            verified=("hand gloves were worn and the tool was in good condition",),
            unverified=("gloves were worn but the tool condition was not checked",),
            absent=("hand gloves were not worn while doing the job",),
            failed=("the glove was torn and did not protect the finger",),
            bypassed=("gloves were removed for better grip",),
            not_followed=("gloves were available at the workshop but were not used",),
        ),
    ),
    Scenario(
        key="minor_slip_ground",
        activity="movement at ground level",
        energy_source=EnergySource.GRAVITY,
        is_high_energy=False,
        direct_control_key="general_ppe",
        primary_lsr=LSR.WORKING_AT_HEIGHT,
        secondary_lsr=(),
        setup=(
            "{designation} {person} was walking near the pump house at {installation}",
            "{person} was moving across the yard at {location} after the shift",
            "crew was walking on the pathway near the office at {location}",
        ),
        incident=(
            "he slipped on the oily patch and twisted his right ankle",
            "he tripped over a hose lying across the walkway and fell on the same level",
            "he lost footing on the wet floor and sat down heavily",
        ),
        condition=("the housekeeping condition was observed during the round",),
        control=_ctrl(
            verified=("the area was well lit, housekeeping was maintained and anti-skid footwear was worn",),
            unverified=("housekeeping looked acceptable but no inspection was recorded",),
            absent=("oil spillage was lying on the walkway and there was no housekeeping arrangement",),
            failed=("the anti-skid sole of the safety shoe was worn out",),
            bypassed=("the barricading around the wet area had been removed",),
            not_followed=("the alternate walkway was marked but he took the short cut across the oily patch",),
        ),
    ),
    Scenario(
        key="manual_handling",
        activity="manual handling of light material",
        energy_source=EnergySource.MECHANICAL,
        is_high_energy=False,
        direct_control_key="training",
        primary_lsr=LSR.SAFE_MECHANICAL_LIFTING,
        secondary_lsr=(),
        setup=(
            "{designation} {person} was shifting a carton of spares at the stores, {location}",
            "{person} was lifting a small valve by hand at {installation}",
            "office files were being shifted manually at {location}",
        ),
        incident=(
            "he felt pain in the lower back while lifting",
            "he strained his shoulder while twisting with the load",
            "he sustained a minor sprain in the wrist",
        ),
        condition=("the manual handling practice was observed",),
        control=_ctrl(
            verified=("manual handling training was current and a trolley was used for the shifting",),
            unverified=("training record was not available at site",),
            absent=("no mechanical aid was provided for the shifting",),
            failed=("the trolley wheel jammed midway",),
            bypassed=("the trolley was kept aside as it was slower",),
            not_followed=("trolley was available but he lifted the item by hand",),
        ),
    ),
    Scenario(
        key="paper_cut_office",
        activity="office / administrative work",
        energy_source=EnergySource.MECHANICAL,
        is_high_energy=False,
        direct_control_key="general_ppe",
        primary_lsr=LSR.LINE_OF_FIRE,
        secondary_lsr=(),
        setup=(
            "{person} was sorting permit records at the {location} office",
            "{designation} {person} was filing documents in the HSE office at {location}",
            "{person} was handling files at the installation office, {installation}",
        ),
        incident=(
            "he sustained a paper cut on the finger",
            "he got a minor cut on the finger from the file edge",
            "the stapler pricked his finger while stapling",
        ),
        condition=("the office housekeeping was observed",),
        control=_ctrl(
            verified=("the work station was in order",),
            unverified=("no workplace assessment record was available",),
            absent=("no specific control was applicable for this activity",),
            failed=("the stapler was defective",),
            bypassed=("the guard on the paper cutter had been removed",),
            not_followed=("the paper cutter was to be used but he tore the sheet by hand",),
        ),
    ),
    Scenario(
        key="minor_chemical_splash",
        activity="handling of small quantity of chemical",
        energy_source=EnergySource.CHEMICAL,
        is_high_energy=False,
        direct_control_key="general_ppe",
        primary_lsr=LSR.LINE_OF_FIRE,
        secondary_lsr=(),
        setup=(
            "{designation} {person} was topping up battery water at {installation}",
            "{person} was decanting a small quantity of detergent at the workshop, {location}",
            "sample collection of produced water was being done at {installation}",
        ),
        incident=(
            "a small splash reached his forearm causing mild irritation",
            "a few drops fell on his hand and caused slight redness",
            "he felt mild irritation in the eye from the splash",
        ),
        condition=("the chemical handling practice was observed",),
        control=_ctrl(
            verified=("goggles and gloves were worn and the eye wash point was nearby and functional",),
            unverified=("PPE was worn but the eye wash point was not checked",),
            absent=("no goggles were worn during the decanting",),
            failed=("the eye wash bottle was found empty",),
            bypassed=("goggles were removed as they were fogging",),
            not_followed=("goggles were available at the point of use but were not worn",),
        ),
    ),
    Scenario(
        key="insect_bite_minor",
        activity="outdoor work at installation",
        energy_source=EnergySource.BIOLOGICAL,
        is_high_energy=False,
        direct_control_key="physical_exclusion_of_fauna",
        primary_lsr=LSR.WORK_AUTHORISATION,
        secondary_lsr=(),
        setup=(
            "{designation} {person} was working outdoor at {installation} in the evening",
            "crew was working near the drain at {location} in the evening hours",
            "{person} was doing gauge reading in the open at {installation}",
        ),
        incident=(
            "he got a mosquito bite and mild swelling",
            "an ant bite caused slight irritation on the leg",
            "he had a minor insect bite on the neck",
        ),
        condition=("mosquito breeding in the stagnant water was observed",),
        control=_ctrl(
            verified=("repellent was provided and stagnant water was drained regularly",),
            unverified=("fogging record was not available",),
            absent=("stagnant water was lying near the location and no fogging was being done",),
            failed=("the mesh on the window was torn",),
            bypassed=("the door of the rest shelter was kept open",),
            not_followed=("repellent was issued but not used",),
        ),
    ),
    Scenario(
        key="eye_irritation_dust",
        activity="grinding / dusty work with low energy",
        energy_source=EnergySource.MECHANICAL,
        is_high_energy=False,
        direct_control_key="general_ppe",
        primary_lsr=LSR.LINE_OF_FIRE,
        secondary_lsr=(),
        setup=(
            "{designation} {person} was doing light emery paper cleaning at the workshop, {location}",
            "{person} was sweeping the shed floor at {installation}",
            "manual cleaning of a small fitting was in progress at {location}",
        ),
        incident=(
            "dust particle entered his eye causing irritation",
            "he complained of watering in the eye due to dust",
            "a small particle went into his eye during the cleaning",
        ),
        condition=("the housekeeping and dust condition was observed",),
        control=_ctrl(
            verified=("safety goggles were worn and the area was damp swept",),
            unverified=("goggles were worn but their condition was not checked",),
            absent=("no eye protection was worn for the job",),
            failed=("the goggles were scratched and he lifted them to see clearly",),
            bypassed=("goggles were kept on the forehead during the work",),
            not_followed=("goggles were available but were not worn",),
        ),
    ),
    Scenario(
        key="minor_bruise_bump",
        activity="routine field work",
        energy_source=EnergySource.MOTION,
        is_high_energy=False,
        direct_control_key="general_ppe",
        primary_lsr=LSR.LINE_OF_FIRE,
        secondary_lsr=(),
        setup=(
            "{designation} {person} was moving inside the pump house at {installation}",
            "{person} was working in the congested area near the manifold at {location}",
            "crew was passing through the low headroom area at {installation}",
        ),
        incident=(
            "he bumped his head on the low pipe and got a minor bruise",
            "his elbow struck the valve handle causing a small bruise",
            "he knocked his shin against the pipe support",
        ),
        condition=("the low headroom and congestion was observed during the round",),
        control=_ctrl(
            verified=("the low headroom was padded and marked and helmet was worn",),
            unverified=("marking was there but its adequacy was not assessed",),
            absent=("no padding or marking was provided at the low headroom",),
            failed=("the padding had come off the pipe",),
            bypassed=("the warning marking had been painted over",),
            not_followed=("helmet was available but not worn inside the shed",),
        ),
    ),
)


ALL_SCENARIOS: tuple[Scenario, ...] = HIGH_ENERGY_SCENARIOS + LOW_ENERGY_SCENARIOS
SCENARIOS_BY_KEY: dict[str, Scenario] = {s.key: s for s in ALL_SCENARIOS}
