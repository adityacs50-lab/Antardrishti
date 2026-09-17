# prahari DESIGN.md — IBM Carbon (primary)

Source: [awesome-design-md · IBM](https://github.com/voltagent/awesome-design-md/tree/main/design-md/ibm)  
Adaptation: **IBM inverse (dark) Carbon** for an OIL HSE control-room demo. White marketing Carbon washes out on projectors; inverse tokens keep enterprise gravitas.

**Hard constraints (do not violate):**
- 100% offline — **no IBM Plex download, no CDN, no analytics**
- System font stack only (match Plex weights with `system-ui` / Segoe UI)
- Status / series / cue colours in `web/src/lib/theme.ts` stay **CVD-validated** for SIF semantics
- ML never decides in the browser

---

## 1. Visual Theme & Atmosphere

- **Philosophy (Carbon):** One assertive blue. Flat-square chrome. Thin borders. **No shadows.**
- **Mood:** Enterprise trust for Oil India — calm, auditable, dense enough for triage.
- **Polarity:** Inverse canvas only (`#161616` family). Light mode is out of scope for the demo floor.
- **Signature line:** Potential ≠ severity.

## 2. Color Palette & Roles

### IBM inverse surfaces (canonical)

| Token | Hex | Role |
|-------|-----|------|
| canvas / `--bg` | `#161616` | Page plane (IBM `inverse-canvas`) |
| surface-0 | `#1c1c1c` | Sunken |
| surface-1 | `#262626` | Cards (IBM `inverse-surface-1`) |
| surface-2 | `#333333` | Raised / hover |
| border | `#393939` | Hairlines |
| border-strong | `#6f6f6f` | Strong rules |

### Ink (IBM inverse)

| Token | Hex | Role |
|-------|-----|------|
| text-1 | `#f4f4f4` | Primary (near inverse-ink) |
| text-2 | `#c6c6c6` | Secondary (IBM `inverse-ink-muted`) |
| text-3 | `#a8a8a8` | Muted / captions (projector-safe) |

### Accent — the only brand color (IBM Blue)

| Token | Hex | Role |
|-------|-----|------|
| primary / accent | `#0f62fe` | CTA, focus, active nav |
| accent-hover | `#0050e6` | Hover |
| blue-60 | `#0043ce` | Pressed / deep |

### Status (reserved — prahari safety science, not IBM marketing)

Keep `theme.ts`: good `#0ca30c`, warning `#fab219`, serious `#ec835a`, critical `#d03b3b`.  
IBM semantic green/yellow/red are **not** used for SIF badges (CVD / product continuity).

### Series & cues (do not change)

`#3987e5` / `#d95926` / `#199e70` + solid / dashed / dotted underlines.

## 3. Typography Rules

No Plex webfont. Map Carbon hierarchy to system UI:

| Role | Size | Weight | Carbon parallel |
|------|------|--------|-----------------|
| Page title | 20px | 400–600 | subhead / card-title light |
| Section | 14px | 600 | body-emphasis |
| Body | 14px | 400 | body-sm |
| Caption / badge | 12px | 400 | caption |
| Button | 14px | 400 | button |

Letter-spacing slight positive on captions (`0.02em`) like Carbon.

## 4. Component Stylings

- **Radius:** 0–4px only (Carbon `none` / `xs` / `sm`). Prefer **0–2px**.
- **Buttons:** Square. Primary fill `#0f62fe`, white label. Secondary = transparent + hairline. No pills.
- **Cards:** 1px border, **zero shadow**, header separated by hairline.
- **Nav:** Solid header (no heavy glass). Active = IBM blue **2px bottom border** + slightly raised surface.
- **Inputs:** Sunken fill, 0–2px radius, focus ring IBM blue.
- **Tags / badges:** Soft rectangle, not pills (`rounded-sm` max).

## 5. Layout Principles

- Max width ~1600px; 16–24px gutters.
- Triage: queue | live analysis on xl.
- Spacing scale: 4 / 8 / 12 / 16 / 24 / 32 / 48 (Carbon-ish).
- Hero strip: left IBM-blue edge, flat card — thesis in &lt;3s for judges.

## 6. Depth & Elevation

Carbon rule: elevation = **surface step + border**, never drop shadow.

## 7. Do's and Don'ts

**Do**
- One blue accent only for chrome/CTAs
- Pair every status colour with text/icon
- Keep extractor path + offline badge visible

**Don't**
- Load Google Fonts / IBM Plex from CDN
- Gradients, neon, cream PostHog canvas, purple Linear look
- Soft large radii / multi-layer shadows
- Client-side SIF scores

## 8. Responsive

- Collapse live analysis under queue below xl
- Touch targets ≥36px on primary actions
- Keep engine-online pill visible; hide secondary meta before md

## 9. Agent Prompt Guide

“Follow IBM Carbon inverse from `DESIGN.md`. Accent `#0f62fe` only for chrome. Surfaces `#161616` / `#262626`. Square corners 0–2px. No shadows. No CDN fonts. Keep `theme.ts` status/cue tokens.”

Quick refs: canvas `#161616`, card `#262626`, accent `#0f62fe`, critical `#d03b3b`.
