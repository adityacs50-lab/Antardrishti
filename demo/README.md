# Demo pack — SIH26165 (prahari)

## How to record the judge video (90–120s)

1. Start the app:
   ```powershell
   cd prahari
   powershell -ExecutionPolicy Bypass -File .\scripts\demo_windows.ps1
   ```
2. Open Win+Alt+R (Xbox Game Bar) or OBS.
3. Follow spoken lines in [`../DEMO_SCRIPT_90s.md`](../DEMO_SCRIPT_90s.md).
4. Save as `prahari-sih26165-demo.mp4` in this folder.

## Screenshots (already captured)

| File | What judges see |
|------|-----------------|
| `screenshots/01-triage-thesis.png` | Thesis strip + triage queue (287 precursors) |
| `screenshots/01-triage-psif-live.png` / `05-live-analysis-psif.png` | Live Analysis → **POTENTIAL SIF** + Energy Isolation |
| `screenshots/02-precursor-map.png` | Accumulation alerts + density heatmap |
| `screenshots/03-report-detail.png` | Explainable detail (spans + rules) |
| `screenshots/04-life-saving-rules.png` | IOGP LSR distribution |

Open [`slideshow.html`](./slideshow.html) in a browser for a click-through walkthrough if you cannot record yet.

## Note on MP4

Judge video is rendered with [Remotion](https://github.com/remotion-dev/remotion):

- File: **`prahari-sih26165-demo.mp4`** (this folder) — 96 s, 1080p, narrated
- Source project: [`../demo-video/`](../demo-video/)

Every UI frame in it is a capture of the running app, taken by Playwright
against a seeded `make demo` stack — not a mockup — and every figure on screen
is read off the engine's own output. The narration is synthesised offline with
Piper from `../demo-video/narration.json`; the video is captioned throughout, so
it still reads with the sound off. Rebuild with:

```bash
make demo                              # repo root, in one terminal
cd demo-video && npm install && pip install piper-tts
npm run capture && npm run build       # in another
cp out/prahari-sih26165-demo.mp4 ../demo/
```

The narration voice is licensed **non-commercial** (CC BY-NC-SA 4.0). That
covers this submission; see [`../demo-video/README.md`](../demo-video/README.md)
for the one-line swap to a commercially usable voice.

See [`../demo-video/README.md`](../demo-video/README.md) for the scene list and
how the captures are framed and measured.

Re-record live UI with OBS if judges want an unscripted click-through.
