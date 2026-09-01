/** Display vocabulary. The API speaks snake_case; humans do not. */

import type {
  Band, ControlStatus, EnergySource, InjuryOutcome, LifeSavingRule,
  SifClassification, Trend,
} from "@/types/api";

export const CLASSIFICATION_LABEL: Record<SifClassification, string> = {
  hsif: "HSIF",
  lsif: "LSIF",
  psif: "Potential SIF",
  capacity: "Capacity",
  exposure: "Exposure",
  success: "Success",
  low_severity: "Low severity",
  insufficient_information: "Insufficient info",
};

/** What each class means, in one line, for tooltips and empty states. */
export const CLASSIFICATION_MEANING: Record<SifClassification, string> = {
  hsif: "Someone was seriously hurt or killed by a high-energy release.",
  lsif: "Serious outcome, but not from a high-energy source.",
  psif: "High energy got loose with nothing adequate in its way. Nobody was hurt — this time.",
  capacity: "High energy got loose and the direct control held. A success worth studying.",
  exposure: "A high-energy hazard was sitting there uncontrolled. Nothing happened yet.",
  success: "The hazard was present and the direct control was verified.",
  low_severity: "No fatal potential, whatever the injury was.",
  insufficient_information: "The report says too little to judge. Saying so is the honest answer.",
};

export const CONTROL_STATUS_LABEL: Record<ControlStatus, string> = {
  present_verified: "Verified",
  present_unverified: "Unverified",
  absent: "Absent",
  failed: "Failed",
  bypassed: "Bypassed",
  not_followed: "Not followed",
  unknown: "Unknown",
};

export const ENERGY_LABEL: Record<EnergySource, string> = {
  gravity: "Gravity", motion: "Motion", mechanical: "Mechanical",
  electrical: "Electrical", pressure: "Pressure", temperature: "Temperature",
  chemical: "Chemical", biological: "Biological", radiation: "Radiation", sound: "Sound",
};

export const INJURY_LABEL: Record<InjuryOutcome, string> = {
  none: "No injury", first_aid: "First aid", minor_injury: "Minor injury",
  serious_injury: "Serious injury", fatality: "Fatality",
};

export const LSR_LABEL: Record<LifeSavingRule, string> = {
  bypassing_safety_controls: "Bypassing Safety Controls",
  confined_space: "Confined Space",
  driving: "Driving",
  energy_isolation: "Energy Isolation",
  hot_work: "Hot Work",
  line_of_fire: "Line of Fire",
  safe_mechanical_lifting: "Safe Mechanical Lifting",
  work_authorisation: "Work Authorisation",
  working_at_height: "Working at Height",
};

export const LSR_SHORT: Record<LifeSavingRule, string> = {
  bypassing_safety_controls: "Bypassing",
  confined_space: "Confined Space",
  driving: "Driving",
  energy_isolation: "Energy Isolation",
  hot_work: "Hot Work",
  line_of_fire: "Line of Fire",
  safe_mechanical_lifting: "Lifting",
  work_authorisation: "Work Auth.",
  working_at_height: "Height",
};

export const BAND_LABEL: Record<Band, string> = {
  watch: "Watch", elevated: "Elevated", high: "High", critical: "Critical",
};

export const TREND_LABEL: Record<Trend, string> = {
  rising: "Rising", falling: "Falling", flat: "Flat",
  insufficient_history: "No history",
};

/** Classes that mean "uncontrolled fatal potential" — the reason this exists. */
export const PRECURSOR_CLASSES: SifClassification[] = ["psif", "exposure"];

export function isPrecursor(c: SifClassification) {
  return PRECURSOR_CLASSES.includes(c);
}

export function titleCase(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

export function formatDate(iso: string) {
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export function daysAgo(iso: string) {
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  const diff = Math.floor((Date.now() - d.getTime()) / 86_400_000);
  if (diff <= 0) return "today";
  if (diff === 1) return "yesterday";
  if (diff < 30) return `${diff}d ago`;
  if (diff < 365) return `${Math.floor(diff / 30)}mo ago`;
  return `${Math.floor(diff / 365)}y ago`;
}

export function pct(n: number, digits = 0) {
  return `${(n * 100).toFixed(digits)}%`;
}
