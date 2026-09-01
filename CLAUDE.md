# CLAUDE.md — prahari

**prahari** is an offline SIF (Serious Injury & Fatality) precursor detection engine for oil & gas safety reports. These rules are non-negotiable. Any change that violates them should be stopped, not worked around.

## ARCHITECTURE RULES

- **100% offline.** No calls to any external API, LLM service, or cloud database, ever. No `openai`, `anthropic`, or requests-to-internet dependencies in runtime code.
- Everything must run from `docker compose up` with the network disconnected.
- **Backend:** Python 3.11, FastAPI, SQLite (file-based, in repo).
- **ML:** HuggingFace `transformers`, models cached locally in `./models`, ONNX Runtime for inference.
- **Frontend:** React + Vite + TypeScript, Tailwind, Recharts. Served locally.
- **No authentication.** This is a demo prototype.

## DESIGN PRINCIPLE (most important)

This is a **neuro-symbolic system**. The ML model **NEVER** decides whether something is a SIF precursor. The model only **EXTRACTS structured facts** from text. A **deterministic rule engine** makes the decision.

Every verdict must be traceable to a **named rule** and the **exact character spans** of text that triggered it.

If you are ever tempted to have a model output a severity score directly, **stop** — that violates the core design.

## Practical implications

- ML layer output = structured facts (entities, spans, extracted attributes). No labels like "SIF", "high risk", "severity: 3" ever come from the model.
- Rule engine layer = plain, auditable Python (or a rules DSL) that consumes structured facts and emits verdicts, each citing: the rule name/id that fired, and the exact character offsets (start, end) in the source text that satisfied the rule's conditions.
- Every verdict returned by the API must include this traceability — rule id + text spans — so a safety reviewer can verify the reasoning without trusting a black box.
- Do not add any dependency that reaches the network at runtime (this excludes `pip`/`npm` install-time tooling, which is fine).
- Do not add auth, user accounts, or session management — out of scope for this prototype.
