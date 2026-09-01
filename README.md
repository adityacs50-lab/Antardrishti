# prahari

Offline SIF (Serious Injury & Fatality) precursor detection engine for oil &
gas safety reports.

> Status: scaffold + safety-science domain model. No detection logic implemented yet.

## What this is

prahari is a **neuro-symbolic** system for flagging SIF precursors in
free-text safety incident reports:

1. An ML fact-extraction layer (HuggingFace `transformers`, exported to ONNX,
   run via ONNX Runtime) reads report text and extracts structured facts —
   entities, attributes, character spans. It never assigns a severity, a
   risk label, or a SIF/not-SIF verdict.
2. A deterministic rule engine consumes those facts and makes the actual
   call. Every verdict is traceable to a **named rule** and the **exact
   character spans** of text that triggered it.

See [`CLAUDE.md`](./CLAUDE.md) for the full set of non-negotiable
architecture and design rules — read it before adding any code.

## Stack

- **Backend:** Python 3.11, FastAPI, SQLite (file-based)
- **ML:** HuggingFace `transformers` + ONNX Runtime, models cached in `./models`
- **Frontend:** React + Vite + TypeScript, Tailwind, Recharts

Runs entirely offline — no external API, LLM service, or cloud database
calls, ever. No authentication (demo prototype).

## Project layout

```
prahari/
├── CLAUDE.md                # non-negotiable architecture & design rules
├── docs/
│   └── DOMAIN.md            # every safety definition in plain English, cited
├── docker-compose.yml
├── docker/
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
├── models/                  # locally cached HF/ONNX models (gitignored)
├── data/                    # SQLite db + any local data (gitignored)
├── backend/
│   └── prahari/
│       ├── main.py          # FastAPI app entrypoint
│       ├── domain/           # safety science: energy wheel, 1500 J threshold,
│       │                     #   direct controls, IOGP Life-Saving Rules.
│       │                     #   Pure data and types - decides nothing.
│       ├── api/              # routers
│       ├── core/             # config, settings
│       ├── ml/               # fact-extraction layer — NEVER decides verdicts
│       ├── rules/            # deterministic rule engine — decides verdicts
│       ├── db/               # SQLAlchemy models, session
│       └── tests/
└── web/                     # React + Vite + TS frontend
    ├── package.json
    └── src/
        ├── components/ui/    # shadcn-style primitives
        ├── components/charts/
        ├── views/
        ├── lib/
        └── types/
```

## Getting started

Prerequisites: Docker and Docker Compose.

```bash
# Build and run the full stack
docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173

Local (non-Docker) development:

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Models

HuggingFace models must be downloaded once (with network access) into
`./models` before the stack can run fully offline. This step is not yet
scripted — see `models/.gitkeep`.

## The domain model

`backend/app/domain/` holds the safety science the rule engine reasons over.
It is pure data and types - enums, frozen definitions and containers. Nothing
in it decides anything.

- **Energy Wheel** - the ten hazardous-energy categories from the EEI Safety
  Classification and Learning model, each with Indian upstream and pipeline
  trigger vocabulary.
- **High-energy threshold** - 1,500 joules, per EEI's High-Energy Control
  Assessment, with the published observable cues (4 ft fall, 50 V, 65 C,
  1.5 m excavation, 30 mph, 500 lb suspended load) that imply crossing it.
- **Direct controls** - the three-part test a control must pass, plus the
  inventory of what counts as direct per energy type and the list of indirect
  controls (training, signage, permits, supervision, general PPE) that must
  never be counted as direct.
- **IOGP Life-Saving Rules** - all nine, with official short names and
  first-person statements, assignable as primary or secondary.

Every definition carries a citation to a real published source, and anything
prahari decided for itself is tagged as such rather than dressed up as
literature. [`docs/DOMAIN.md`](./docs/DOMAIN.md) explains each definition in
plain English so it can be defended verbally to a safety professional.

```bash
cd backend && python -m pytest tests -q
```

## The labelled evaluation set

`backend/prahari/data/` generates realistic OIL unsafe-act, unsafe-condition
and near-miss reports with ground-truth labels attached - a scored evaluation
set with zero manual annotation.

Reports are **composed, never read back**. The generator picks a target SCL
class, constructs a scenario spec that yields exactly that class through the
published decision table, and only then renders text. The labels are a property
of the spec, so they cannot be wrong in the way hand-annotation is wrong.

```bash
python -m prahari.data.generator --n 3000 --seed 42
python -m prahari.data.generator --n 20 --seed 7 --samples 20   # eyeball it
```

Output: `data/synthetic_reports.jsonl`, stratified 70/15/15 on the SIF class.

Text is written the way the field actually writes it - terse, abbreviation-heavy
(`PTW`, `LOTO`, `WAH`, `H2S`, `BOP`, `GGS`, `EPS`), typo-ridden, and code-mixed
across English, romanised Hindi (`safety belt nahi pehna tha`), Devanagari
(`गैस चेक नहीं हुआ`), romanised Assamese (`eku aghat poa nai`) and Assamese
script (`কোনো আঘাত হোৱা নাই`), across real OIL locations.

Roughly 78% of records are deliberately hard:

| Family | What it is | Why it matters |
|---|---|---|
| `high_potential_no_outcome` | Fatal potential, nobody scratched | A severity model scores these ~0. They are the whole point. |
| `visible_injury_low_potential` | Real injury, zero fatal potential | A severity model over-ranks these. Exactly backwards. |
| `underdetermined` | Two vague lines | Correct answer is to say so. Labels are left null. |
| `controlled_high_energy` | High energy, control held | Must not be flagged, or the system cries wolf. |

## The API

FastAPI + SQLite, no auth (demo prototype), no network calls anywhere - there
is a test that parses every runtime module and fails the build if a
network-capable import appears, and another that exercises every endpoint with
`socket.socket` monkeypatched to raise.

```bash
cd backend
pip install -e ".[dev]"
python -m alembic upgrade head          # migrations
python -m prahari.cli seed --limit 800  # demo data on first run
uvicorn prahari.main:app --reload       # http://localhost:8000/docs
```

| Endpoint | What it does |
|---|---|
| `POST /api/reports` | Ingest one report; runs extraction + engine; returns the verdict |
| `POST /api/reports/bulk` | JSONL or CSV upload |
| `GET /api/reports` | Paginated; filter by classification, lsr, site, energy, date range, `min_confidence` |
| `GET /api/reports/{id}` | Full detail with evidence spans for highlighting |
| `GET /api/triage` | SIF potential only, ranked by triage rank then recency |
| `GET /api/analytics/density` | Precursor density per site x activity (count and rate) |
| `GET /api/analytics/lsr` | Distribution across the nine Life-Saving Rules |
| `GET /api/analytics/barriers` | Which control fails most, where, trending |
| `GET /api/analytics/accumulation` | **Precursor Accumulation Index** |
| `PATCH /api/reports/{id}/review` | Confirm or override; correction stored separately |

### The Precursor Accumulation Index

The distinctive piece. It scores each **site x energy source** and rises when
*the same barrier failure repeats at the same place* inside a rolling window,
because that repetition - not any single report - is the pattern that precedes
an actual event.

- Only precursors and actual events contribute; controlled work adds nothing.
- Every contributor is exponentially time-decayed (45-day half life).
- Reports are grouped by **barrier signature** = (control, control status).
- Each signature's decayed count is raised to an exponent above 1, so repeats
  escalate super-linearly.
- The strongest signature dominates; unrelated failures are discounted, so
  **four failures of one barrier outscore four failures of four barriers**.
  There is a test named `test_repetition_outscores_variety` asserting exactly
  that, because linear counting would tie them and the whole claim would be
  hollow.

Every score returns its contributing report ids and decayed weights, so it can
be recomputed by hand.

### Human in the loop

`PATCH /api/reports/{id}/review` writes a **new Review row**. The verdict is
never edited or deleted. An auditor can always see what the system said before
a human touched it, and the gap between verdict and correction is the training
signal for the next model.

## The frontend

`web/` — React + Vite + TypeScript, Tailwind, Recharts, shadcn-style
primitives. Dark industrial palette, validated with the dataviz palette
validator rather than eyeballed. See [`web/README.md`](./web/README.md).

Four views: **Triage Queue** (with a Live Analysis panel that analyses pasted
text through the real API), **Report Detail** (evidence spans highlighted
inline beside the rule trace), **Precursor Map** (density heatmap + the
Accumulation Index with an alert banner), and **Life-Saving Rules**
(distribution across all nine, with per-rule barrier drill-down).

Three things it deliberately does not do: run any rule logic in the browser,
fall back to mock data when the API is down, or fetch anything from the
network.

```bash
cd web && npm install && npm run dev    # http://localhost:5173
```

## The ML extraction layer

`backend/prahari/ml/` — MuRIL (`google/muril-base-cased`) fine-tuned with LoRA
for **token classification**, tagging six span types: `ENERGY_SOURCE`,
`MAGNITUDE_CUE`, `CONTROL_MENTION`, `CONTROL_NEGATION`, `ACTIVITY`, `LOCATION`.

The model **never emits a verdict**. It finds spans; the deterministic rule
engine decides, unchanged. Swapping the extractor cannot change how a verdict
is justified — that is the point of the split, and a test enforces it.

```bash
pip install -e ".[train]"
python -m prahari.ml.training.prepare_data      # corpus -> BIO dataset
python -m prahari.ml.training.train_lora        # ~2 GPU-hours on a Colab T4
python -m prahari.ml.training.evaluate          # metrics + false-negative dossier
python -m prahari.ml.training.export_onnx       # -> models/prahari.onnx (INT8)
```

Three decisions worth knowing:

- **Labels come from the generator, not the keyword extractor.** The corpus
  emits `gold_spans` — what it knows it wrote. Training on the keyword
  extractor's own matches would produce a model that can only imitate it.
- **The threshold favours recall (0.35, not 0.5)**, and the best checkpoint is
  chosen on recall, not F1. A false positive costs one HSE review; a false
  negative costs a life. `tests/ml/test_recall_floor.py` fails below 0.90.
- **It fails closed.** No model, corrupt model, or any inference error → a
  logged warning and the keyword extractor. The demo never hard-fails.

## Demo

```bash
make setup     # once, WITH a network
make verify    # proves the offline claim — run this in the room
make demo      # build + seed + launch + open browser. No network needed.
make reset     # clean known-good state in under 10 seconds
```

[`DEMO.md`](./DEMO.md) is a 90-second runbook: exact click path, the three
reports in order, and the sentence to say at each step. The ordering is the
argument — a visible injury that scores **low**, then a report where nothing
happened that scores **high**, then the site where that same barrier has
already failed six times.

Its claims are pinned by `backend/tests/test_demo_contract.py`, so a lexicon
change that would break the runbook fails the build instead of the demo.

`scripts/verify_offline.sh` greps the runtime for banned imports and external
URLs, checks model checksums, then boots the stack with outbound traffic
pointed at a black hole and asserts a correct verdict end to end.

The API prints a startup banner — and the UI shows a badge — stating which
extraction path is live (ONNX or keyword fallback) and how many reports are
loaded, so nobody has to take a claim on trust.

## Development status

Done: scaffold, domain model, SCL taxonomy, synthetic generator with gold
spans, deterministic extractor, rule engine, full API + migrations + seed CLI,
four-view frontend, and the complete ML pipeline (data prep, LoRA training,
evaluation, ONNX/INT8 export, runtime with fallback). **326 backend tests
passing**, 3 skipping until a model is trained.

Engine accuracy on the held-out test split, keyword path: **83.3%** (84.2% val).

**335 backend tests passing**, 3 skipping until a model is trained.

Not run yet: the training itself (needs a GPU), and `docker compose up`.
