import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, CheckCircle2, Filter, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { ClassificationBadge, ConfidencePill, ControlBadge, LsrBadge } from "@/components/Chips";
import { NewReportDialog } from "@/components/NewReportDialog";
import { QueryBoundary } from "@/components/StateViews";
import { LiveAnalysisPanel } from "./LiveAnalysisPanel";
import { api } from "@/lib/api";
import { useQuery } from "@/lib/useQuery";
import { daysAgo, formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ReportSummary } from "@/types/api";

const PAGE_SIZE = 25;

function QueueRow({ report }: { report: ReportSummary }) {
  return (
    <Link
      to={`/reports/${report.id}`}
      className={cn(
        "group grid grid-cols-[auto_1fr_auto] items-start gap-4 border-b border-line px-4 py-3.5 transition-colors last:border-b-0 hover:bg-surface-raised",
      )}
    >
      <span
        className="tnum mt-0.5 w-9 text-right text-sm font-semibold text-ink-faint"
        title="Triage rank — a fixed table over the engine's own classes and control states, not a model score"
      >
        {report.triage_rank}
      </span>

      <div className="min-w-0 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <ClassificationBadge value={report.classification} />
          <LsrBadge value={report.primary_lsr} />
          <ControlBadge value={report.control_status} />
          {report.reviewed && (
            <span className="inline-flex items-center gap-1 text-2xs text-status-good">
              <CheckCircle2 className="size-3" /> Reviewed
            </span>
          )}
        </div>
        <p className="truncate text-xs text-ink-muted" title={report.reason}>
          {report.reason}
        </p>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-2xs text-ink-faint">
          <span className="font-medium text-ink-muted">{report.site}</span>
          <span>{formatDate(report.date)}</span>
          <span className="opacity-70">{daysAgo(report.date)}</span>
          {report.activity && <span className="truncate">{report.activity}</span>}
        </div>
      </div>

      <div className="flex items-center gap-3 pt-0.5">
        <ConfidencePill value={report.evidence_completeness} />
        <ArrowRight className="size-4 text-ink-faint transition-transform group-hover:translate-x-0.5 group-hover:text-ink" />
      </div>
    </Link>
  );
}

export function TriageView() {
  const [params, setParams] = useSearchParams();
  const site = params.get("site") ?? "";
  const [includeEvents, setIncludeEvents] = useState(false);
  const [page, setPage] = useState(0);

  const meta = useQuery(() => api.meta(), []);
  const query = useMemo(
    () => ({
      site: site ? [site] : undefined,
      include_actual_events: includeEvents,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }),
    [site, includeEvents, page],
  );
  const triage = useQuery(() => api.triage(query), [site, includeEvents, page]);

  const total = triage.data?.total ?? 0;
  const shown = triage.data?.items.length ?? 0;

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
      <section className="space-y-3">
        <header className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <h1 className="flex items-center gap-2 text-lg font-semibold tracking-tight text-ink">
              <TriangleAlert className="size-5 text-status-serious" />
              Triage Queue
            </h1>
            <p className="text-xs text-ink-muted">
              Uncontrolled fatal potential, ranked highest first. Nobody was necessarily hurt in any
              of these — that is the point.
            </p>
          </div>
          <NewReportDialog
            sites={meta.data?.sites ?? []}
            activities={meta.data?.activities ?? []}
            onSubmitted={() => { triage.refetch(); meta.refetch(); }}
          />
        </header>

        <Card>
          <CardHeader className="flex-row flex-wrap items-center gap-3 space-y-0 py-2.5">
            <span className="inline-flex items-center gap-1.5 text-2xs text-ink-faint">
              <Filter className="size-3.5" /> Filter
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
            <label className="inline-flex cursor-pointer items-center gap-2 text-2xs text-ink-muted">
              <input
                type="checkbox"
                checked={includeEvents}
                onChange={(e) => { setIncludeEvents(e.target.checked); setPage(0); }}
                className="size-3.5 accent-[#3987e5]"
              />
              Include actual events (HSIF / LSIF)
            </label>
            <span className="tnum ml-auto text-2xs text-ink-faint">
              {total} report{total === 1 ? "" : "s"}
            </span>
          </CardHeader>

          <QueryBoundary
            loading={triage.loading}
            offline={triage.offline}
            error={triage.error}
            empty={shown === 0}
            onRetry={triage.refetch}
            emptyTitle="No SIF potential in the queue"
            emptyHint="Either nothing qualifies, or the database is empty. Seed it with: python -m prahari.cli seed --limit 800"
          >
            <div>
              {triage.data?.items.map((r) => <QueueRow key={r.id} report={r} />)}
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

      <section className="xl:sticky xl:top-[76px] xl:self-start">
        <LiveAnalysisPanel />
      </section>
    </div>
  );
}
