/**
 * Captures the screens the demo video is built from, by driving the real app.
 *
 *   make demo            # in one terminal: API on :8000, SPA on :5173
 *   node capture.mjs     # in another
 *
 * Every frame of the finished video that shows a UI is one of these PNGs — the
 * video never mocks a screen. Re-run this after any UI change and re-render.
 *
 * Two things make the captures usable as video plates:
 *
 *  - Each shot is *framed in camera*. `frameOn` scrolls the page so the element
 *    the scene is about sits high in the viewport, which leaves the lower third
 *    free for captions and stops the render's push-in from running off the
 *    bottom of the page into empty background.
 *  - Each shot records the viewport-space bounding box of the elements the
 *    scene points at. Those numbers are what `R` in src/PrahariDemo.tsx holds,
 *    so the spotlights stay locked to real UI instead of being eyeballed.
 *
 * Shots land in public/shots/ and the measured boxes in public/shots/boxes.json.
 * The boxes are written for reference when re-tuning scenes; PrahariDemo.tsx
 * keeps its own copy so a render never depends on this script having been run.
 */
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.PRAHARI_WEB ?? "http://127.0.0.1:5173";
const OUT = path.join(import.meta.dirname, "public", "shots");

// Playwright's bundled Chromium, wherever this image put it.
const CANDIDATES = [
  process.env.CHROME_PATH,
  "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
  ...(fs.existsSync("/opt/pw-browsers")
    ? fs
        .readdirSync("/opt/pw-browsers")
        .filter((d) => d.startsWith("chromium-"))
        .map((d) => `/opt/pw-browsers/${d}/chrome-linux/chrome`)
    : []),
].filter(Boolean);
const EXE = CANDIDATES.find((p) => p && fs.existsSync(p));
if (!EXE) {
  console.error("No Chromium found. Set CHROME_PATH to a Chromium binary.");
  process.exit(1);
}

// Freeze animations and hide scrollbars: a plate must be identical every run.
const QUIET = `
  *,*::before,*::after{animation-duration:0s!important;animation-delay:0s!important;
    transition-duration:0s!important;transition-delay:0s!important;}
  ::-webkit-scrollbar{width:0!important;height:0!important;display:none!important;}
  html{scrollbar-width:none!important;}
`;

fs.mkdirSync(OUT, { recursive: true });
const boxes = {};

const browser = await chromium.launch({
  executablePath: EXE,
  args: [
    "--no-sandbox",
    "--force-color-profile=srgb",
    "--font-render-hinting=none",
    "--hide-scrollbars",
  ],
});
const ctx = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 2, // 2x plates stay sharp under the render's push-ins
  colorScheme: "dark",
  reducedMotion: "reduce",
});
const page = await ctx.newPage();

const settle = async (ms = 1400) => {
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(ms);
};
const T = (t) => page.getByText(t, { exact: false });

const measure = async (loc) => {
  try {
    const el = loc.first();
    if (!(await el.count())) return null;
    const b = await el.boundingBox({ timeout: 3000 });
    return b
      ? { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }
      : null;
  } catch {
    return null;
  }
};

/** Scroll so `loc` sits at viewport y = targetY. Frames the shot in camera. */
const frameOn = async (loc, targetY) => {
  const el = loc.first();
  await el.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(350);
  const b = await el.boundingBox();
  if (!b) return;
  await page.evaluate((d) => window.scrollBy({ top: d, behavior: "instant" }), Math.round(b.y - targetY));
  await page.waitForTimeout(650);
};

const shot = async (name, targets = {}) => {
  await page.addStyleTag({ content: QUIET }).catch(() => {});
  await page.screenshot({ path: path.join(OUT, `${name}.png`), scale: "device" });
  const measured = {};
  for (const [k, loc] of Object.entries(targets)) measured[k] = await measure(loc);
  boxes[name] = measured;
  console.log(`  ${name}.png`, JSON.stringify(measured));
};

const scenario = async (name) => {
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.waitForTimeout(300);
  await page.getByRole("button", { name }).first().click();
  await settle(2400);
};

console.log(`capturing from ${BASE}`);

/* 1 · Triage queue — the thesis strip, the KPIs and the measured engine numbers */
await page.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 60000 });
await settle(2600);
await shot("triage-top", {
  thesis: T("Potential ≠ severity"),
  kpiPsif: T("POTENTIAL SIFS"),
  engine: T("Recall"),
  banner: T("Air-gapped Engine"),
});

/* 2 · Sandbox · Report A — a real injury with no fatal potential */
await page.goto(`${BASE}/sandbox`, { waitUntil: "networkidle", timeout: 60000 });
await settle(2200);
await scenario(/Low severity/i);
await frameOn(T("No rule engaged"), 300);
await shot("f-low", { chips: T("No rule engaged") });

/* 3 · Sandbox · Report B — the PSIF verdict, then the hybrid engine panel */
await scenario(/Clear Potential SIF/i);
await frameOn(T("POTENTIAL SIF"), 330);
await shot("f-psif", { chip: T("POTENTIAL SIF"), body: page.locator("textarea").first() });

await frameOn(T("Hybrid engine signal"), 210);
await shot("f-hybrid", {
  hybrid: T("Hybrid engine signal"),
  nlp: T("NLP EXTRACTION"),
  final: T("FINAL VERDICT"),
});

/* 4 · The audit trail — named rules, their citations and their spans */
const toggle = T("show the audit trail");
if (await toggle.count()) {
  await toggle.first().click();
  await settle(1800);
}
await frameOn(T("R-ENERGY-01"), 230);
await shot("f-rules", { r1: T("R-ENERGY-01"), r2: T("R-HE-01"), r3: T("R-CTRL-05") });

/* 5 · Code-mixed field language, and the spans the engine found in it */
await scenario(/Multi-rule/i);
await frameOn(page.locator("textarea").first(), 250);
await shot("f-hing", { body: page.locator("textarea").first() });
await frameOn(T("Energy cue"), 300);
await shot("f-hing-spans", { legend: T("Energy cue") });

/* 6 · Precursor map — escalation, then the accumulation index */
await page.goto(`${BASE}/map`, { waitUntil: "networkidle", timeout: 60000 });
await settle(2600);
await shot("f-map", {
  escalation: T("above the escalation threshold"),
  action1: T("Install and enforce fixed machine guarding"),
});
await frameOn(T("Precursor Accumulation Index"), 170);
await shot("f-chart", { title: T("Precursor Accumulation Index") });

/* 7 · Ontology — the vocabulary the engine reasons with */
await page.goto(`${BASE}/ontology`, { waitUntil: "networkidle", timeout: 60000 });
await settle(2600);
await shot("f-onto", { tabs: T("Energy sources"), mech: T("Heavy rotating equipment") });

fs.writeFileSync(path.join(OUT, "boxes.json"), JSON.stringify(boxes, null, 2));
console.log(`\n${Object.keys(boxes).length} shots -> ${OUT}`);
await browser.close();
