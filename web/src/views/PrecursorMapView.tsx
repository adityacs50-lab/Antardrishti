import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Flame, Grid3x3, Info, TrendingDown, TrendingUp, Minus } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { BandBadge } from "@/components/Chips";
import { QueryBoundary } from "@/components/StateViews";
import { AccumulationTrend } from "@/components/charts/AccumulationTrend";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useQuery } from "@/lib/useQuery";
import { densityFill, densityInk, TREND_TONE } from "@/lib/theme";
import { ENERGY_LABEL, TREND_LABEL, pct } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AccumulationCell, Trend } from "@/types/api";

const WINDOW = 365;

function TrendIcon({ trend }: { trend: Trend }) {
  const Icon = trend === "rising" ? TrendingUp : trend === "falling" ? TrendingDown : Minus;
  return <Icon className="size-3.5" style={{ color: TREND_TONE[trend] }} />;
}

function AccumulationRow({ cell, onOpen }: { cell: AccumulationCell; onOpen: (site: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const top = cell.signatures[0];
  return (
    <li className="border-b border-line last:border-b-0">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-raised"
      >
        <span className="tnum mt-0.5 w-12 shrink-0 text-right text-sm font-semibold text-ink">
          {cell.index.toFixed(1)}
        </span>
        <span className="min-w-0 flex-1 space-y-1.5">
          <span className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-ink">{cell.site}</span>
            <span className="text-2xs text-ink-muted">{ENERGY_LABEL[cell.energy_source]}</span>
            <BandBadge value={cell.band} />
            <span className="inline-flex items-center gap-1 text-2xs" style={{ color: TREND_TONE[cell.trend] }}>
              <TrendIcon trend={cell.trend} /> {TREND_LABEL[cell.trend]}
            </span>
            {cell.max_repeat > 1 && (
              <span className="rounded border border-status-critical/40 bg-status-critical/10 px-1.5 py-0.5 text-2xs font-medium text-status-critical">
                same barrier ×{cell.max_repeat}
              </span>
            )}
          </span>
          {top && (
            <span className="block truncate text-2xs text-ink-muted">
              {top.control_label} — {top.control_status.replace(/_/g, " ")}
            </span>
          )}
        </span>
      </button>

      {expanded && (
        <div className="animate-fade-in space-y-3 bg-surface-sunken px-4 pb-4 pt-1">
          <p className="text-xs leading-relaxed text-ink-muted">{cell.explanation}</p>
          {cell.signatures.map((sig) => (
            <div key={`${sig.control_key}-${sig.control_status}`} className="rounded-md border border-line p-2.5">
              <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-2xs font-medium text-ink">
                  {sig.control_label} · {sig.control_status.replace(/_/g, " ")}
                </span>
                <span className="tnum text-2xs text-ink-faint">
                  {sig.occurrences}× → contributes {sig.contribution.toFixed(1)}
                </span>
              </div>
              <ul className="space-y-0.5">
                {sig.contributors.map((c) => (
                  <li key={c.report_id} className="flex items-center justify-between gap-2 text-2xs">
                    <button
                      onClick={() => onOpen(String(c.report_id))}
                      className="font-mono text-series-1 hover:underline"
                    >
                      {c.report_uid}
                    </button>
                    <span className="tnum text-ink-faint">
                      {c.date} · {c.age_days}d · weight {c.decayed_weight.toFixed(2)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <p className="text-2xs italic text-ink-faint">
            Every number above is reproducible by hand from these report ids and weights.
          </p>
        </div>
      )}
    </li>
  );
}

export function PrecursorMapView() {
  const navigate = useNavigate();
  const density = useQuery(() => api.density(), []);
  const accumulation = useQuery(() => api.accumulation({ window_days: WINDOW }), []);

  const grid = useMemo(() => {
    if (!density.data) return null;
    const { sites, activities, cells } = density.data;
    const lookup = new Map(cells.map((c) => [`${c.site}|${c.activity}`, c]));
    // Busiest activities first, so the heatmap does not open on empty columns.
    const ranked = [...activities].sort((a, b) => {
      const sum = (act: string) =>
        sites.reduce((n, s) => n + (lookup.get(`${s}|${act}`)?.precursor_count ?? 0), 0);
      return sum(b) - sum(a);
    });
    return { sites, activities: ranked, lookup };
  }, [density.data]);

  const alerts = (accumulation.data?.cells ?? []).filter(
    (c) => c.band === "high" || c.band === "critical",
  );

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="flex items-center gap-2 text-lg font-semibold tracking-tight text-ink">
          <Grid3x3 className="size-5 text-series-1" />
          Precursor Map
        </h1>
        <p className="text-xs text-ink-muted">
          Where uncontrolled fatal potential concentrates, and where the same barrier keeps failing.
        </p>
      </header>

      {alerts.length > 0 && (
        <div className="animate-slide-up rounded-lg border border-status-critical/45 bg-status-critical/10 p-4">
          <div className="flex items-start gap-3">
            <Flame className="mt-0.5 size-5 shrink-0 text-status-critical" />
            <div className="min-w-0 space-y-1.5">
              <p className="text-sm font-semibold text-ink">
                {alerts.length} site–energy pair{alerts.length === 1 ? "" : "s"} above the
                escalation threshold
              </p>
              <ul className="space-y-1">
                {alerts.slice(0, 4).map((c) => (
                  <li key={`${c.site}-${c.energy_source}`} className="text-xs leading-relaxed text-ink-muted">
                    <strong className="text-ink">
                      {c.site} · {ENERGY_LABEL[c.energy_source]}
                    </strong>{" "}
                    — index {c.index.toFixed(1)}
                    {c.max_repeat > 1 && <> · the same barrier failed {c.max_repeat} times</>}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Precursor density — site × activity</CardTitle>
            <CardDescription>
              Share of reports for that pair that came back as uncontrolled fatal potential. Click a
              cell to filter the triage queue.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <QueryBoundary
              loading={density.loading}
              offline={density.offline}
              error={density.error}
              empty={!grid || grid.sites.length === 0}
              onRetry={density.refetch}
              emptyTitle="No reports to map yet"
              emptyHint="Seed the database: python -m prahari.cli seed --limit 800"
              skeleton={<Skeleton className="m-4 h-64" />}
            >
              {grid && (
                <div className="overflow-x-auto p-4">
                  <table className="w-full border-separate border-spacing-[2px] text-2xs">
                    <thead>
                      <tr>
                        <th className="sticky left-0 z-10 bg-surface px-2 py-1 text-left font-medium text-ink-faint">
                          Activity
                        </th>
                        {grid.sites.map((s) => (
                          <th key={s} className="px-1 py-1 text-center font-medium text-ink-muted">
                            <span className="inline-block max-w-[62px] truncate" title={s}>{s}</span>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {grid.activities.map((activity) => (
                        <tr key={activity}>
                          <td
                            className="sticky left-0 z-10 max-w-[200px] truncate bg-surface px-2 py-1 text-ink-muted"
                            title={activity}
                          >
                            {activity}
                          </td>
                          {grid.sites.map((site) => {
                            const cell = grid.lookup.get(`${site}|${activity}`);
                            const total = cell?.total_reports ?? 0;
                            const rate = cell?.precursor_rate ?? 0;
                            return (
                              <td key={site} className="p-0">
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <button
                                      disabled={total === 0}
                                      onClick={() => navigate(`/?site=${encodeURIComponent(site)}`)}
                                      className={cn(
                                        "tnum h-8 w-full rounded-[3px] text-center font-medium transition-transform",
                                        total > 0 && "hover:scale-[1.12] hover:ring-2 hover:ring-ink/30",
                                      )}
                                      style={{
                                        backgroundColor: densityFill(rate, total),
                                        color: densityInk(rate, total),
                                      }}
                                    >
                                      {total > 0 ? cell!.precursor_count : ""}
                                    </button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <strong>{site}</strong> · {activity}
                                    <br />
                                    {total === 0 ? (
                                      "No reports"
                                    ) : (
                                      <>
                                        {cell!.precursor_count} of {total} reports were precursors (
                                        {pct(rate)})
                                      </>
                                    )}
                                  </TooltipContent>
                                </Tooltip>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <div className="mt-3 flex items-center gap-2">
                    <span className="text-2xs text-ink-faint">Precursor rate</span>
                    <span className="flex gap-[2px]">
                      {[0, 0.15, 0.35, 0.55, 0.75, 0.95].map((r) => (
                        <span key={r} className="h-3 w-6 rounded-[2px]"
                          style={{ backgroundColor: densityFill(r, 1) }} />
                      ))}
                    </span>
                    <span className="text-2xs text-ink-faint">0% → 100%</span>
                  </div>
                </div>
              )}
            </QueryBoundary>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-2">
              <div className="space-y-1">
                <CardTitle>Precursor Accumulation Index</CardTitle>
                <CardDescription>
                  Rises when the <em>same</em> barrier fails repeatedly at the <em>same</em> place.
                </CardDescription>
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span><Info className="size-4 text-ink-faint" /></span>
                </TooltipTrigger>
                <TooltipContent>
                  Only precursors and actual events contribute. Each is time-decayed (45-day half
                  life) and grouped by barrier signature; a signature's count is raised to an
                  exponent above 1, and the strongest signature dominates — so four failures of one
                  barrier outscore four failures of four different barriers.
                </TooltipContent>
              </Tooltip>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <QueryBoundary
              loading={accumulation.loading}
              offline={accumulation.offline}
              error={accumulation.error}
              empty={(accumulation.data?.cells.length ?? 0) === 0}
              onRetry={accumulation.refetch}
              emptyTitle="No accumulating precursors"
              emptyHint="Nothing is repeating at any site yet — which is good news."
              skeleton={<Skeleton className="m-4 h-64" />}
            >
              {accumulation.data && (
                <>
                  <div className="border-b border-line p-4">
                    <AccumulationTrend cells={accumulation.data.cells} />
                  </div>
                  <ul className="max-h-[420px] overflow-y-auto">
                    {accumulation.data.cells.slice(0, 25).map((cell) => (
                      <AccumulationRow
                        key={`${cell.site}-${cell.energy_source}`}
                        cell={cell}
                        onOpen={(reportId) => navigate(`/reports/${reportId}`)}
                      />
                    ))}
                  </ul>
                </>
              )}
            </QueryBoundary>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
