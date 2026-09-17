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

- File: **`prahari-sih26165-demo.mp4`** (this folder)
- Source project: [`../demo-video/`](../demo-video/) — `npm run render`

Re-record live UI with OBS if judges want a real click-through; Remotion covers the narrative walkthrough from verified screenshots.
