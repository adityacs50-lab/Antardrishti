import { staticFile, continueRender, delayRender } from "remotion";
import { useEffect, useState } from "react";

/**
 * The video's design system. Colours are lifted from the app's own tokens
 * (web/src/index.css) so the motion graphics and the captured UI read as one
 * product rather than a deck wrapped around some screenshots.
 */
export const C = {
  bg: "#0d0d0d",
  bgDeep: "#080808",
  surface: "#161616",
  surface1: "#1c1c1c",
  surface2: "#262626",
  border: "#393939",
  borderStrong: "#6f6f6f",

  text1: "#f4f4f4",
  text2: "#c6c6c6",
  text3: "#8d8d8d",

  accent: "#0f62fe", // Carbon blue — the app's --accent
  accentSoft: "#4589ff",

  danger: "#fa4d56", // critical / PSIF red
  warn: "#ff832b", // potential-SIF amber
  ok: "#42be65", // air-gapped · online green
  violet: "#a56eff",
} as const;

export const FONT = '"IBM Plex Sans", "Liberation Sans", sans-serif';
export const MONO = '"IBM Plex Mono", "DejaVu Sans Mono", monospace';

const FACES: Array<[string, number, string]> = [
  ["IBM Plex Sans", 400, "fonts/ibm-plex-sans-latin-400-normal.woff2"],
  ["IBM Plex Sans", 500, "fonts/ibm-plex-sans-latin-500-normal.woff2"],
  ["IBM Plex Sans", 600, "fonts/ibm-plex-sans-latin-600-normal.woff2"],
  ["IBM Plex Sans", 700, "fonts/ibm-plex-sans-latin-700-normal.woff2"],
  ["IBM Plex Mono", 400, "fonts/ibm-plex-mono-latin-400-normal.woff2"],
  ["IBM Plex Mono", 600, "fonts/ibm-plex-mono-latin-600-normal.woff2"],
];

export const fontCss = () =>
  FACES.map(
    ([family, weight, file]) => `@font-face{font-family:"${family}";font-style:normal;
      font-weight:${weight};font-display:block;src:url("${staticFile(file)}") format("woff2");}`,
  ).join("\n");

/**
 * Blocks the render until every face is actually rasterisable. Without this the
 * first frames of a render can ship in the fallback face, which looks like a
 * different video for half a second.
 */
export const useFonts = () => {
  const [handle] = useState(() => delayRender("loading IBM Plex"));
  useEffect(() => {
    const load = FACES.map(([family, weight]) =>
      (document as Document).fonts.load(`${weight} 64px "${family}"`),
    );
    Promise.all(load)
      .then(() => (document as Document).fonts.ready)
      .then(() => continueRender(handle))
      .catch(() => continueRender(handle));
  }, [handle]);
};

/** Frame-space rectangle inside the 1920x1080 screenshot coordinate system. */
export type Rect = { x: number; y: number; w: number; h: number };

export const W = 1920;
export const H = 1080;

/** A 16:9 rect anchored at (x,y) with the given width — keeps moves letterbox-free. */
export const rect = (x: number, y: number, w: number): Rect => ({
  x,
  y,
  w,
  h: (w * 9) / 16,
});

export const FULL: Rect = { x: 0, y: 0, w: W, h: H };
