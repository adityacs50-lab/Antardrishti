import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CheckCircle2, Filter, TriangleAlert, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { EnergyBarrierBadge, LsrBadge } from "@/components/Chips";
import { BulkImportDialog } from "@/components/BulkImportDialog";
import { NewReportDialog } from "@/components/NewReportDialog";
import { QueryBoundary } from "@/components/StateViews";
import { KpiBar } from "@/components/KpiBar";
import { AuditDrawer } from "@/components/AuditDrawer";
import { ExportForHSE } from "@/components/ExportForHSE";
import { InsightsBar } from "@/components/InsightsBar";
import { api } from "@/lib/api";
import { useQuery } from "@/lib/useQuery";
import { CLASSIFICATION_LABEL, CLASSIFICATION_MEANING, LSR_LABEL, formatDate } from "@/lib/format";
import { CLASSIFICATION_TONE } from "@/lib/theme";
import type { LifeSavingRule, ReportSummary } from "@/types/api";

const PAGE_SIZE = 25;

/**
 * Column 1, "Priority & Site". The rank number carries classification as a
 * colour, not as a fourth badge — the table brief asks for exactly five
 * columns, so what used to be a standalone classification chip is folded
 * into the one element that was always about priority anyway. Full wording
 * is a hover away; nothing is lost, just deferred.
 */
function PriorityCell({ report }: { report: ReportSummary }) {
  const tone = CLASSIFICATION_TONE[report.classification];
  return (
    <div className="flex items-start gap-3">
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className="tnum flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold"
            style={{ color: tone.fg, backgroundColor: tone.bg, boxShadow: `inset 0 0 0 1px ${tone.ring}` }}
          >
            {report.triage_rank}
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <strong>{CLASSIFICATION_LABEL[report.classification]}.</strong>{" "}
          {CLASSIFICATION_MEANING[report.classification]}
        </TooltipContent>
      </Tooltip>
      <div className="min-w-0 space-y-0.5">
        <div className="flex items-center gap-1.5">
          <span className="truncate text-xs font-medium text-ink">{report.site}</span>
          {report.reviewed && (
            <Tooltip>
              <TooltipTrigger asChild>
                <span><CheckCircle2 className="size-3 shrink-0 text-status-good" /></span>
              </TooltipTrigger>
              <TooltipContent>Reviewed</TooltipContent>
            </Tooltip>
          )}
        </div>
        <span className="block font-mono text-2xs text-ink-faint">{report.report_uid}</span>
        <span className="block text-2xs text-ink-faint">{formatDate(report.date)}</span>
      </div>
    </div>
  );
}

/** Column 2, "Activity & Excerpt". */
function ActivityExcerptCell({ report }: { report: ReportSummary }) {
  return (
    <div className="max-w-sm space-y-1">
      {report.activity && (
        <span className="inline-block rounded border border-line bg-surface-sunken px-1.5 py-0.5 text-2xs text-ink-muted">
          {report.activity}
        </span>
      )}
      <p className="line-clamp-2 text-xs leading-relaxed text-ink-muted" title={report.excerpt}>
        {report.excerpt}
      </p>
    </div>
  );
}

/** Below `md` the five-column table cannot fit; the same facts stack as a card. */
function QueueCard({ report, onAudit }: { report: ReportSummary; onAudit: (id: number) => void }) {
  return (
    <li className="space-y-2.5 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <PriorityCell report={report} />
        <Button variant="outline" size="sm" onClick={() => onAudit(report.id)}>
          Audit
        </Button>
      </div>
      <ActivityExcerptCell report={report} />
      <div className="flex flex-wrap items-center gap-1.5">
        <LsrBadge
          value={report.primary_lsr}
          energySource={report.energy_source}
          classification={report.classification}
        />
        <EnergyBarrierBadge energySource={report.energy_source} controlStatus={report.control_status} />
      </div>
    </li>
  );
}

function QueueRow({ report, onAudit }: { report: ReportSummary; onAudit: (id: number) => void }) {
  return (
    <tr className="border-b border-line transition-colors last:border-b-0 hover:bg-surface-raised">
      <td className="px-4 py-3 align-top">
        <PriorityCell report={report} />
      </td>
      <td className="px-4 py-3 align-top">
        <ActivityExcerptCell report={report} />
      </td>
      <td className="px-4 py-3 align-top">
        <LsrBadge
          value={report.primary_lsr}
          energySource={report.energy_source}
          classification={report.classification}
        />
      </td>
      <td className="px-4 py-3 align-top">
        <EnergyBarrierBadge energySource={report.energy_source} controlStatus={report.control_status} />
      </td>
      <td className="px-4 py-3 align-top text-right">
        <Button variant="outline" size="sm" onClick={() => onAudit(report.id)}>
          Audit
        </Button>
      </td>
    </tr>
  );
}

export function TriageView() {
  const [params, setParams] = useSearchParams();
  const site = params.get("site") ?? "";
  // Set by "View reports under this rule" on the Life-Saving Rules screen.
  const lsrParam = params.get("lsr");
  const lsr = lsrParam && lsrParam in LSR_LABEL ? (lsrParam as LifeSavingRule) : "";
  const [includeEvents, setIncludeEvents] = useState(false);
  const [page, setPage] = useState(0);
  const [auditId, setAuditId] = useState<number | null>(null);

  const meta = useQuery(() => api.meta(), []);
  const query = useMemo(
    () => ({
      site: site ? [site] : undefined,
      lsr: lsr ? [lsr] : undefined,
      include_actual_events: includeEvents,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }),
    [site, lsr, includeEvents, page],
  );
  const triage = useQuery(() => api.triage(query), [site, lsr, includeEvents, page]);

  const total = triage.data?.total ?? 0;
  const shown = triage.data?.items.length ?? 0;

  const refreshAll = () => {
    triage.refetch();
    meta.refetch();
    window.dispatchEvent(new Event("prahari:data-changed"));
  };

  return (
    <div className="space-y-6">
      <div className="hero-strip animate-fade-in">
        <span className="border border-accent/40 bg-accent/15 px-2 py-0.5 text-2xs font-normal uppercase tracking-wide text-accent">
          Thesis
        </span>
        <p className="text-sm text-ink">
          <span className="font-semibold">Potential ≠ severity</span>
          <span className="text-ink-muted"> — we rank fatal energy with a missing barrier.</span>
        </p>
      </div>

      {/* KPI bar: the four numbers a reviewer checks before opening a
          single row. */}
      <KpiBar />

      {/* One slim row: measured engine numbers + the most urgent barrier
          action. Full detail opens in a side panel. */}
      <InsightsBar />

      <section className="space-y-3">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-base font-semibold tracking-tight text-ink">
            <TriangleAlert className="size-4 text-status-serious" />
            Triage Queue
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <ExportForHSE site={site} lsr={lsr || undefined} includeEvents={includeEvents} total={total} />
            <BulkImportDialog onImported={refreshAll} />
            <NewReportDialog
              sites={meta.data?.sites ?? []}
              activities={meta.data?.activities ?? []}
              onSubmitted={refreshAll}
            />
          </div>
        </header>

        <Card>
          <CardHeader className="flex-row flex-wrap items-center gap-3 space-y-0 py-2.5">
            <span className="inline-flex items-center gap-1.5 text-2xs text-ink-faint">
              <Filter className="size-3.5" /> Site
            </span>
            <Select
              aria-label="Site"
              value={site}
              onChange={(e) => {
                const next = new URLSearchParams(params);
                e.target.value ? next.set("site", e.target.value) : next.delete("site");
                setParams(next, { replace: true });
                setPage(0);
              }}
              className="h-8 max-w-[190px] text-xs"
            >
              <option value="">All sites</option>
              {meta.data?.sites.map((s) => <option key={s} value={s}>{s}</option>)}
            </Select>
            {lsr && (
              <button
                type="button"
                onClick={() => {
                  const next = new URLSearchParams(params);
                  next.delete("lsr");
                  setParams(next, { replace: true });
                  setPage(0);
                }}
                className="inline-flex h-8 items-center gap-1.5 border border-accent/40 bg-accent/10 px-2.5 text-2xs text-ink transition-colors hover:bg-accent/20"
                aria-label={`Remove rule filter: ${LSR_LABEL[lsr]}`}
              >
                Rule: {LSR_LABEL[lsr]}
                <X className="size-3" />
              </button>
            )}
            <label className="ml-auto inline-flex cursor-pointer items-center gap-2 text-2xs text-ink-faint">
              <input
                type="checkbox"
                checked={includeEvents}
                onChange={(e) => { setIncludeEvents(e.target.checked); setPage(0); }}
                className="size-3.5 accent-[#3987e5]"
              />
              Include actual events
            </label>
            <span className="tnum text-2xs text-ink-faint">
              {total} report{total === 1 ? "" : "s"}
            </span>
          </CardHeader>

          <QueryBoundary
            loading={triage.loading}
            offline={triage.offline}
            error={triage.error}
            empty={shown === 0}
            onRetry={triage.refetch}
            emptyTitle={site || lsr ? "No reports match these filters" : "No SIF potential in the queue"}
            emptyHint={
              site || lsr
                ? "Clear the site or rule filter, or tick “Include actual events”."
                : "Nothing qualifies yet. Add a report or bulk-import a CSV export to get started."
            }
          >
            <ul className="divide-y divide-line md:hidden">
              {triage.data?.items.map((r) => (
                <QueueCard key={r.id} report={r} onAudit={setAuditId} />
              ))}
            </ul>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-line-strong text-2xs uppercase tracking-wide text-ink-faint">
                    <th className="px-4 py-2 font-medium">Priority &amp; Site</th>
                    <th className="px-4 py-2 font-medium">Activity &amp; Excerpt</th>
                    <th className="px-4 py-2 font-medium">Primary LSR Tag</th>
                    <th className="px-4 py-2 font-medium">Energy &amp; Barrier Status</th>
                    <th className="px-4 py-2 text-right font-medium">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {triage.data?.items.map((r) => (
                    <QueueRow key={r.id} report={r} onAudit={setAuditId} />
                  ))}
                </tbody>
              </table>
            </div>
            {total > PAGE_SIZE && (
              <div className="flex items-center justify-between border-t border-line px-4 py-2.5">
                <span className="tnum text-2xs text-ink-faint">
                  {page * PAGE_SIZE + 1}–{page * PAGE_SIZE + shown} of {total}
                </span>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={(page + 1) * PAGE_SIZE >= total}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </QueryBoundary>
        </Card>
      </section>

      {/* Slide-over Audit drawer — everything the row used to show inline
          (confidence, fired rules, governing rule detail) plus the audit
          controls, without leaving the queue. */}
      <AuditDrawer
        reportId={auditId}
        open={auditId !== null}
        onOpenChange={(v) => { if (!v) setAuditId(null); }}
        onReviewed={refreshAll}
      />
    </div>
  );
}
