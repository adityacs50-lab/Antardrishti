import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpRight, ListTodo, TrendingUp } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BandBadge } from "@/components/Chips";
import { api } from "@/lib/api";
import { useQuery } from "@/lib/useQuery";
import { ENERGY_LABEL } from "@/lib/format";
import { TREND_TONE } from "@/lib/theme";
import type { AccumulationCell, Band, ControlStatus, DensityOut } from "@/types/api";

/**
 * Recommended Immediate Actions.
 *
 * Deterministic, like everything else: rank the Accumulation Index cells by
 * band, then rising trend, then index; take the top three; name the barrier
 * that keeps failing there and the activity at that site with the most
 * precursors. The verb comes from HOW the barrier failed. No model, no
 * scoring invented in the browser — just a readable ordering of what the
 * analytics endpoints already computed, with a link to the evidence.
 */

const BAND_RANK: Record<Band, number> = { critical: 3, high: 2, elevated: 1, watch: 0 };

const VERB: Record<ControlStatus, string> = {
  bypassed: "Audit override authorisations for",
  absent: "Install and enforce",
  failed: "Inspect and replace",
  not_followed: "Enforce use of",
  present_unverified: "Add a verification step for",
  unknown: "Confirm the state of",
  present_verified: "Maintain",
};

/** "Fixed machine guarding" -> "fixed machine guarding", but "BOP test" stays. */
const lowerFirst = (s: string) => (/^[A-Z][a-z]/.test(s) ? s[0].toLowerCase() + s.slice(1) : s);

export interface Recommendation {
  cell: AccumulationCell;
  activity: string | null;
  action: string;
}

export function buildRecommendations(
  cells: AccumulationCell[],
  density: DensityOut | undefined,
  n = 3,
): Recommendation[] {
  const ranked = [...cells].sort(
    (a, b) =>
      BAND_RANK[b.band] - BAND_RANK[a.band] ||
      Number(b.trend === "rising") - Number(a.trend === "rising") ||
      b.index - a.index,
  );
  return ranked.slice(0, n).map((cell) => {
    const top = cell.signatures[0];
    const activity =
      density?.cells
        .filter((d) => d.site === cell.site && d.precursor_count > 0)
        .sort((a, b) => b.precursor_count - a.precursor_count)[0]?.activity ?? null;
    const action = top
      ? `${VERB[top.control_status]} ${lowerFirst(top.control_label)}`
      : `Review ${ENERGY_LABEL[cell.energy_source].toLowerCase()} barriers`;
    return { cell, activity, action };
  });
}

export function RecommendedActions({
  className,
  onSelect,
}: {
  className?: string;
  /** Called after a row navigates, e.g. to close the panel it sits in. */
  onSelect?: () => void;
}) {
  const navigate = useNavigate();
  const accumulation = useQuery(() => api.accumulation({ window_days: 365 }), []);
  const density = useQuery(() => api.density(), []);

  const recs = useMemo(
    () => buildRecommendations(accumulation.data?.cells ?? [], density.data),
    [accumulation.data, density.data],
  );

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="inline-flex items-center gap-2">
          <ListTodo className="size-4 text-status-serious" />
          Recommended Immediate Actions
        </CardTitle>
        <CardDescription>
          Where barrier reinforcement matters most — highest Accumulation Index, rising first.
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        {accumulation.loading ? (
          <div className="space-y-2 p-4">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-14 w-full" />)}
          </div>
        ) : accumulation.offline || accumulation.error ? (
          <p className="p-4 text-xs text-ink-faint">Unavailable — the API is not reachable.</p>
        ) : recs.length === 0 ? (
          <p className="p-4 text-xs text-ink-faint">No accumulating precursors in the last 12 months.</p>
        ) : (
          <ol className="divide-y divide-line">
            {recs.map(({ cell, activity, action }, i) => (
              <li key={`${cell.site}-${cell.energy_source}`}>
                <button
                  onClick={() => { navigate(`/?site=${encodeURIComponent(cell.site)}`); onSelect?.(); }}
                  className="group flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-raised"
                >
                  <span className="tnum mt-0.5 flex size-6 shrink-0 items-center justify-center border border-line-strong text-xs font-semibold text-ink">
                    {i + 1}
                  </span>
                  <span className="min-w-0 flex-1 space-y-1">
                    <span className="block text-xs font-medium text-ink">{action}</span>
                    <span className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-2xs text-ink-muted">
                      <span className="font-medium text-ink">{cell.site}</span>
                      <span>{ENERGY_LABEL[cell.energy_source]}</span>
                      {activity && <span className="min-w-0 basis-full sm:basis-auto">{activity}</span>}
                      <BandBadge value={cell.band} />
                      {cell.trend === "rising" && (
                        <span className="inline-flex items-center gap-0.5" style={{ color: TREND_TONE.rising }}>
                          <TrendingUp className="size-3" /> rising
                        </span>
                      )}
                    </span>
                    <span className="tnum block text-2xs text-ink-faint">
                      index {cell.index.toFixed(1)}
                      {cell.max_repeat > 1 && <> · same barrier failed {cell.max_repeat}×</>}
                    </span>
                  </span>
                  <ArrowUpRight className="mt-0.5 size-3.5 shrink-0 text-ink-faint transition-colors group-hover:text-ink" />
                </button>
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
