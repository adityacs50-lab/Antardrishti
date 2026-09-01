# prahari — 90-second demo runbook

**One argument, three screens: we detect potential, not consequence.**

Everything below runs with the network off. If anything goes wrong at any
point, `make reset` restores a clean known-good state in under 10 seconds and
you start again from Step 0.

---

## Before you walk up (5 minutes, once)

```bash
make setup      # ONLY step that needs a network. Do this the night before.
make verify     # proves the offline claim. Must print PASSED.
make reset      # clean, seeded, known-good state
```

`make verify` is the one to run in the room, on the actual laptop, before the
session starts. It greps the codebase for banned imports and external URLs,
checks model checksums, then boots the stack with outbound traffic pointed at
a black hole and asserts that a real report classifies correctly. If it prints
**PASSED**, the network being off cannot break you.

Then **turn the wifi off and leave it off.** Demoing offline is the claim;
make it visibly true.

---

## Step 0 · Launch (10 seconds, before you speak)

```bash
make demo
```

The browser opens at `http://localhost:5173`. The terminal prints a banner.

> **Leave the terminal visible on a second monitor if you have one.** The
> banner states which extraction path is live and how many reports are loaded.
> It is your evidence that nothing is faked.

**Check before you start talking:**

- Terminal banner says `100% OFFLINE` and shows a report count of ~700
- Top-right of the UI shows a green **Engine online** pill
- Beside it: **Keyword fallback** or **ONNX model** — whichever is true

---

## Step 1 · The injury that is not the problem (0:00 – 0:25)

**Click path:** Landing page → **Live Analysis** panel on the right →
dropdown → **`1 · Cut finger in the workshop`**

The verdict appears as you select it.

**Expected result:**

| field | value |
|---|---|
| Classification | **Low severity** |
| Energy | low energy |
| Outcome | Minor injury |

**Say this:**

> "A fitter cut his finger. Real injury, first aid, a real entry in the safety
> log. Our system says **low severity** — because the energy involved could
> never have killed him.
>
> Every safety dashboard in the industry would rank this as an incident.
> Ours ranks it near the bottom. Watch why that matters."

*(~25 seconds. Do not linger. This slide only exists to set up the next one.)*

---

## Step 2 · The nothing that is the problem (0:25 – 1:00)

**Click path:** same dropdown → **`2 · Pumping unit guard missing, Moran`**

**Expected result:**

| field | value |
|---|---|
| Classification | **Potential SIF** |
| Energy | Mechanical · high energy |
| Control | Absent — *fixed machine guarding* |
| Life-Saving Rule | Energy Isolation |
| Evidence spans | ~20, highlighted inline |

**Say this, pointing at the highlighted text:**

> "Nobody was hurt here. Nobody was even close enough to file a report about
> an injury, because there wasn't one. This report would be closed the same
> day at almost every operator in the world.
>
> Our system says **Potential SIF** — a man was inside the guard area of a
> machine that started on its own, with the guard missing and no isolation.
> That is a fatality that happened not to occur.
>
> And look —" *(point at the colour-coded highlights)* —
> "**blue is the hazard, orange is the barrier that failed.** Every highlight
> is a character range the rule engine actually used."

**Then expand `8 rules fired — show the audit trail`:**

> "This is not a model guessing. Rule `R-CTRL-01` found the control state.
> `R-CLASS-01` looked the classification up in the Edison Electric Institute
> decision table. Each one cites a published source. A safety officer can
> disagree with a rule and go change it — you cannot disagree with a number
> that fell out of a neural network."

*(~35 seconds. This is the heart of the demo. Slow down here.)*

---

## Step 3 · The pattern nobody sees (1:00 – 1:25)

**Click path:** top nav → **Precursor Map**

A red alert banner is already on screen.

**Expected result:**

| field | value |
|---|---|
| Alert banner | 4 site–energy pairs above the escalation threshold |
| Top row | **Moran · Mechanical** — index ~39, band **HIGH**, trend **rising** |
| Badge | `same barrier ×6` |

**Click the Moran / Mechanical row to expand it.**

**Say this:**

> "The report I just pasted was at Moran. Here is Moran, before I ever
> touched it.
>
> **Fixed machine guarding, absent, six separate times in a year, at this one
> site.** Six reports. Nobody was hurt in any of them, so all six were closed.
>
> Every one of those is a report someone read and filed. What nobody could see
> is the *pattern* — because no dashboard in this industry counts the same
> barrier failing at the same place. They count injuries. There were none."

**Point at the contributor list with report IDs, dates and weights:**

> "And this number is not a black box either. Every report that contributes to
> it is listed, with its date and its decayed weight. An HSE officer can
> recompute this by hand and argue with our constants."

*(~25 seconds.)*

---

## Close (1:25 – 1:30)

> "A cut finger scored low. A near-miss with nobody hurt scored high. And the
> sixth repeat of one barrier failure at one site is now on fire.
>
> That is the whole product: **we score potential, not consequence.**"

---

## If something breaks

| Symptom | Fix |
|---|---|
| Anything at all looks wrong | `make reset` — 4-6s typically, under 10 worst case — then `make demo` |
| Browser shows *Backend unreachable* | The API died. `make reset && make demo`. **This is correct behaviour** — the UI refuses to show fabricated data rather than inventing a verdict. Say so out loud; it is a feature. |
| Port already in use | `make stop`, then `make demo` |
| Banner says `reports in db 0` | `make seed` |
| Precursor Map top row is not Moran | You seeded fewer than 700 reports. `unset PRAHARI_SEED_LIMIT && make reset` |
| A verdict is not what this doc says | You edited the lexicon. `git stash && make reset` |

**If a judge asks you to paste their own report:** let them. Type it into the
textarea directly. It will classify. If it comes back
*Insufficient information*, that is the honest answer for a two-line report —
say so, do not apologise for it. Guessing would be the defect.

---

## Questions you will be asked

**"Is this actually offline?"**
> "Run `make verify` yourself. It greps our whole runtime for network imports
> and external URLs, then boots the stack with outbound traffic pointed at a
> black hole and asserts a correct verdict. The wifi is off right now."

**"Is the model running, or the fallback?"**
> "Right now, the keyword fallback — the banner says so, and so does the badge
> in the corner. We built the MuRIL LoRA pipeline; the trained weights aren't
> loaded on this machine. The important part is that it doesn't matter to the
> verdict: the model only finds spans, the rule engine decides, and swapping
> the extractor cannot change how any verdict is justified."

*(Never claim the model is running when the banner says KEYWORD. The banner is
on screen. Getting caught overstating this would cost more than the model
gains.)*

**"How accurate is it?"**
> "81% end-to-end on a held-out split of 450 reports we never tuned on. But
> accuracy is the wrong question for this system — every error is inspectable.
> You can read the rule trace and see exactly which rule went wrong. That is
> not true of a fine-tuned classifier at any accuracy."

**"Why not just fine-tune a classifier on incident severity?"**
> "Because look at Step 1 and Step 2 again. The bleeding finger and the
> uncontrolled machine. A model trained on outcome severity learns that the
> finger is worse. It is trained on exactly the wrong signal — that's the SIF
> plateau the whole industry is stuck on."

**"Where do the definitions come from?"**
> "The 1,500-joule high-energy threshold and the three-part direct-control
> test are from Edison Electric Institute's published work. The nine
> Life-Saving Rules are IOGP Report 459. The Indian upstream vocabulary is
> grounded in OISD's E&P standards. It is all in `docs/DOMAIN.md`, with the
> places we made our own judgement calls flagged as ours."
