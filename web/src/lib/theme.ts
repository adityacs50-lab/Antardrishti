/**
 * Colour assignment by JOB, not by taste.
 *
 * STATUS colours (good/warning/serious/critical) are reserved for state and are
 * never reused as a series colour. SIF classification is a state, so it wears
 * status colours. Every status is paired with an icon and a text label — colour
 * never carries the meaning alone.
 *
 * SERIES colours are the validated categorical set (see index.css header).
 */

import type { Band, ControlStatus, SifClassification, Trend } from "@/types/api";

export const STATUS = {
  good: "#0ca30c",
  warning: "#fab219",
  serious: "#ec835a",
  critical: "#d03b3b",
  neutral: "#6B7C8F",
  violet: "#9085e9",
} as const;

export const SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500"] as const;

/** Sequential blue ramp, stepped for the DARK surface: low = near-surface. */
export const SEQUENTIAL_DARK = [
  "#16202B", "#173f6b", "#184f95", "#256abf", "#2a78d6", "#5598e7", "#9ec5f4",
] as const;

export const CUE = { energy: "#3987e5", control: "#d95926", context: "#199e70" } as const;

type Tone = { fg: string; bg: string; ring: string; dot: string };

const tone = (hex: string, bgAlpha = 0.14, ringAlpha = 0.35): Tone => ({
  fg: hex,
  bg: hexA(hex, bgAlpha),
  ring: hexA(hex, ringAlpha),
  dot: hex,
});

export function hexA(hex: string, alpha: number) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgb(${r} ${g} ${b} / ${alpha})`;
}

export const CLASSIFICATION_TONE: Record<SifClassification, Tone> = {
  hsif: tone(STATUS.critical),
  psif: tone(STATUS.serious),
  exposure: tone(STATUS.warning),
  lsif: tone(STATUS.serious, 0.1, 0.25),
  capacity: tone(STATUS.good),
  success: tone(STATUS.good),
  low_severity: tone(STATUS.neutral, 0.12, 0.3),
  insufficient_information: tone(STATUS.violet, 0.12, 0.3),
};

export const CONTROL_TONE: Record<ControlStatus, Tone> = {
  present_verified: tone(STATUS.good),
  present_unverified: tone(STATUS.warning),
  absent: tone(STATUS.critical),
  failed: tone(STATUS.critical),
  bypassed: tone(STATUS.critical),
  not_followed: tone(STATUS.serious),
  unknown: tone(STATUS.neutral),
};

export const BAND_TONE: Record<Band, Tone> = {
  watch: tone(STATUS.neutral, 0.12, 0.3),
  elevated: tone(STATUS.warning),
  high: tone(STATUS.serious),
  critical: tone(STATUS.critical),
};

export const TREND_TONE: Record<Trend, string> = {
  rising: STATUS.critical,
  falling: STATUS.good,
  flat: STATUS.neutral,
  insufficient_history: STATUS.neutral,
};

/** Heatmap fill for a precursor rate in [0,1]. Zero recedes to the surface. */
export function densityFill(rate: number, total: number) {
  if (total === 0) return "hsl(var(--surface-0))";
  if (rate <= 0) return "#16202B";
  if (rate < 0.2) return "#1d3f66";
  if (rate < 0.4) return "#184f95";
  if (rate < 0.6) return "#256abf";
  if (rate < 0.8) return "#3987e5";
  return "#6da7ec";
}

/** Text colour that stays legible on top of densityFill(). */
export function densityInk(rate: number, total: number) {
  if (total === 0) return "hsl(var(--text-3))";
  return rate >= 0.6 ? "#0B0F14" : "hsl(var(--text-1))";
}
