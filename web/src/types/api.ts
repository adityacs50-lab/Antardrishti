/** Types mirroring the FastAPI Pydantic schemas in backend/prahari/api/schemas.py. */

export type SifClassification =
  | "hsif" | "lsif" | "psif" | "capacity"
  | "exposure" | "success" | "low_severity" | "insufficient_information";

export type EnergySource =
  | "gravity" | "motion" | "mechanical" | "electrical" | "pressure"
  | "temperature" | "chemical" | "biological" | "radiation" | "sound";

export type ControlStatus =
  | "present_verified" | "present_unverified" | "absent"
  | "failed" | "bypassed" | "not_followed" | "unknown";

export type InjuryOutcome =
  | "none" | "first_aid" | "minor_injury" | "serious_injury" | "fatality";

export type LifeSavingRule =
  | "bypassing_safety_controls" | "confined_space" | "driving"
  | "energy_isolation" | "hot_work" | "line_of_fire"
  | "safe_mechanical_lifting" | "work_authorisation" | "working_at_height";

export type Trend = "rising" | "falling" | "flat" | "insufficient_history";
export type Band = "watch" | "elevated" | "high" | "critical";

export interface EvidenceSpan {
  start: number;
  end: number;
  quoted_text: string;
  rule_id: string | null;
}

export interface RuleFiring {
  rule_id: string;
  description: string;
  conclusion: string;
  citation_key: string;
  spans: EvidenceSpan[];
}

export interface SIFVerdict {
  classification: SifClassification;
  energy_source: EnergySource | null;
  high_energy: boolean;
  high_energy_incident: boolean;
  control_status: ControlStatus;
  direct_control_key: string | null;
  direct_control_effective: boolean;
  injury_outcome: InjuryOutcome;
  primary_lsr: LifeSavingRule | null;
  secondary_lsr: LifeSavingRule[];
  evidence_completeness: number;
  triage_rank: number;
  engine_version: string;
  extractor_version: string;
  fired_rules: RuleFiring[];
}

export interface ReportSummary {
  id: number;
  report_uid: string;
  site: string;
  date: string;
  reporter_role: string | null;
  activity: string | null;
  excerpt: string;
  classification: SifClassification;
  energy_source: EnergySource | null;
  primary_lsr: LifeSavingRule | null;
  control_status: ControlStatus;
  evidence_completeness: number;
  triage_rank: number;
  reviewed: boolean;
  reason: string;
}

export interface Review {
  id: number;
  reviewer_role: string;
  decision: "confirm" | "override";
  reason: string;
  corrected_classification: SifClassification | null;
  corrected_energy_source: EnergySource | null;
  corrected_control_status: ControlStatus | null;
  corrected_primary_lsr: LifeSavingRule | null;
  created_at: string;
}

export interface ReportDetail {
  id: number;
  report_uid: string;
  text: string;
  site: string;
  date: string;
  reporter_role: string | null;
  activity: string | null;
  source: string;
  ingested_at: string;
  verdict: SIFVerdict;
  evidence_spans: EvidenceSpan[];
  reviews: Review[];
  effective_classification: SifClassification;
}

export interface Page<T> { total: number; limit: number; offset: number; items: T[] }

export interface AnalyzeResult {
  text: string;
  verdict: SIFVerdict;
  evidence_spans: EvidenceSpan[];
  reason: string;
}

export interface Meta {
  sites: string[];
  activities: string[];
  classifications: SifClassification[];
  energy_sources: EnergySource[];
  control_statuses: ControlStatus[];
  life_saving_rules: { value: LifeSavingRule; short_name: string }[];
  engine_version: string;
  extractor_version: string;
  report_count: number;
}

export interface DensityCell {
  site: string; activity: string;
  total_reports: number; precursor_count: number; precursor_rate: number;
}
export interface DensityOut {
  window_days: number | null; sites: string[]; activities: string[]; cells: DensityCell[];
}

export interface LsrBucket {
  lsr: LifeSavingRule; short_name: string;
  count: number; precursor_count: number; share: number;
}
export interface LsrOut { total: number; unassigned: number; buckets: LsrBucket[] }

export interface BarrierPattern {
  control_key: string; control_label: string; control_class: string;
  energy_source: EnergySource | null; site: string | null;
  failure_count: number; statuses: Record<string, number>;
  first_seen: string | null; last_seen: string | null;
  trend: Trend; recent_count: number; previous_count: number;
}
export interface BarriersOut { window_days: number; patterns: BarrierPattern[] }

export interface AccumulationContributor {
  report_id: number; report_uid: string; date: string;
  classification: SifClassification; control_status: ControlStatus;
  age_days: number; decayed_weight: number;
}
export interface AccumulationSignature {
  control_key: string; control_label: string; control_status: ControlStatus;
  occurrences: number; decayed_occurrences: number; contribution: number;
  contributors: AccumulationContributor[];
}
export interface AccumulationCell {
  site: string; energy_source: EnergySource;
  index: number; band: Band;
  total_precursors: number; max_repeat: number;
  trend: Trend; previous_index: number;
  signatures: AccumulationSignature[];
  explanation: string;
}
export interface AccumulationOut {
  window_days: number; half_life_days: number; repeat_exponent: number;
  diversity_discount: number; bands: Record<Band, number>;
  as_of: string; cells: AccumulationCell[];
}

export interface ReviewPayload {
  reviewer_role: string;
  decision: "confirm" | "override";
  reason: string;
  corrected_classification?: SifClassification;
  corrected_energy_source?: EnergySource;
  corrected_control_status?: ControlStatus;
  corrected_primary_lsr?: LifeSavingRule;
}
