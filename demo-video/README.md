# Demo video (SIH26165)

A 96-second 1080p walkthrough of prahari, built with
[Remotion](https://github.com/remotion-dev/remotion) — programmatic React video.

**Every UI frame in the video is a capture of the real app**, driven by
Playwright against a running `make demo` stack with the seeded 700-report
database. Nothing on screen is a mockup, and every number spoken by a caption
(97.6% recall, 85.1% precision, 450 held-out reports, 1.9 ms mean, 120 potential
SIFs, index 40.4 at Moran) is read off the engine's own output, not typed into a
slide.

Output: `out/prahari-sih26165-demo.mp4`, copied to `../demo/` as the tracked
deliverable.

## Rebuilding it

```bash
# 1. In one terminal, from the repo root — the capture needs the real app.
make demo                  # API on :8000, SPA on :5173, 700 reports seeded

# 2. In another terminal.
cd demo-video
npm install
npm run capture            # drives the app, writes public/shots/*.png
npm run build              # render + encode -> out/prahari-sih26165-demo.mp4
cp out/prahari-sih26165-demo.mp4 ../demo/prahari-sih26165-demo.mp4
```

`npm run build` is `render` (Remotion → a high-bitrate master) followed by
`encode` (a web-delivery H.264: limited-range BT.709, `+faststart`, ~39 MB).

Preview while editing scenes with `npm run studio`.

### Chromium

Remotion drives Chromium through the old headless mode, which Chrome 1194+
removed from the main binary. `remotion.config.ts` therefore points the renderer
at `chrome-headless-shell`, which still implements it, if this machine has the
Playwright browser bundle. On a machine without it, drop that block or pass
`--browser-executable=<path to a Chromium that supports old headless>`.

## How the captures become video

Two details in `capture.mjs` are what let a screenshot survive being pushed into
and annotated, and they are worth keeping if you change it:

- **Shots are framed in camera.** `frameOn()` scrolls the page so the element a
  scene is about sits high in the viewport. That leaves the lower third free for
  the caption, and stops the render's push-in from running off the bottom of the
  page into empty background.
- **Shots carry measured coordinates.** Each capture records the viewport-space
  bounding box of the elements its scene points at. Those numbers live in `R` in
  `src/PrahariDemo.tsx`, so spotlights stay locked to real UI under a moving
  camera instead of being positioned by eye. `focus()` then builds a camera that
  frames a region without ever cropping it or leaving the image bounds.

If you restyle a screen, re-run `npm run capture`, check the printed boxes
against `R`, and re-render.

## Scenes

| # | Scene | Beat |
|---|-------|------|
| 1 | Cold open | *Potential ≠ severity* |
| 2 | The problem | Safety systems rank what happened |
| 3 | Triage queue | 120 potential SIFs · the measured engine numbers |
| 4 | Report A · the trap | A real injury that should score low — and does |
| 5 | Report B · the argument | Nobody hurt, and it still escalates |
| 6 | How the verdict is made | Model extracts facts → named rules decide |
| 7 | Audit trail | Nine rules, each citing a standard and its spans |
| 8 | Real field language | Hinglish in, 18 evidence spans out |
| 9 | Precursor map | One report is noise; a repeat is a pattern |
| 10 | Accumulation index | Moran · mechanical · 40.4 · CRITICAL |
| 11 | Ontology | The vocabulary, served from the engine |
| 12 | Close | Recall, precision, latency, air-gapped |

The spoken version of this runs to the same order as `../DEMO_SCRIPT_90s.md`.

## Files

```
capture.mjs          drives the running app, writes the plates
scripts/encode.mjs   master -> shareable H.264
src/PrahariDemo.tsx  the timeline: scenes, cameras, regions of interest
src/components.tsx   camera rig, spotlights, callouts, captions, type cards
src/theme.ts         palette (lifted from web/src/index.css) and font loading
public/shots/        the captured plates
public/fonts/        IBM Plex, bundled so the render needs no network
```

The video has no audio track: it is captioned throughout and is meant to play
silently on a projector.
