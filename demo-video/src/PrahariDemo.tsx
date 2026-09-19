import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { C, FONT, MONO, W, H, useFonts, fontCss, type Rect } from "./theme";
import {
  Caption,
  Callout,
  Kicker,
  Metric,
  ProgressRail,
  Screen,
  Spotlight,
  Statement,
  focus,
  Vignette,
  Wordmark,
  ease,
  easeInOut,
  lerpRect,
} from "./components";

export const FPS = 30;
export const WIDTH = W;
export const HEIGHT = H;

const XF = 14; // crossfade length, in frames

/**
 * Regions of interest, in the coordinate space of the captured 1920x1080
 * screenshots. Every one of these points at a real element in the running app —
 * they were read off the captures rather than drawn by eye, so the spotlights
 * stay locked to the UI as the camera moves.
 */
const R = {
  triage: {
    thesis: { x: 179, y: 113, w: 1562, h: 46 },
    kpiRow: { x: 179, y: 182, w: 1562, h: 118 },
    kpiPsif: { x: 179, y: 182, w: 384, h: 118 },
    engine: { x: 186, y: 324, w: 404, h: 47 },
    banner: { x: 1012, y: 4, w: 224, h: 29 },
  },
  low: {
    chips: { x: 200, y: 594, w: 400, h: 36 },
  },
  psif: {
    chips: { x: 200, y: 320, w: 500, h: 36 },
    body: { x: 197, y: 465, w: 1526, h: 155 },
  },
  hybrid: {
    card: { x: 200, y: 648, w: 1530, h: 228 },
    nlp: { x: 213, y: 716, w: 476, h: 110 },
    rules: { x: 722, y: 716, w: 476, h: 110 },
    final: { x: 1229, y: 716, w: 480, h: 110 },
  },
  audit: {
    card1: { x: 197, y: 206, w: 1526, h: 97 },
    card2: { x: 197, y: 309, w: 1526, h: 97 },
    card3: { x: 197, y: 412, w: 1526, h: 97 },
  },
  hing: {
    body: { x: 197, y: 250, w: 1526, h: 155 },
    spans: { x: 197, y: 284, w: 1531, h: 112 },
  },
  map: {
    escalation: { x: 179, y: 175, w: 1562, h: 158 },
    action1: { x: 192, y: 414, w: 1536, h: 80 },
  },
  chart: {
    plot: { x: 190, y: 228, w: 1540, h: 252 },
    moran: { x: 190, y: 470, w: 1540, h: 70 },
  },
  onto: {
    tabs: { x: 179, y: 196, w: 1562, h: 40 },
    mech: { x: 179, y: 540, w: 778, h: 278 },
  },
} satisfies Record<string, Record<string, Rect>>;

/* ------------------------------------------------------------------ scenes */

type Scene = {
  id: string;
  chapter: string;
  dur: number;
  render: (f: number, d: number) => React.ReactNode;
};

/** Camera drift helper: eased tween across the whole scene. */
const drift = (a: Rect, b: Rect, f: number, d: number) =>
  lerpRect(a, b, easeInOut(Math.min(1, Math.max(0, f / d))));

const SCENES: Scene[] = [
  /* 1 ------------------------------------------------------------ cold open */
  {
    id: "open",
    chapter: "",
    dur: 180,
    render: (f) => {
      const line = ease(f, [22, 70], [0, 1]);
      const sub = ease(f, [74, 104], [0, 1]);
      return (
        <AbsoluteFill
          style={{
            backgroundColor: C.bgDeep,
            justifyContent: "center",
            paddingLeft: 150,
          }}
        >
          {/* faint engineering grid, same motif as the app shell */}
          <AbsoluteFill
            style={{
              opacity: ease(f, [0, 40], [0, 0.5]),
              backgroundImage: `linear-gradient(to right, ${C.border}55 1px, transparent 1px),
                                linear-gradient(to bottom, ${C.border}55 1px, transparent 1px)`,
              backgroundSize: "68px 68px",
              maskImage: "radial-gradient(70% 60% at 30% 50%, #000 0%, transparent 78%)",
            }}
          />
          <div style={{ position: "relative" }}>
            <div style={{ marginBottom: 46 }}>
              <Wordmark frame={f} start={4} />
            </div>

            <div style={{ opacity: line }}>
              <Statement
                frame={f}
                start={26}
                size={92}
                lines={[
                  <>
                    Potential <span style={{ color: C.danger }}>≠</span> severity
                  </>,
                ]}
              />
            </div>

            <div
              style={{
                opacity: sub,
                transform: `translateY(${(1 - sub) * 20}px)`,
                marginTop: 30,
                maxWidth: 1180,
                fontFamily: FONT,
                fontSize: 37,
                lineHeight: 1.4,
                color: C.text2,
                letterSpacing: "-0.012em",
              }}
            >
              An offline engine that finds the incidents which{" "}
              <span style={{ color: C.text1, fontWeight: 600 }}>could have killed someone</span> —
              including the ones where nobody got hurt.
            </div>

            <div
              style={{
                marginTop: 56,
                opacity: ease(f, [112, 142], [0, 1]),
                display: "flex",
                gap: 14,
                alignItems: "center",
              }}
            >
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "9px 16px",
                  borderRadius: 999,
                  border: `1px solid ${C.ok}`,
                  color: C.ok,
                  fontFamily: MONO,
                  fontSize: 21,
                  letterSpacing: "0.06em",
                }}
              >
                <span
                  style={{
                    width: 9,
                    height: 9,
                    borderRadius: 999,
                    backgroundColor: C.ok,
                    boxShadow: `0 0 12px ${C.ok}`,
                  }}
                />
                100% OFFLINE
              </span>
              <span
                style={{
                  padding: "9px 16px",
                  borderRadius: 999,
                  border: `1px solid ${C.border}`,
                  color: C.text3,
                  fontFamily: MONO,
                  fontSize: 21,
                  letterSpacing: "0.06em",
                }}
              >
                NEURO-SYMBOLIC
              </span>
            </div>
          </div>
        </AbsoluteFill>
      );
    },
  },

  /* 2 ------------------------------------------------------- the problem */
  {
    id: "problem",
    chapter: "The problem",
    dur: 155,
    render: (f) => (
      <AbsoluteFill
        style={{ backgroundColor: C.bg, justifyContent: "center", paddingLeft: 150 }}
      >
        <div style={{ marginBottom: 34, opacity: ease(f, [0, 22], [0, 1]) }}>
          <Kicker colour={C.danger}>The blind spot</Kicker>
        </div>
        <Statement
          frame={f}
          start={12}
          size={70}
          lines={[
            "Safety systems rank what happened.",
            <>
              Fatalities are preceded by{" "}
              <span style={{ color: C.warn }}>near-misses nobody ranked</span>.
            </>,
          ]}
        />
        <div
          style={{
            marginTop: 44,
            maxWidth: 1250,
            opacity: ease(f, [66, 96], [0, 1]),
            transform: `translateY(${(1 - ease(f, [66, 96], [0, 1])) * 18}px)`,
            fontFamily: FONT,
            fontSize: 35,
            lineHeight: 1.42,
            color: C.text2,
          }}
        >
          A bypassed relief valve that hurt nobody gets closed the same day. The same bypass, a
          week later, kills a crew. <span style={{ color: C.text1 }}>prahari ranks the energy
          and the missing barrier</span> — not the injury.
        </div>
      </AbsoluteFill>
    ),
  },

  /* 3 ------------------------------------------- triage queue + the proof */
  {
    id: "triage",
    chapter: "Triage queue",
    dur: 300,
    render: (f, d) => {
      const cam = drift(focus(R.triage.kpiRow, 1860, 0.34), focus(R.triage.engine, 1520, 0.4), f, d);
      const s1 = ease(f, [58, 84], [0, 1]) * (1 - ease(f, [140, 162], [0, 1]));
      const s2 = ease(f, [168, 194], [0, 1]);
      return (
        <>
          <Screen src="shots/triage-top.png" cam={cam}>
            <Spotlight box={R.triage.kpiRow} progress={s1} colour={C.warn} />
            <Spotlight box={R.triage.engine} progress={s2} colour={C.accentSoft} />
          </Screen>
          <Callout
            box={R.triage.kpiPsif}
            cam={cam}
            label="120 potential SIFs"
            sub="fatal energy, no barrier, nobody hurt yet"
            colour={C.warn}
            progress={s1}
          />
          <Callout
            box={R.triage.engine}
            cam={cam}
            label="97.6% recall · 85.1% precision"
            sub="450 held-out reports · regenerated by script, not typed"
            colour={C.accentSoft}
            progress={s2}
          />
          <Caption
            progress={ease(f, [16, 44], [0, 1]) * (1 - ease(f, [d - 26, d - 6], [0, 1]))}
            lines={["700 field reports, ranked by what could have happened."]}
          />
        </>
      );
    },
  },

  /* 4 ------------------------------------------------- report A, the trap */
  {
    id: "trap",
    chapter: "Report A · the trap",
    dur: 265,
    render: (f, d) => {
      const cam = drift(focus(R.low.chips, 1840, 0.5), focus(R.low.chips, 1460, 0.46), f, d);
      const s = ease(f, [62, 90], [0, 1]);
      return (
        <>
          <Screen src="shots/f-low.png" cam={cam}>
            <Spotlight box={R.low.chips} progress={s} colour={C.ok} />
          </Screen>
          <Callout
            box={R.low.chips}
            cam={cam}
            label="Low severity · no rule engaged"
            sub="a real injury — and zero fatal potential"
            colour={C.ok}
            progress={s}
          />
          <Caption
            progress={ease(f, [14, 42], [0, 1]) * (1 - ease(f, [d - 26, d - 6], [0, 1]))}
            kicker="Report A"
            accent={C.ok}
            lines={[
              "A slip in the canteen. A bruised knee.",
              "Every system tracks this one. We rank it low.",
            ]}
          />
        </>
      );
    },
  },

  /* 5 -------------------------------------------- report B, the argument */
  {
    id: "psif",
    chapter: "Report B · the argument",
    dur: 320,
    render: (f, d) => {
      const cam = drift(focus(R.psif.body, 1860, 0.46), focus(R.psif.chips, 1480, 0.48), f, d);
      const sText = ease(f, [40, 66], [0, 1]) * (1 - ease(f, [150, 172], [0, 1]));
      const sChips = ease(f, [178, 206], [0, 1]);
      return (
        <>
          <Screen src="shots/f-psif.png" cam={cam}>
            <Spotlight box={R.psif.body} progress={sText} colour={C.accentSoft} />
            <Spotlight box={R.psif.chips} progress={sChips} colour={C.warn} />
          </Screen>
          <Callout
            box={R.psif.body}
            cam={cam}
            label="Relief valve bypassed · flange blew out"
            sub="no injury to any personnel"
            colour={C.accentSoft}
            progress={sText}
          />
          <Callout
            box={R.psif.chips}
            cam={cam}
            label="POTENTIAL SIF"
            sub="pressure · high energy · barrier bypassed"
            colour={C.warn}
            progress={sChips}
          />
          <Caption
            progress={ease(f, [12, 40], [0, 1]) * (1 - ease(f, [140, 158], [0, 1]))}
            kicker="Report B"
            accent={C.warn}
            lines={["Nobody was hurt. Anywhere else, this closes today."]}
          />
          <Caption
            progress={ease(f, [214, 240], [0, 1]) * (1 - ease(f, [d - 26, d - 6], [0, 1]))}
            kicker="Verdict"
            accent={C.warn}
            lines={["prahari escalates it. The energy could have killed two people."]}
          />
        </>
      );
    },
  },

  /* 6 ------------------------------------------------ the neuro-symbolic core */
  {
    id: "hybrid",
    chapter: "How the verdict is made",
    dur: 275,
    render: (f, d) => {
      const cam = drift(focus(R.hybrid.card, 1500, 0.44), focus(R.hybrid.card, 1240, 0.42), f, d);
      const a = ease(f, [30, 56], [0, 1]) * (1 - ease(f, [96, 112], [0, 1]));
      const b = ease(f, [112, 138], [0, 1]) * (1 - ease(f, [178, 194], [0, 1]));
      const c = ease(f, [194, 220], [0, 1]);
      return (
        <>
          <Screen src="shots/f-hybrid.png" cam={cam}>
            <Spotlight box={R.hybrid.nlp} progress={a} colour={C.ok} pad={6} />
            <Spotlight box={R.hybrid.rules} progress={b} colour={C.accentSoft} pad={6} />
            <Spotlight box={R.hybrid.final} progress={c} colour={C.warn} pad={6} />
          </Screen>
          <Callout
            box={R.hybrid.nlp}
            cam={cam}
            side="top"
            label="1 · the model only extracts facts"
            sub="4 of 4 fact slots · 11 evidence spans"
            colour={C.ok}
            progress={a}
          />
          <Callout
            box={R.hybrid.rules}
            cam={cam}
            side="top"
            label="2 · named rules decide"
            sub="same text, same verdict, every time"
            colour={C.accentSoft}
            progress={b}
          />
          <Callout
            box={R.hybrid.final}
            cam={cam}
            side="top"
            label="3 · the verdict"
            sub="decided by rules only — never by the model"
            colour={C.warn}
            progress={c}
          />
          <Caption
            progress={ease(f, [8, 34], [0, 1]) * (1 - ease(f, [d - 26, d - 6], [0, 1]))}
            kicker="Neuro-symbolic"
            lines={["Hybrid, but not a black box."]}
          />
        </>
      );
    },
  },

  /* 7 --------------------------------------------------- the audit trail */
  {
    id: "audit",
    chapter: "Audit trail",
    dur: 300,
    render: (f, d) => {
      const cam = drift(focus(R.audit.card1, 1820, 0.4), focus(R.audit.card2, 1420, 0.42), f, d);
      const a = ease(f, [48, 74], [0, 1]) * (1 - ease(f, [128, 146], [0, 1]));
      const b = ease(f, [176, 202], [0, 1]);
      return (
        <>
          <Screen src="shots/f-rules.png" cam={cam}>
            <Spotlight box={R.audit.card1} progress={a} colour={C.accentSoft} pad={5} />
            <Spotlight box={R.audit.card3} progress={b} colour={C.ok} pad={5} />
          </Screen>
          <Callout
            box={R.audit.card1}
            cam={cam}
            label="R-ENERGY-01 → energy_source=pressure"
            sub="cites EEI Safety Classification · 3 spans in text"
            colour={C.accentSoft}
            progress={a}
          />
          <Callout
            box={R.audit.card3}
            cam={cam}
            label="R-CTRL-05 → control_status=bypassed"
            sub="cites EEI High-Energy Control Assessment · 1 span in text"
            colour={C.ok}
            progress={b}
          />
          <Caption
            progress={ease(f, [10, 38], [0, 1]) * (1 - ease(f, [116, 134], [0, 1]))}
            lines={[
              "Nine named rules fired — each one citing a standard",
              "and the exact characters that triggered it.",
            ]}
          />
          <Caption
            progress={ease(f, [214, 240], [0, 1]) * (1 - ease(f, [d - 26, d - 6], [0, 1]))}
            lines={["A safety reviewer can audit the reasoning without trusting the model."]}
          />
        </>
      );
    },
  },

  /* 8 ---------------------------------------------- code-mixed field language */
  {
    id: "hinglish",
    chapter: "Real field language",
    dur: 275,
    render: (f, d) => {
      // Two captures in one beat: the raw code-mixed report, then the same text
      // with the engine's evidence spans drawn over it. They dissolve so the
      // spans look like they land on the report rather than replacing it.
      const swap = ease(f, [140, 168], [0, 1]);
      const camText = drift(focus(R.hing.body, 1840, 0.42), focus(R.hing.body, 1560, 0.42), f, d);
      const camSpans = drift(focus(R.hing.spans, 1620, 0.44), focus(R.hing.spans, 1400, 0.44), f, d);
      const a = ease(f, [40, 66], [0, 1]) * (1 - swap);
      const b = ease(f, [158, 186], [0, 1]);
      return (
        <>
          <AbsoluteFill style={{ opacity: 1 - swap }}>
            <Screen src="shots/f-hing.png" cam={camText}>
              <Spotlight box={R.hing.body} progress={a} colour={C.violet} />
            </Screen>
          </AbsoluteFill>
          <AbsoluteFill style={{ opacity: swap }}>
            <Screen src="shots/f-hing-spans.png" cam={camSpans}>
              <Spotlight box={R.hing.spans} progress={b} colour={C.accentSoft} />
            </Screen>
          </AbsoluteFill>
          <Callout
            box={R.hing.body}
            cam={camText}
            label="Hinglish, exactly as it is written on site"
            sub="“Hot work permit nahi liya gaya tha aur gas test nahi kiya.”"
            colour={C.violet}
            progress={a}
          />
          <Callout
            box={R.hing.spans}
            cam={camSpans}
            label="18 evidence spans · 3 Life-Saving Rules"
            sub="hot work · energy isolation · work authorisation"
            colour={C.accentSoft}
            progress={b}
          />
          <Caption
            progress={ease(f, [10, 38], [0, 1]) * (1 - ease(f, [112, 130], [0, 1]))}
            kicker="Code-mixed input"
            accent={C.violet}
            lines={["Field reports are not written in clean English."]}
          />
          <Caption
            progress={ease(f, [166, 192], [0, 1]) * (1 - ease(f, [d - 26, d - 6], [0, 1]))}
            lines={["The engine reads it anyway — and shows its evidence."]}
          />
        </>
      );
    },
  },

  /* 9 ------------------------------------------------------ from noise to pattern */
  {
    id: "map",
    chapter: "Precursor map",
    dur: 265,
    render: (f, d) => {
      const cam = drift(focus(R.map.escalation, 1860, 0.4), focus(R.map.action1, 1500, 0.44), f, d);
      const a = ease(f, [40, 66], [0, 1]) * (1 - ease(f, [120, 138], [0, 1]));
      const b = ease(f, [152, 180], [0, 1]);
      return (
        <>
          <Screen src="shots/f-map.png" cam={cam}>
            <Spotlight box={R.map.escalation} progress={a} colour={C.danger} />
            <Spotlight box={R.map.action1} progress={b} colour={C.warn} pad={6} />
          </Screen>
          <Callout
            box={R.map.escalation}
            cam={cam}
            label="4 site–energy pairs above the escalation threshold"
            colour={C.danger}
            progress={a}
          />
          <Callout
            box={R.map.action1}
            cam={cam}
            label="Install and enforce fixed machine guarding"
            sub="Moran · mechanical · the same barrier failed 6 times"
            colour={C.warn}
            progress={b}
          />
          <Caption
            progress={ease(f, [10, 38], [0, 1]) * (1 - ease(f, [108, 126], [0, 1]))}
            kicker="One report is noise"
            accent={C.danger}
            lines={["The same barrier failing at the same site is a pattern."]}
          />
        </>
      );
    },
  },

  /* 10 --------------------------------------------------- accumulation index */
  {
    id: "chart",
    chapter: "Accumulation index",
    dur: 250,
    render: (f, d) => {
      const cam = drift(focus(R.chart.plot, 1860, 0.42), focus(R.chart.moran, 1500, 0.44), f, d);
      const a = ease(f, [34, 62], [0, 1]) * (1 - ease(f, [116, 134], [0, 1]));
      const b = ease(f, [146, 174], [0, 1]);
      return (
        <>
          <Screen src="shots/f-chart.png" cam={cam}>
            <Spotlight box={R.chart.plot} progress={a} colour={C.accentSoft} />
            <Spotlight box={R.chart.moran} progress={b} colour={C.danger} pad={6} />
          </Screen>
          <Callout
            box={R.chart.plot}
            cam={cam}
            side="bottom"
            label="Precursor Accumulation Index"
            sub="rises when the same barrier fails repeatedly at the same place"
            colour={C.accentSoft}
            progress={a}
          />
          <Callout
            box={R.chart.moran}
            cam={cam}
            side="bottom"
            label="Moran · mechanical · index 40.4 · CRITICAL"
            sub="fixed machine guarding — absent"
            colour={C.danger}
            progress={b}
          />
          <Caption
            progress={ease(f, [8, 34], [0, 1]) * (1 - ease(f, [104, 122], [0, 1]))}
            lines={["This is the number an HSE meeting can actually fund."]}
          />
        </>
      );
    },
  },

  /* 11 ------------------------------------------------------------- ontology */
  {
    id: "ontology",
    chapter: "Ontology",
    dur: 215,
    render: (f, d) => {
      const cam = drift(focus(R.onto.tabs, 1860, 0.36), focus(R.onto.mech, 1480, 0.44), f, d);
      const a = ease(f, [42, 70], [0, 1]);
      return (
        <>
          <Screen src="shots/f-onto.png" cam={cam}>
            <Spotlight box={R.onto.mech} progress={a} colour={C.accentSoft} />
          </Screen>
          <Callout
            box={R.onto.mech}
            cam={cam}
            label="Served from the engine itself, not a copy"
            sub="EEI Energy Wheel · barrier states · IOGP Life-Saving Rules"
            colour={C.accentSoft}
            progress={a}
          />
          <Caption
            progress={ease(f, [10, 36], [0, 1]) * (1 - ease(f, [d - 26, d - 6], [0, 1]))}
            kicker="Defendable"
            lines={["Every term the engine reasons with is published and inspectable."]}
          />
        </>
      );
    },
  },

  /* 12 ---------------------------------------------------------------- close */
  {
    id: "close",
    chapter: "",
    dur: 245,
    render: (f) => {
      const grid = ease(f, [0, 40], [0, 0.45]);
      return (
        <AbsoluteFill
          style={{ backgroundColor: C.bgDeep, justifyContent: "center", paddingLeft: 150 }}
        >
          <AbsoluteFill
            style={{
              opacity: grid,
              backgroundImage: `linear-gradient(to right, ${C.border}55 1px, transparent 1px),
                                linear-gradient(to bottom, ${C.border}55 1px, transparent 1px)`,
              backgroundSize: "68px 68px",
              maskImage: "radial-gradient(70% 60% at 32% 50%, #000 0%, transparent 78%)",
            }}
          />
          <div style={{ position: "relative" }}>
            <Statement
              frame={f}
              start={6}
              size={68}
              lines={[
                <>
                  Every verdict traces to a{" "}
                  <span style={{ color: C.accentSoft }}>named rule</span>
                </>,
                <>
                  and the <span style={{ color: C.accentSoft }}>exact characters</span> that fired
                  it.
                </>,
              ]}
            />

            <div style={{ display: "flex", gap: 108, marginTop: 72 }}>
              <Metric
                frame={f}
                start={70}
                value={97.6}
                decimals={1}
                suffix="%"
                label="recall on SIF precursors"
                colour={C.ok}
              />
              <Metric
                frame={f}
                start={84}
                value={85.1}
                decimals={1}
                suffix="%"
                label="precision · 450 held-out reports"
                colour={C.accentSoft}
              />
              <Metric
                frame={f}
                start={98}
                value={1.9}
                decimals={1}
                suffix=" ms"
                label="mean, per report, on CPU"
                colour={C.text1}
              />
            </div>

            <div
              style={{
                marginTop: 78,
                display: "flex",
                alignItems: "center",
                gap: 26,
                opacity: ease(f, [126, 158], [0, 1]),
              }}
            >
              <Wordmark frame={f} start={126} />
              <span
                style={{
                  paddingLeft: 26,
                  borderLeft: `1px solid ${C.border}`,
                  fontFamily: FONT,
                  fontSize: 27,
                  color: C.text2,
                }}
              >
                runs air-gapped · no API, no cloud, no model calling home
              </span>
            </div>
          </div>
        </AbsoluteFill>
      );
    },
  },
];

/* ------------------------------------------------------------- composition */

// Scenes butt up against each other and overlap by XF frames for the crossfade.
const STARTS: number[] = [];
let cursor = 0;
for (const s of SCENES) {
  STARTS.push(cursor);
  cursor += s.dur - XF;
}
export const TOTAL_FRAMES = cursor + XF;

export const PrahariDemo: React.FC = () => {
  useFonts();
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: C.bgDeep }}>
      <style>{fontCss()}</style>

      {SCENES.map((s, i) => {
        const start = STARTS[i];
        const local = frame - start;
        if (local < -2 || local > s.dur + 2) return null;

        // Cross-dissolve in and out; the first and last scenes fade from black.
        const opacity =
          ease(local, [0, XF], [0, 1]) * (1 - ease(local, [s.dur - XF, s.dur], [0, 1]));

        return (
          <AbsoluteFill key={s.id} style={{ opacity }}>
            {s.render(local, s.dur)}
          </AbsoluteFill>
        );
      })}

      <Vignette />

      <ProgressRail
        progress={frame / TOTAL_FRAMES}
        chapter={
          SCENES.find((s, i) => frame >= STARTS[i] && frame < STARTS[i] + s.dur)?.chapter ?? ""
        }
        opacity={
          ease(frame, [150, 190], [0, 1]) *
          (1 - ease(frame, [TOTAL_FRAMES - 250, TOTAL_FRAMES - 210], [0, 1]))
        }
      />

      {/* Fade up from black on the first frames, and out on the last. */}
      <AbsoluteFill
        style={{
          backgroundColor: "#000",
          opacity:
            (1 - ease(frame, [0, 26], [0, 1])) +
            ease(frame, [TOTAL_FRAMES - 34, TOTAL_FRAMES], [0, 1]),
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
