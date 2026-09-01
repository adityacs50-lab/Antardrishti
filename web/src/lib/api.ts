/// <reference types="vite/client" />
/**
 * The one and only source of verdicts: the local API.
 *
 * There is deliberately NO client-side fallback and NO mock data. A second
 * implementation of the rule engine in TypeScript would drift from the Python
 * one, and the moment it did, this UI would display a verdict the audited
 * engine never produced — which destroys the only claim the product makes.
 * Likewise, silently substituting sample data when the backend is down would
 * put fabricated safety verdicts on screen with no indication they are fake.
 *
 * So: if the API is unreachable, every call throws and the UI says so.
 */

import type {
  AccumulationOut, AnalyzeResult, BarriersOut, DensityOut, LsrOut, Meta,
  Page, ReportDetail, ReportSummary, ReviewPayload, SifClassification,
  EnergySource, LifeSavingRule,
} from "@/types/api";

const BASE = (import.meta.env?.VITE_API_BASE_URL as string | undefined) ?? "";

export class ApiError extends Error {
  constructor(message: string, readonly status?: number, readonly detail?: unknown) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = 15000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { Accept: "application/json", ...(init?.headers ?? {}) },
    });
  } catch (err) {
    clearTimeout(timer);
    if ((err as Error).name === "AbortError") {
      throw new ApiError(`Request to ${path} timed out.`);
    }
    throw new ApiError(
      "Cannot reach the prahari API. Start it with: uvicorn prahari.main:app --reload",
    );
  }
  clearTimeout(timer);

  if (!res.ok) {
    let detail: unknown;
    try { detail = (await res.json())?.detail; } catch { /* non-JSON error body */ }
    throw new ApiError(
      typeof detail === "string" ? detail : `${res.status} ${res.statusText}`,
      res.status,
      detail,
    );
  }
  return (await res.json()) as T;
}

function qs(params: object): string {
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(params as Record<string, unknown>)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) value.forEach((v) => sp.append(key, String(v)));
    else sp.append(key, String(value));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export interface ReportFilters {
  classification?: SifClassification[];
  lsr?: LifeSavingRule[];
  site?: string[];
  energy_source?: EnergySource[];
  date_from?: string;
  date_to?: string;
  min_confidence?: number;
  reviewed?: boolean;
  limit?: number;
  offset?: number;
}

export const api = {
  health: () =>
    request<{
      status: string;
      engine_version: string;
      extractor_version: string;
      offline: string;
      extractor: "NEURAL" | "KEYWORD";
      extractor_detail: string;
      model_present: boolean;
      report_count: number | string;
    }>("/health"),
  meta: () => request<Meta>("/api/meta"),

  triage: (p: { site?: string[]; include_actual_events?: boolean; limit?: number; offset?: number } = {}) =>
    request<Page<ReportSummary>>(`/api/triage${qs(p)}`),

  reports: (p: ReportFilters = {}) => request<Page<ReportSummary>>(`/api/reports${qs(p)}`),

  report: (id: number) => request<ReportDetail>(`/api/reports/${id}`),

  analyze: (text: string) =>
    request<AnalyzeResult>("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }),

  review: (id: number, payload: ReviewPayload) =>
    request<ReportDetail>(`/api/reports/${id}/review`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  density: (p: { date_from?: string; date_to?: string } = {}) =>
    request<DensityOut>(`/api/analytics/density${qs(p)}`),

  lsr: (p: { date_from?: string; date_to?: string; site?: string } = {}) =>
    request<LsrOut>(`/api/analytics/lsr${qs(p)}`),

  barriers: (p: { window_days?: number; site?: string; limit?: number } = {}) =>
    request<BarriersOut>(`/api/analytics/barriers${qs(p)}`),

  accumulation: (p: { window_days?: number; site?: string; min_index?: number } = {}) =>
    request<AccumulationOut>(`/api/analytics/accumulation${qs(p)}`),
};
