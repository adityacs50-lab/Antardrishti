# The prahari domain model, in plain English

This document exists so that any member of the team can defend every definition
in `backend/app/domain/` out loud, to a safety professional, without notes.

Read it before a demo. Each section says what we assert, where the number came
from, and — where it matters — what we made up ourselves. That last part is
deliberate. A safety professional will trust a system faster if it is honest
about the seams than if it presents everything with equal confidence.

**Every source cited here was retrieved and read. Nothing in this document is
recalled from memory or inferred.** Where the literature disagrees with itself,
the disagreement is written down rather than smoothed over.

---

## 0. Why the model is shaped like this

The core claim of energy-based safety is uncomfortable and well-evidenced:
**the things that injure people frequently are not the things that kill them.**
Slips, trips and hand cuts dominate incident counts. Fatalities come from a
small, distinct set of high-energy exposures. So a programme that drives down
its total recordable rate can leave its fatality exposure completely untouched.

This is the "SIF plateau", and it is why prahari does not try to predict
"riskiness" in general. It asks two specific questions of every report:

1. Was a **high-energy** source involved?
2. Was a **direct control** present and verified?

A report where the answers are *yes* and *no* is a **SIF precursor** — a
situation that could have killed someone and happened not to. That combination
is what we surface. Nothing about it requires a model to have an opinion.

---

## 1. The Energy Wheel — ten categories

**What we assert.** All hazardous energy in the workplace falls into ten
categories: gravity, motion, mechanical, electrical, pressure, temperature,
chemical, biological, radiation, sound.

**Where it comes from.** The Edison Electric Institute *Safety Classification
and Learning (SCL) Model*, Figure 4, lists exactly these ten. It is not our
taxonomy and we should not describe it as one. The energy-wheel concept is
standard across the energy-based safety literature.

**Why a wheel rather than a hazard list.** Hazard lists are endless and
site-specific; energy types are finite and physical. If you can name the energy,
you can ask what would release it and what stands in the way. Ten categories
also means an analyst can hold the whole taxonomy in their head, which matters
when the alternative is a 200-row hazard register nobody reads.

**How to defend the odd ones.** *Biological* and *sound* rarely produce SIFs in
the joule sense. We carry them anyway, because dropping two of the ten would
mean claiming a taxonomy we had quietly edited. Both are flagged in the code as
special cases (see §2.4).

> **Cited:** EEI, *Safety Classification and Learning (SCL) Model*, Figure 4 —
> "gravity, motion, mechanical, electrical, pressure, sound, radiation,
> biological, chemical, and temperature".

### Trigger phrases are ours, and they are cues, not conclusions

The Indian oilfield vocabulary attached to each energy type — `monkey board`,
`derrick floor`, `GGS`, `DG set`, `HT line`, `well kick`, `pig launcher`,
`sour gas` — is prahari's own contribution, tagged `PRAHARI_CHOICE` in the
citation registry. It is grounded in the vocabulary used by OISD's E&P
standards (the Indian upstream regulator's own words: OISD-STD-190 is literally
titled *Safety in Derrick Floor Operations*), but no published source hands you
this list. We built it.

**Say this if challenged:** a phrase match is a *fact*, not a verdict. It
records that a string appeared at specific character offsets. Whether that
means anything is decided downstream by a named rule. This is the difference
between a keyword classifier and a neuro-symbolic system, and it is the entire
architecture.

---

## 2. The high-energy threshold — 1,500 joules

**What we assert.** A hazard is *high-energy* when the energy that could be
released exceeds **1,500 joules**.

**Where it comes from.** The EEI *High-Energy Control Assessment (HECA)*,
principal author Dr. Matthew Hallowell: hazards with more than 1,500 joules of
physical energy are the ones most likely to cause a serious injury or fatality.
The threshold is empirical — derived from studying which exposures actually
produced fatal and life-altering outcomes — not from a first-principles
biomechanics argument.

**Intuition for a non-specialist.** 1,500 J is roughly the energy of an adult
falling about 1.7 metres, or of a 30 kg object dropped from 5 metres. Below it,
you get injuries. Above it, you start getting funerals.

### 2.1 The unit discrepancy — know this before someone finds it

The literature is not self-consistent about the imperial equivalent, and a
sharp safety professional may notice:

- INGAA's 2024 pipeline inventory says: *"more than 1500 Joules or
  approximately 500 ft-lb of physical energy"*.
- The EEI SCL Model text says: *"an element of work that involves more than
  500 ft-lbs of physical energy"*.
- But 500 ft·lbf is about **678 J**, and 1,500 J is about **1,106 ft·lbf**.
  These are not the same number.

**Our position:** we use **1,500 joules**, because that is the figure the
primary source (EEI HECA) uses as the definition, and because it is the number
the field consistently quotes. We record the 500 ft-lb figure in the code as
`QUOTED_THRESHOLD_FOOT_POUNDS` purely so the discrepancy is visible, and we
never compute with it.

**Say this if challenged:** "We noticed that too. The joule figure is the one
the primary source defines the threshold with, so that is what we implement,
and we've documented the inconsistency rather than picking whichever number
suited us."

### 2.2 Magnitude cues — so nobody has to compute joules in the field

Asking a safety officer to estimate joules is not workable. The literature
instead publishes observable proxies. These are implemented in
`high_energy.py`, each with its published number and rationale:

| Cue | Threshold | Source |
|---|---|---|
| Fall from elevation | **4 ft (1.2 m)**, ground to bottom of feet | EEI HECA / SCL |
| Fall (secondary cue) | **6 ft (1.8 m)** | see §2.3 |
| Suspended load | **> 500 lb (227 kg)**, raised **> 1 ft** | EEI HECA |
| Motor vehicle | **≥ 30 mph (48 km/h)** | EEI HECA |
| Mobile equipment | **any time it is in motion** (mass, not speed) | EEI HECA |
| Rotating equipment | **heavier than a powered hand tool** | EEI HECA |
| Electrical | **≥ 50 V** | EEI SCL / HECA |
| Arc flash | **any arc flash** | EEI HECA |
| Temperature | **≥ 150 °F (65.6 °C)** — 3rd-degree burns in 2 s contact | EEI HECA |
| Steam | **any release of steam** | EEI SCL |
| Fire | **any sustained fuel source** | EEI HECA |
| Explosion | **any event described as an explosion** | EEI HECA |
| Excavation | **unsupported soil > 5 ft (1.5 m)** | EEI HECA / SCL |
| Chemical | **IDLH values; O₂ < 16%; pH < 2 or > 12.5** | EEI SCL |
| Pressure vessel | **computed per case** | EEI SCL, App. 5 |

Note the shape of this table. Some cues are *measured* (a number in the text),
some are *categorical* (the literature says presence alone crosses the
threshold), and some are *computed* (the cue only flags that a calculation is
owed). The code models this distinction explicitly as `CueBasis`, because
conflating them is how you end up asserting a precision you do not have.

### 2.3 Why there are two fall-height cues

The brief specified ~1.8 m. The literature says 4 ft (1.2 m). Both are in the
code, and here is why.

- **1.2 m / 4 ft** is the EEI energy threshold, and it is the *lower*, more
  conservative trigger — it flags more reports, not fewer.
- **1.8 m / 6 ft** is the fall-protection trigger height used in construction
  practice, and it is where the arithmetic becomes unarguable: a 90 kg person
  falling 1.8 m releases about 1,590 J, comfortably over the threshold.

Keeping both means the engine can cite the strict-arithmetic cue when a report
gives a height above 1.8 m, and the conservative literature cue otherwise. We
did not silently substitute a number we preferred for the published one.

### 2.4 Where the joule test genuinely does not apply

**Biological.** Snakebite is not a joule quantity. On a remote Indian well pad
the controlling variable in a snakebite fatality is time-to-antivenom, not
energy. We treat biological exposure as high-*consequence* where the credible
outcome is death, and we tag this `PRAHARI_CHOICE` in the code. It is our
judgement, not EEI's.

**Sound.** Occupational noise does not approach 1,500 J of mechanical energy,
and noise-induced hearing loss is not a SIF under most definitions. We carry
sound to keep the wheel complete and flag it as chronic-exposure rather than
SIF-precursor. Also tagged `PRAHARI_CHOICE`.

**Say this if challenged:** "Two of the ten don't fit the joule test. We could
have hidden that by dropping them from the wheel. We'd rather show you exactly
where our judgement replaced the literature's."

---

## 3. Direct controls — the three-part test

**What we assert.** A control counts as a **direct control** only if *all three*
of the following hold:

- **(a) Targeted** — it is specifically targeted to the high-energy source.
- **(b) Effective when used properly** — it effectively mitigates exposure when
  installed, verified and used properly; a SIF should not occur if those
  conditions are met.
- **(c) Survives human error** — it remains effective even if there is
  unintentional human error during the work, unrelated to the installation of
  the control.

**Where it comes from.** Verbatim from EEI HECA. This is not our test.

**Limb (c) is the one that does the work.** It is the reason training is not a
control. Training is *precisely* the thing that fails when someone makes the
unintentional error that limb (c) assumes they will make. Same for signage,
same for "be careful", same for a spotter — a spotter is a human being asked to
catch human error. EEI is explicit: *"training, warning signs, rules, and
experience"* are not direct controls *"because they are susceptible to
unintentional human error."*

**Absolute vs mitigating.** EEI splits direct controls in two: *absolute*
controls eliminate the exposure entirely; *mitigating* controls reduce it below
the threshold. The code models both as `ControlClass`.

**The system caveat — worth raising before they do.** EEI notes many direct
controls are only direct *as a system*: a fall-arrest system is direct only
when the engineered anchor, lanyard, harness and a structure that can take the
arrest load are all present. A harness hanging on a hook is not a direct
control. The code records this as `requires_system`.

### 3.1 Direct controls by energy type

Drawn from EEI and, for oil & gas specifics, from INGAA's 2024 pipeline
inventory — the same model applied to pipeline construction:

| Energy | Direct controls |
|---|---|
| Gravity | Guardrail; complete fall-arrest system on an engineered anchor; secured hole cover; certified rigging with secondary braking |
| Motion | Cab protection (ROPS/FOPS, reinforced cabin, seatbelt); seatbelt + airbag + rollover frame; hard engineered barrier; cribbing/blocking |
| Mechanical | Fixed machine guarding; verified LOTO of stored mechanical energy; e-stop / torque limiter |
| Electrical | De-energisation + LOTO **proved dead**; insulated barrier or boom; equipment earthing/bonding |
| Pressure | Double block and bleed with verified zero; depressurise and verify; two **tested** well barriers (BOP/kill system); whip checks; engineered excavation support |
| Temperature | Thermal insulation barrier / welding blanket; flammable isolation + **continuous** gas monitoring; fixed fire detection and suppression |
| Chemical | Engineered forced ventilation; supplied-air BA as a system; positive isolation and purge |
| Radiation | Built-in source shielding, collimator, mechanical failsafe; survey-meter verification of retraction; welding screen |
| Biological | Physical exclusion (cleared vegetation, sealed enclosures); on-site antivenom + tested evacuation |
| Sound | Acoustic enclosure / attenuation **at source** |

### 3.2 Indirect controls — never count these

Explicitly **not** direct controls. Implemented, tested and locked:

training and competency certificates · toolbox talks, TBTs, pre-job meetings
and JSAs · signage and warning boards · a permit as paperwork without verified
physical isolation · supervision and observation programmes · spotters,
banksmen and flagmen · exclusion zones, barricade tape and soft fencing ·
written procedures and SOPs · general-purpose PPE (hard hat, gloves, boots,
coveralls) · experience, vigilance and "be careful" · reverse alarms and
cameras · taglines.

INGAA states this directly: pre-job meetings, JSAs and observation programmes
*"facilitate or enable the effective deployment and use of controls but do not
meet the definition of Direct Controls"*, and it lists spotters, signage,
cameras, reverse alarms, taglines and barricading as "Other Controls".

There is a dedicated unit test (`test_the_named_indirect_controls_are_present_and_indirect`)
that fails the build if any of these is ever reclassified. That is on purpose:
this is the single most abusable place in the model, because reclassifying
"training" as a control would let the engine clear genuinely uncontrolled work.

### 3.3 Two nuances that will come up

**Barriers.** A *hard engineered physical barrier* is a direct control (EEI).
*Barricade tape and soft fencing* are not (INGAA's "Other Controls"). The
distinction is whether the barrier stops the energy or merely marks where it
is. Both are in the model, classified differently, deliberately.

**PPE.** The rule is that most standard non-specialised PPE is *not* direct.
But there are narrow, energy-specific exceptions the literature names
explicitly, and we implement exactly those and no more: seatbelts and airbags
(EEI names them), thermal insulated gloves and welding blankets for specific
hot tasks (INGAA), welding helmets and curtains against arc UV (INGAA), and
supplied-air respiratory protection as a monitored system. A cartridge mask in
an IDLH atmosphere is not a direct control.

### 3.4 Control status — seven states, and why

`PRESENT_VERIFIED` · `PRESENT_UNVERIFIED` · `ABSENT` · `FAILED` · `BYPASSED` ·
`NOT_FOLLOWED` · `UNKNOWN`

The important one is the split between **verified** and **unverified**. Limb
(b) of the direct-control test requires the control to be *"installed,
**verified**, and used properly"*. An isolation nobody proved dead, a BOP
nobody function-tested, a harness nobody inspected — these are not controls
yet. They are the precursor.

The code puts `PRESENT_UNVERIFIED` in `NON_PROTECTIVE_STATUSES` alongside
absent, failed, bypassed, not-followed and unknown, leaving `PRESENT_VERIFIED`
as the only protective status. That is the model's sharpest opinion, and it
follows directly from EEI's own wording.

---

## 4. The nine IOGP Life-Saving Rules

**What we assert.** Nine rules, with these official short names:

| Rule | Official short name |
|---|---|
| Bypassing Safety Controls | Obtain authorisation before overriding or disabling safety controls |
| Confined Space | Obtain authorisation before entering a confined space |
| Driving | Follow safe driving rules |
| Energy Isolation | Verify isolation and zero energy before work begins |
| Hot Work | Control flammables and ignition sources |
| Line of Fire | Keep yourself and others out of the line of fire |
| Safe Mechanical Lifting | Plan lifting operations and control the area |
| Work Authorisation | Work with a valid permit when required |
| Working at Height | Protect yourself against a fall when working at height |

**Where they come from.** IOGP *Report 459, Life-Saving Rules* (2018). The nine
simplified rules replaced an earlier set of eighteen, and were derived by
analysing 405 personal-safety fatalities reported to IOGP between 2008 and
2017, asking which rule would have prevented or mitigated each fatal outcome.
IOGP states that 376 of the fatalities in that window might have been
prevented had these rules been followed.

**Why the "I" statements are stored verbatim.** The rules are written in the
first person from the worker's perspective ("I always wear a seatbelt", "I
confirm there is an attendant standing by"). That is the wording an Indian
operating company's crew will have seen on the rig-site board. Quoting it back
in a verdict is what makes the output recognisable to the people it is about,
rather than an abstraction.

### 4.1 PRIMARY and SECONDARY — read this before claiming IOGP authority

Report 459's published methodology maps each fatality to *the* rule that would
have prevented or mitigated it. That is a **single, primary** assignment. IOGP
does **not** publish a two-tier primary/secondary scheme, and we could not find
one in the public data portal.

**SECONDARY is prahari's extension**, added to record contributing rules where
a report plainly engages more than one — a fall during a lift with no permit
engages Working at Height, Safe Mechanical Lifting and Work Authorisation at
once. It is tagged `PRAHARI_CHOICE` in the code and documented in `lsr.py`.

**Say this if challenged:** "Primary assignment mirrors IOGP's own
methodology. The secondary tier is ours — we added it because real reports
engage more than one rule, and we've labelled it as our own so nobody cites
IOGP for it."

This matters. Claiming an industry body's authority for something it did not
publish is the fastest way to lose a safety professional's trust.

### 4.2 Energy type → Life-Saving Rule

Every one of the ten energy types maps to at least one rule, and every one of
the nine rules is reachable from at least one energy type. Both properties are
enforced by tests, so the taxonomy cannot silently develop a hole.

---

## 4A. The SCL event classification - the seven classes

**What we assert.** Every report resolves to one of seven classes, decided by
four booleans: was high energy present, did a high-energy incident actually
occur, was a direct control present and effective, was a serious injury
sustained.

**Where it comes from.** The EEI SCL Model, verbatim:

| Class | SCL definition | High energy | Incident | Direct control | Serious injury |
|---|---|:--:|:--:|:--:|:--:|
| **HSIF** | "Incident with a release of high energy where a serious injury was sustained." | Y | Y | N | Y |
| **LSIF** | "Incident with a release of low energy where a serious injury was sustained." | N | - | - | Y |
| **PSIF** | "Incident with a release of high energy in the absence of a direct control where a serious injury was not sustained." | Y | Y | N | N |
| **Capacity** | "Incident with a release of high energy in the presence of a direct control where a serious injury was not sustained." | Y | Y | Y | N |
| **Exposure** | "Condition where a high-energy hazard was present without a corresponding direct control." | Y | N | N | N |
| **Success** | "Condition where a high-energy hazard was present and had a corresponding direct control." | Y | N | Y | N |
| **Low-Severity** | "Low-priority incidents ... did not result in or have the potential to result in a SIF." | N | - | - | N |

Implemented as `SCL_DECISION_TABLE` in `domain/classification.py` - a dict, not
a function. The rule engine and the data generator read the same table, so they
cannot drift apart.

### The single most important thing in this document

Look at what **Low-Severity** does. An injury that actually happened - real
blood, a real first-aid entry, maybe a lost day - is Low-Severity when the
energy was low. And **PSIF**, where nobody was scratched at all, outranks it.

That inversion is the entire argument for this project. A model trained to
predict severity from outcomes learns the opposite of the truth from that pair,
because in the training data the bleeding finger looks worse than the
unguarded 11 KV line that happened not to kill anyone that day. A deterministic
table cannot make that mistake, because it never looks at the outcome to decide
the potential.

**Say this if challenged, and lead with it in a pitch.** It is the clearest
one-sentence answer to "why not just fine-tune a classifier".

### Two combinations SCL does not enumerate

The SCL table has no row for "high energy + incident + direct control present +
serious injury". It is contradictory: had the direct control truly held, the
serious injury would not have occurred. prahari resolves it to **HSIF** and
records the reasoning in the code - the injury is itself evidence that the
control did not in fact hold. The same applies to a serious injury with no
recorded high-energy incident. Both are documented as prahari resolutions, not
as SCL rows.

### INSUFFICIENT_INFORMATION is ours

Not an SCL class. `PRAHARI_CHOICE`. Added because a large share of real
unsafe-act reports are two vague lines - "worker was careless, advised" - from
which no honest classification follows. Returning "insufficient information" is
the correct answer to those. Guessing is not, and a system that guesses on the
vague ones will be caught out by the first safety professional who reads its
output.

---

## 4B. The synthetic evaluation set

`prahari/data/` generates labelled reports so the system can be scored without
anyone hand-annotating a corpus.

**Why the labels are trustworthy.** Reports are *composed, never read back*.
The generator picks a target class, constructs a scenario spec that produces
exactly that class through `SCL_DECISION_TABLE`, and only then renders text.
The label is a property of the spec. Nothing in the generator ever looks at a
generated string and decides what it means - that would make the labels exactly
as unreliable as the model being evaluated. Every spec is re-checked against
the table after construction and generation raises if it disagrees.

**What the text looks like.** Terse, abbreviation-heavy, typo-ridden and
code-mixed across English, romanised Hindi, Devanagari, romanised Assamese and
Assamese script, set at real OIL locations (Naoholia, Baghjan, Duliajan, Moran,
Kusijan, Dikom, Jorajan, Madhuban, Tengakhat, Hebeda). The register is prahari's
own construction, tagged as such - no published corpus was copied.

**The four hard-case families**, roughly 78% of the set:

1. `high_potential_no_outcome` - PSIF and Exposure with no injury at all.
2. `visible_injury_low_potential` - Low-Severity with a real injury.
3. `underdetermined` - vague reports; labels the text cannot support are left
   **null**, because scoring a model against an unstated fact teaches it to
   guess.
4. `controlled_high_energy` - Capacity and Success, which must *not* be flagged.

**One generation rule worth knowing.** Where a control was deliberately
defeated, the generator makes **Bypassing Safety Controls** the primary
Life-Saving Rule and demotes the scenario's own rule to secondary. That is what
the rule covers, and it mirrors IOGP's "which rule, followed, would have
prevented this" logic.

---

## 4C. The extractor, the engine, and how good they actually are

### The split, in code

`prahari/ml/extractor.py` finds facts and their character offsets. It never
returns a class, a severity or a score. `prahari/rules/engine.py` consumes
those facts and applies named rules. Nothing else decides anything.

The extractor today is **rule-based, not a model**: dictionary and pattern
matching over the domain lexicons, with sentence segmentation and negation
handling. That is deliberate - it needs no download and no network, so the
stack runs disconnected right now. It is designed to be replaced by a
token-classification model exported to ONNX. Because the engine consumes facts
rather than text, swapping the extractor cannot change how a verdict is
justified. That is the entire benefit of the neuro-symbolic split, and it is
worth saying out loud in a pitch.

### Two conventions to be able to defend

**Most-degraded-wins, scoped to the sentence.** Where a report signals more
than one control state, the worst governs - "harness was inspected but he did
not tie off" is NOT_FOLLOWED, not PRESENT_VERIFIED. Optimistic resolution would
let one reassuring phrase clear a genuinely uncontrolled job. Status signals
are attributed to the control named in the *same sentence*, because report-wide
resolution let a negation anywhere condemn a control a different sentence had
verified.

**Absence of evidence is not a control.** Where high energy is established and
no direct control is mentioned, the engine records ABSENT, not "probably fine".
This is deliberately conservative: it produces false precursors, never false
clears. If a safety professional challenges the false-positive rate, that is
the answer - the asymmetry is chosen, not accidental.

### Measured performance, and what still fails

Against the held-out **test** split of the synthetic corpus (450 records the
engine has never been tuned on):

| Metric | Test | Val |
|---|---|---|
| SIF classification accuracy | **81.3%** | 82.9% |
| Control status accuracy | 68.8% | 72.3% |
| Energy source accuracy | 58.9% | 59.3% |

Per class on test: HSIF 100%, LSIF 92%, Exposure 91%, Low-Severity 86%,
Success 83%, Insufficient 80%, PSIF 63%, Capacity 56%.

**Do not oversell this.** The honest framing is that a deterministic engine with
no training reaches ~79% on a corpus built to be hard, and that every one of
its errors is inspectable - you can read the rule firings and see exactly which
rule went wrong, which is not true of a fine-tuned classifier at any accuracy.

Known weaknesses, in order of size:

1. **PSIF confused with Exposure.** The engine must decide whether energy was
   actually released or merely present, and a control clause describing the
   control giving way reads like an event. Mitigated by ignoring only the
   release markers that ARE the control-state phrase, rather than everything in
   that sentence — "the sling parted and the load dropped from 4 mtr" states
   both a control failure and a real release, and discarding the whole sentence
   mis-read a genuine PSIF as a mere Exposure. Reduced but not eliminated.
2. **Energy source at 58.9%.** The dominant-phrase heuristic picks the wrong
   Energy Wheel category when a report mentions several. This barely affects
   classification (which depends on the high-energy *boolean*), but it does
   affect the density and accumulation analytics, which key on energy type.
3. **Capacity at 56%.** Recognising a control as verified needs the right
   phrasing; a genuinely controlled job described in unusual words gets read as
   unverified. Conservative in the safe direction, but it under-counts success.
4. **A report that never states a magnitude cannot be high-energy.** "Working
   at height without a harness", with no height given, has no cue and no
   measurement, so it falls to low energy. The ONNX extractor should fix this
   by learning the hazard from context rather than from a phrase list.

### "Confidence" in the API is not a confidence score

The list endpoint accepts `min_confidence`. It filters on
`evidence_completeness`: the fraction of the four required fact slots (energy,
magnitude, control state, outcome) for which the extractor found evidence. It
measures how much of the report was legible, **not** how sure anything is that
a verdict is right. There is no probability anywhere in this system, and a test
fails the build if a severity- or score-shaped name appears in the domain.

---

## 4D. The Precursor Accumulation Index

The claim the system rests on is not "we can spot a dangerous report" - a
careful reader can do that. It is that **the same barrier failing repeatedly at
the same place** is the pattern that precedes an event, and that this pattern is
invisible in a normal incident dashboard because each report is individually
unremarkable and gets closed out on its own.

The index scores each (site, energy source) pair:

1. Only PSIF, Exposure and HSIF contribute. Capacity, Success and low-energy
   incidents add nothing.
2. Every contributor is exponentially time-decayed (45-day half life), so an
   old cluster fades.
3. Contributors are grouped by **barrier signature** = (control, control
   status). "Fall arrest absent" and "fall arrest not followed" are different
   signatures.
4. Each signature's decayed count is raised to an exponent of 1.6, so repeats
   escalate super-linearly.
5. **The strongest signature dominates and the rest are discounted to 0.35.**
   This matters: summing signatures linearly let four unrelated one-off
   failures outscore two repeats of the same barrier - the exact inversion of
   what the index claims to measure. That bug was caught by writing the claim
   down as a test (`test_repetition_outscores_variety`) before trusting it.
6. Banded (watch / elevated / high / critical) and compared against the
   previous window for direction of travel.

**The weights are not a severity model.** `CLASS_WEIGHT` assigns fixed
multipliers to classes a deterministic table produced. It is a declared,
auditable ordering over the rule layer's own output, not a severity a model
inferred from text. CLAUDE.md forbids the first, not the second.

Every score returns its contributing report ids, dates and decayed weights, so
an HSE officer can recompute it by hand and argue with the constants - which
are all declared at the top of `api/analytics.py`.

**The demo line:** at Baghjan, the antivenom stock and casualty evacuation plan
were recorded as present but unverified five separate times in a year. Nobody
was hurt in any of those five reports, so all five were closed. That is the
sixth one waiting to happen, and no severity dashboard would ever have shown it.

### Why the seeder clusters

`prahari.cli seed` gives each kind of work a home site and lands most of its
reports there. This is not demo dressing: real fields look like this, because
the same crew on the same installation makes the same mistake repeatedly. A
uniform random scatter has no repeats to find and would make the index look
useless against data that does not resemble reality. `--no-cluster` seeds a
flat scatter if you want to see the difference.

---

## 4E. Why the verdict is never overwritten

`PATCH /api/reports/{id}/review` writes a new `Review` row. The `Verdict` is
immutable - there is no endpoint that edits one, and a test asserts the
classification is unchanged after an override.

The audit question a safety professional will ask is "what did the system say
before a human touched it". A system that overwrites itself cannot answer, and
its corrections are then worthless as a training signal for the next model,
because you can no longer tell what was corrected.

---

## 5. What the model deliberately does not do

- **No severity score.** Nothing in `app/domain/` exposes a severity, score,
  risk level, probability or confidence field. There is a unit test that
  inspects `__all__` and fails the build if such a name ever appears.
- **No decisions.** Every class in this package is either an enum, a frozen
  definition, or a container the rule engine fills in. There is no logic.
- **No inference from the ML layer.** The model extracts facts and character
  spans. It never assigns an energy type as a judgement, never rates severity,
  never decides whether a control was adequate.

The reason is the design principle in `CLAUDE.md`: **every verdict must be
traceable to a named rule and the exact character spans of text that triggered
it.** A safety professional can disagree with a rule and go change it. Nobody
can disagree with a number that fell out of a neural network.

---

## 6. Sources

All retrieved and read, August 2026.

1. Edison Electric Institute — *High-Energy Control Assessments (HECA)*,
   principal author Dr. Matthew Hallowell.
   https://www.eei.org/-/media/Project/EEI/Documents/Issues-and-Policy/Power-to-Prevent-SIF/EEI-HECA.pdf
   *(1,500 J threshold; three-part direct control test; the 13 high-energy
   hazard categories and their magnitudes.)*

2. Edison Electric Institute — *Safety Classification and Learning (SCL)
   Model*.
   https://www.eei.org/-/media/Project/EEI/Documents/Issues-and-Policy/Power-to-Prevent-SIF/eeiSCLmodel.pdf
   *(Ten-category energy wheel, Figure 4; absolute vs mitigating controls;
   per-energy magnitude thresholds; the "not direct controls" list.)*

3. M. R. Hallowell — *Safety Metrics*, Professional Safety Journal (ASSP),
   May 2023, peer-reviewed.
   https://www.assp.org/docs/default-source/psj-articles/f1hallowell_0523.pdf

4. INGAA — *Pipeline Construction High-Energy Hazards and Controls Inventory*,
   July 2024.
   https://ingaa.org/wp-content/uploads/2024/11/2024_High-Energy-Hazards-and-Controls-Inventory.pdf
   *(Oil & gas application; energy-specific direct controls; the explicit
   "Other Controls" non-direct list.)*

5. IOGP — *Report 459: Life-Saving Rules*, 2018.
   https://www.iogp.org/bookstore/product/life-saving-rules/
   *(The nine rules, official short names and first-person statements.)*

6. Oil Industry Safety Directorate (India) — Exploration & Production
   standards. https://www.oisd.gov.in/en-in/Exploration_&_Production
   Used for Indian upstream vocabulary and practice:
   - OISD-STD-174 — *Well Control* (statutory under OMR 2017)
   - OISD-GDN-182 — *Safe Practices for Workover and Well Stimulation Operations*
   - OISD-STD-190 — *Safety in Derrick Floor Operations (Onshore and Offshore Drilling Rigs)*
   - OISD-STD-216 — *Electrical Safety in Onshore Drilling & Workover Rigs*
   - OISD-STD-231 — *Sucker Rod Pumping Units*
   - OISD-RP-238 — *Well Integrity*
   - OISD-GDN-226 — *Natural Gas Transmission Pipelines and City Gas Distribution Networks*

### Everything tagged as ours, in one place

Tagged `PRAHARI_CHOICE` in `citations.py`, and defensible only as our own
judgement:

- the Indian oilfield trigger-phrase vocabulary for all ten energy types;
- the SECONDARY Life-Saving Rule rank (§4.1);
- treating biological exposure as high-consequence rather than high-energy (§2.4);
- treating sound as chronic-exposure rather than SIF-precursor (§2.4);
- the biological direct controls (physical exclusion; antivenom + evacuation);
- the acoustic-enclosure direct control for sound;
- the two-tier fall-height cue (§2.3);
- the `INSUFFICIENT_INFORMATION` class (§4A);
- the resolution of the two combinations the SCL table does not enumerate (§4A);
- the entire synthetic report register and vocabulary (§4B);
- the rule that a bypassed control makes Bypassing Safety Controls the primary
  Life-Saving Rule (§4B);
- the entire v0 rule-based extractor and its lexicons (§4C);
- most-degraded-wins and absence-is-not-a-control (§4C);
- `evidence_completeness` and the `triage_rank` ordering (§4C);
- the whole Precursor Accumulation Index, its constants and its bands (§4D).
