# prahari — Judges one-pager (SIH26165)

**Problem:** [SIH26165](https://sih2026.vuce.in/ps/SIH26165) — AI/NLP engine to detect **SIF precursors** in Oil India UA/UC, near-miss and incident free-text reports (Oil India Limited · Smart Automation).

**Product:** **prahari** (प्रहरी) — offline neuro-symbolic SIF precursor detection.

## What we deliver against the PS

| Requirement | Evidence in demo |
|-------------|------------------|
| Classify SIF-potential vs non-SIF | Live Analysis: cut finger → low potential; missing guard + no isolation, no injury → **PSIF** |
| Map IOGP Life-Saving Rules | Verdict + Rules view (e.g. Energy Isolation) |
| Recurring patterns (activity / location / barrier) | Precursor Map + Accumulation Index |
| Interactive dashboard | Triage · Detail · Map · LSR |
| Explainable AI | Named rules + character spans highlighted — not a black-box score |

## Architecture (one sentence)

**NLP extracts facts** (MuRIL ONNX or keyword fallback) → **deterministic rule engine decides** (EEI SCL + IOGP LSR) → every verdict is a receipt.

## Why this wins for OIL / HSE

- Ranks **what almost killed someone**, not what bled
- **100% offline** — works on field networks / air-gapped demos
- Grounded in published safety science (EEI HECA/SCL, IOGP 459, OISD vocabulary)
- Human confirm/override is **append-only** (audit trail)

## Honest metrics (say this out loud)

- Held-out accuracy on synthetic corpus, keyword path: **~83%** test
- LoRA/ONNX training is optional; demo may show **Keyword fallback** — the **rules** still decide; neural path only improves span extraction
- Corpus is **synthetic by construction** (gold labels); field vocabulary is the next widening step

## Run on Windows

```powershell
cd prahari
powershell -ExecutionPolicy Bypass -File .\scripts\demo_windows.ps1
```

Or: seed + API + Vite (see `DEMO_SCRIPT_90s.md`).

## Repo note

Canonical app: **`prahari/`**. Root-level `SIH/web/` is a legacy UI — ignore it.
