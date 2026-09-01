# prahari · web

React + Vite + TypeScript + Tailwind + Recharts. Dark, industrial, offline.

```bash
npm install
npm run dev      # http://localhost:5173  (proxies /api to :8000)
npm run build
npm run typecheck
```

The backend must be running:

```bash
cd ../backend
python -m prahari.cli seed --limit 800
uvicorn prahari.main:app --reload
```

## Four views

| Route | View | What it is for |
|---|---|---|
| `/` | **Triage Queue** | What an HSE officer opens on Monday. Uncontrolled fatal potential, ranked. Includes the **Live Analysis** panel. |
| `/reports/:id` | **Report Detail** | The pitch. Evidence spans highlighted inline, the rule trace beside them, confirm/override. |
| `/map` | **Precursor Map** | Site × activity density heatmap + the Precursor Accumulation Index with an alert banner. |
| `/rules` | **Life-Saving Rules** | Distribution across all nine, with per-rule barrier drill-down. |

## Three rules this codebase does not break

**1. There is no rule engine in the browser.** Every verdict — including the
Live Analysis panel — comes from `POST /api/analyze` or the stored verdict. A
second implementation in TypeScript would drift from the audited Python one,
and the moment it did, this UI would show a verdict the engine never produced.
That would destroy the only claim the product makes.

**2. There is no mock data and no silent fallback.** If the API is unreachable
the UI says so, loudly, and shows nothing. Putting a fabricated safety verdict
on screen — even in a demo — is a worse failure than an empty screen.

**3. Nothing is fetched from the network.** No web fonts (system stack only),
no CDN, no analytics. `npm run build` output contains no external URLs. It
renders with the network off.

## Colour

Colours are assigned by job, not taste, and validated rather than eyeballed:

- **Status** (`good` / `warning` / `serious` / `critical`) is reserved for state.
  SIF classification is a state, so it wears status colours — always paired with
  an icon or text, never colour alone.
- **Categorical** series and the three evidence-highlight hues
  (energy `#3987e5`, control `#d95926`, context `#199e70`) were run through the
  dataviz palette validator against the card surface `#131A22`: lightness band,
  chroma floor, colour-blind separation, normal-vision floor and contrast all
  pass under an all-pairs test. A first pick (magenta/violet) failed and was
  replaced.
- Each highlight hue also carries a **distinct underline style** — solid,
  dashed, dotted — so identity survives colour-blindness, print and
  forced-colours mode.

Do not substitute a hue without re-running the validator.

## Notes

- `evidence_completeness` is shown as a 4-segment meter labelled "Evidence".
  It is **not** a model confidence score — there is no probability anywhere in
  prahari. It counts how many of the four required fact slots were legible.
- `triage_rank` is a fixed table over the engine's own classes and control
  states (`backend/prahari/api/service.py`), not a learned score.
