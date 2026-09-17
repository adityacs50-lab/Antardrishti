import { useState } from "react";
import { Download, FileSpreadsheet, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import {
  CLASSIFICATION_LABEL, CONTROL_STATUS_LABEL, ENERGY_LABEL, LSR_LABEL, formatDate,
} from "@/lib/format";
import type { ReportSummary } from "@/types/api";

/**
 * Export for HSE — the Triage Queue as it is currently filtered, every page,
 * as a CSV or a print-ready summary (the browser's "Save as PDF").
 *
 * Built entirely in the browser from the same /api/triage rows the table
 * shows, so the export can never disagree with the screen. No PDF library:
 * the app ships no network dependencies, and the print dialog already writes
 * PDFs on every OS.
 */

const PAGE = 500; // the API's max page size
const HARD_CAP = 5000;

async function fetchAll(site: string, includeEvents: boolean): Promise<{ items: ReportSummary[]; total: number }> {
  const items: ReportSummary[] = [];
  let total = 0;
  for (let offset = 0; offset < HARD_CAP; offset += PAGE) {
    const page = await api.triage({
      site: site ? [site] : undefined,
      include_actual_events: includeEvents,
      limit: PAGE,
      offset,
    });
    total = page.total;
    items.push(...page.items);
    if (items.length >= total || page.items.length === 0) break;
  }
  return { items, total };
}

const COLUMNS: { head: string; get: (r: ReportSummary) => string }[] = [
  { head: "Priority", get: (r) => String(r.triage_rank) },
  { head: "Report ID", get: (r) => r.report_uid },
  { head: "Date", get: (r) => r.date },
  { head: "Site", get: (r) => r.site },
  { head: "Activity", get: (r) => r.activity ?? "" },
  { head: "Classification", get: (r) => CLASSIFICATION_LABEL[r.classification] },
  { head: "Energy", get: (r) => (r.energy_source ? ENERGY_LABEL[r.energy_source] : "") },
  { head: "Barrier", get: (r) => CONTROL_STATUS_LABEL[r.control_status] },
  { head: "Primary LSR", get: (r) => (r.primary_lsr ? LSR_LABEL[r.primary_lsr] : "") },
  { head: "Evidence (of 4)", get: (r) => String(Math.round(r.evidence_completeness * 4)) },
  { head: "Reviewed", get: (r) => (r.reviewed ? "yes" : "no") },
  { head: "Engine reason", get: (r) => r.reason },
  { head: "Excerpt", get: (r) => r.excerpt },
];

function csvCell(v: string) {
  // Guard against spreadsheet formula injection from free-text report fields.
  const safe = /^[=+\-@]/.test(v) ? `'${v}` : v;
  return /[",\n\r]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
}

function stamp() {
  // Digits only, e.g. 202609171342. Keep this regex free of bracketed
  // colons: Tailwind's class scanner reads those as arbitrary CSS properties.
  return new Date().toISOString().slice(0, 16).replace(/\D/g, "");
}

function download(filename: string, body: string, type: string) {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const esc = (s: string) =>
  s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

function printableHtml(items: ReportSummary[], scope: string) {
  const counts = new Map<string, number>();
  items.forEach((r) => counts.set(CLASSIFICATION_LABEL[r.classification], (counts.get(CLASSIFICATION_LABEL[r.classification]) ?? 0) + 1));
  const pending = items.filter((r) => !r.reviewed).length;
  const rows = items
    .map(
      (r) => `<tr>
        <td class="n">${r.triage_rank}</td>
        <td><b>${esc(r.site)}</b><br><span class="m">${esc(r.report_uid)} · ${esc(formatDate(r.date))}</span></td>
        <td>${esc(CLASSIFICATION_LABEL[r.classification])}</td>
        <td>${esc(r.energy_source ? ENERGY_LABEL[r.energy_source] : "—")} / ${esc(CONTROL_STATUS_LABEL[r.control_status])}</td>
        <td>${esc(r.primary_lsr ? LSR_LABEL[r.primary_lsr] : "—")}</td>
        <td>${esc(r.reason)}<br><span class="m">${esc(r.excerpt)}</span></td>
      </tr>`,
    )
    .join("");
  return `<!doctype html><html><head><meta charset="utf-8"><title>prahari HSE export ${stamp()}</title>
<style>
  body{font:11px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:#111;margin:24px}
  h1{font-size:17px;margin:0 0 2px} .m{color:#666;font-size:10px}
  .sum{display:flex;gap:18px;margin:12px 0 14px;padding:8px 0;border-top:2px solid #d95926;border-bottom:1px solid #ddd}
  .sum b{display:block;font-size:16px}
  table{width:100%;border-collapse:collapse} th,td{border-bottom:1px solid #ddd;padding:5px 6px;text-align:left;vertical-align:top}
  th{font-size:9px;text-transform:uppercase;letter-spacing:.04em;color:#555;border-bottom:1px solid #999}
  td.n{font-weight:700;text-align:center} tr{page-break-inside:avoid}
  footer{margin-top:14px;color:#666;font-size:9px}
</style></head><body>
<h1>prahari · SIF precursor summary for HSE</h1>
<div class="m">SIH26165 · Oil India Limited · generated ${esc(new Date().toLocaleString("en-IN"))} · scope: ${esc(scope)}</div>
<div class="sum">
  <div><b>${items.length}</b>reports</div>
  ${[...counts].map(([k, v]) => `<div><b>${v}</b>${esc(k)}</div>`).join("")}
  <div><b>${pending}</b>pending review</div>
</div>
<table><thead><tr><th>Rank</th><th>Site / report</th><th>Class</th><th>Energy / barrier</th><th>Primary LSR</th><th>Why (engine) / excerpt</th></tr></thead>
<tbody>${rows}</tbody></table>
<footer>Every classification above was produced by the deterministic prahari rule engine and is traceable to named rules and text spans in the app. Priority is a fixed triage table, not a model score.</footer>
<script>window.onload=function(){setTimeout(function(){window.print()},200)}</script>
</body></html>`;
}

export function ExportForHSE({ site, includeEvents, total }: { site: string; includeEvents: boolean; total: number }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<"csv" | "pdf" | null>(null);
  const [error, setError] = useState<string>();
  const scope = `${site || "All sites"} · ${includeEvents ? "precursors + actual events" : "precursors (PSIF, Exposure)"}`;

  const exportCsv = async () => {
    setBusy("csv");
    setError(undefined);
    try {
      const { items } = await fetchAll(site, includeEvents);
      const body = [COLUMNS.map((c) => c.head), ...items.map((r) => COLUMNS.map((c) => c.get(r)))]
        .map((row) => row.map(csvCell).join(","))
        .join("\r\n");
      // BOM so Excel opens Devanagari/Assamese text correctly.
      download(`prahari-hse-${site || "all"}-${stamp()}.csv`, "﻿" + body, "text/csv;charset=utf-8");
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  const exportPdf = async () => {
    // Open synchronously inside the click, or popup blockers eat it.
    const win = window.open("", "_blank");
    if (!win) {
      setError("The browser blocked the print window. Allow pop-ups for this page and try again.");
      return;
    }
    win.document.write("<p style='font:13px system-ui;padding:24px'>Preparing HSE summary…</p>");
    setBusy("pdf");
    setError(undefined);
    try {
      const { items } = await fetchAll(site, includeEvents);
      win.document.open();
      win.document.write(printableHtml(items, scope));
      win.document.close();
      setOpen(false);
    } catch (e) {
      win.close();
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setError(undefined); }}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" disabled={total === 0}>
          <Download /> Export for HSE
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Export for HSE</DialogTitle>
          <DialogDescription>
            Exports the queue exactly as filtered now — {total} report{total === 1 ? "" : "s"}, ranked
            by priority.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3 px-5 py-4">
          <p className="text-2xs text-ink-faint">Scope: <span className="text-ink-muted">{scope}</span></p>
          <div className="grid gap-2 sm:grid-cols-2">
            <Button variant="secondary" onClick={() => void exportPdf()} disabled={busy !== null}>
              {busy === "pdf" ? <Loader2 className="animate-spin" /> : <FileText />}
              PDF summary
            </Button>
            <Button variant="secondary" onClick={() => void exportCsv()} disabled={busy !== null}>
              {busy === "csv" ? <Loader2 className="animate-spin" /> : <FileSpreadsheet />}
              CSV (Excel)
            </Button>
          </div>
          <p className="text-2xs leading-relaxed text-ink-faint">
            PDF opens a print-ready summary — choose “Save as PDF” in the print dialog. CSV includes
            the engine's reason and evidence count for every row.
          </p>
          {error && (
            <p className="border border-status-warning/40 bg-status-warning/10 px-3 py-2 text-xs text-status-warning">
              {error}
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
