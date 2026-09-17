import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight, Gauge, ListTodo } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sheet, SheetBody, SheetContent, SheetDescription, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import { BandBadge } from "@/components/Chips";
import { EngineMetricsCard } from "@/components/EngineMetricsCard";
import { RecommendedActions, buildRecommendations } from "@/components/RecommendedActions";
import { api } from "@/lib/api";
import { useQuery } from "@/lib/useQuery";
import { pct } from "@/lib/format";

/**
 * One slim row on the Triage Queue: the engine's measured headline numbers and
 * the single most urgent barrier action. The full Engine Performance card and
 * the full action list open in a side panel, so the queue stays the first
 * thing on the page.
 */
export function InsightsBar() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const metrics = useQuery(() => api.engineMetrics(), []);
  const accumulation = useQuery(() => api.accumulation({ window_days: 365 }), []);
  const density = useQuery(() => api.density(), []);

  const refetch = metrics.refetch;
  const refetchAcc = accumulation.refetch;
  useEffect(() => {
    const on = () => { refetch(); refetchAcc(); };
    window.addEventListener("prahari:data-changed", on);
    return () => window.removeEventListener("prahari:data-changed", on);
  }, [refetch, refetchAcc]);

  const bench = metrics.data?.benchmark;
  const pd = bench?.splits[bench.headline_split].precursor_detection;
  const recs = useMemo(
    () => buildRecommendations(accumulation.data?.cells ?? [], density.data),
    [accumulation.data, density.data],
  );
  const top = recs[0];

  return (
    <>
      <Card className="animate-fade-in flex flex-col divide-y divide-line text-xs lg:flex-row lg:items-stretch lg:divide-x lg:divide-y-0">
        {/* Engine headline */}
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="group flex min-w-0 items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent/50"
          aria-label="Open engine performance details"
        >
          <Gauge className="size-4 shrink-0 text-series-1" />
          <span className="shrink-0 text-2xs uppercase tracking-wide text-ink-faint">Engine</span>
          {metrics.loading ? (
            <Skeleton className="h-4 w-48" />
          ) : pd ? (
            <span className="tnum flex flex-wrap items-baseline gap-x-3 gap-y-0.5 text-ink-muted">
              <span>Recall <b className="font-semibold text-ink">{pct(pd.recall, 1)}</b></span>
              <span>Precision <b className="font-semibold text-ink">{pct(pd.precision, 1)}</b></span>
              <span>F1 <b className="font-semibold text-ink">{pct(pd.f1, 1)}</b></span>
            </span>
          ) : (
            <span className="text-ink-faint">Metrics unavailable</span>
          )}
          <ChevronRight className="ml-auto size-3.5 shrink-0 text-ink-faint transition-transform group-hover:translate-x-0.5 group-hover:text-ink" />
        </button>

        {/* Top action */}
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1.5 px-4 py-2.5 lg:flex-nowrap">
          <ListTodo className="size-4 shrink-0 text-status-serious" />
          <span className="shrink-0 text-2xs uppercase tracking-wide text-ink-faint">Top action</span>
          {accumulation.loading ? (
            <Skeleton className="h-4 w-64" />
          ) : top ? (
            <button
              type="button"
              onClick={() => navigate(`/?site=${encodeURIComponent(top.cell.site)}`)}
              className="flex min-w-0 basis-full flex-wrap items-center gap-x-2 gap-y-1 text-left hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 sm:basis-auto lg:flex-nowrap"
              title={`${top.action} — ${top.cell.site}. Click to filter the queue to this site.`}
            >
              <span className="min-w-0 font-medium text-ink lg:truncate">{top.action}</span>
              <span className="shrink-0 text-ink-muted">· {top.cell.site}</span>
              <span className="shrink-0"><BandBadge value={top.cell.band} /></span>
            </button>
          ) : (
            <span className="text-ink-faint">
              {accumulation.error ? "Unavailable" : "No accumulating precursors"}
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto h-7 shrink-0 px-2 text-2xs"
            onClick={() => setOpen(true)}
          >
            {recs.length > 1 ? `All ${recs.length} actions` : "Details"}
          </Button>
        </div>
      </Card>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent widthClassName="max-w-2xl">
          <SheetHeader>
            <SheetTitle>Engine performance &amp; recommended actions</SheetTitle>
            <SheetDescription>
              Measured on held-out data, and the barriers that most need reinforcing.
            </SheetDescription>
          </SheetHeader>
          <SheetBody className="space-y-4">
            <EngineMetricsCard />
            <RecommendedActions onSelect={() => setOpen(false)} />
          </SheetBody>
        </SheetContent>
      </Sheet>
    </>
  );
}
