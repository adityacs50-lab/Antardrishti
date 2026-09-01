import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip as RTooltip,
  XAxis, YAxis,
} from "recharts";
import { ShieldCheck, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { QueryBoundary } from "@/components/StateViews";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useQuery } from "@/lib/useQuery";
import { LSR_LABEL, LSR_SHORT, TREND_LABEL, ENERGY_LABEL } from "@/lib/format";
import { STATUS, TREND_TONE } from "@/lib/theme";
import { cn } from "@/lib/utils";
import type { LifeSavingRule, Trend } from "@/types/api";

const WINDOW = 365;

function TrendIcon({ trend }: { trend: Trend }) {
  const Icon = trend === "rising" ? TrendingUp : trend === "falling" ? TrendingDown : Minus;
  return <Icon className="size-3" style={{ color: TREND_TONE[trend] }} />;
}

export function LifeSavingRulesView() {
  const lsr = useQuery(() => api.lsr(), []);
  const barriers = useQuery(() => api.barriers({ window_days: WINDOW, limit: 200 }), []);
  const [selected, setSelected] = useState<LifeSavingRule | null>(null);
  const navigate = useNavigate();

  const chartData = useMemo(
    () =>
      (lsr.data?.buckets ?? []).map((b) => ({
        rule: b.lsr,
        name: LSR_SHORT[b.lsr],
        full: b.short_name,
        count: b.count,
        precursors: b.precursor_count,
      })),
    [lsr.data],
  );

  // The API has no per-rule barrier endpoint; barriers carry an energy source,
  // and the domain maps energy -> rules. Rather than invent a mapping in the
  // browser, the drill-down filters reports by rule and summarises the controls
  // those reports actually named.
  const drill = useQuery(
    () => (selected ? api.reports({ lsr: [selected], limit: 200 }) : Promise.resolve(null)),
    [selected],
  );

  const drillBarriers = useMemo(() => {
    if (!drill.data) return [];
    const counts = new Map<string, { key: string; status: string; n: number }>();
    for (const r of drill.data.items) {
      if (r.control_status === "present_verified") continue;
      const key = `${r.control_status}`;
      const entry = counts.get(key) ?? { key, status: r.control_status, n: 0 };
      entry.n += 1;
      counts.set(key, entry);
    }
    return [...counts.values()].sort((a, b) => b.n - a.n);
  }, [drill.data]);

  const selectedBarriers = useMemo(() => {
    if (!selected || !barriers.data) return [];
    return barriers.data.patterns.slice(0, 60);
  }, [selected, barriers.data]);

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="flex items-center gap-2 text-lg font-semibold tracking-tight text-ink">
          <ShieldCheck className="size-5 text-series-1" />
          Life-Saving Rules
        </h1>
        <p className="text-xs text-ink-muted">
          IOGP Report 459. Which of the nine rules the reports engage, and which barrier fails most
          often behind each.
        </p>
      </header>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Distribution across the nine rules</CardTitle>
            <CardDescription>
              Bars show every report with an assigned rule; the darker inset is the share that was
              uncontrolled fatal potential. Click a bar to drill in.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <QueryBoundary
              loading={lsr.loading}
              offline={lsr.offline}
              error={lsr.error}
              empty={(lsr.data?.total ?? 0) === 0}
              onRetry={lsr.refetch}
              emptyTitle="No reports yet"
              emptyHint="Seed the database: python -m prahari.cli seed --limit 800"
              skeleton={<Skeleton className="h-72" />}
            >
              <ResponsiveContainer width="100%" height={330}>
                <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 40, bottom: 4, left: 4 }}>
                  <CartesianGrid stroke="#2c2c2a" strokeDasharray="2 4" horizontal={false} />
                  <XAxis type="number" stroke="#383835" fontSize={10} tickLine={false} axisLine={{ stroke: "#383835" }} />
                  <YAxis
                    type="category" dataKey="name" width={110}
                    stroke="#383835" fontSize={10} tickLine={false} axisLine={false}
                  />
                  <RTooltip
                    cursor={{ fill: "rgb(255 255 255 / 0.04)" }}
                    contentStyle={{
                      background: "#1A2330", border: "1px solid #33425A",
                      borderRadius: 6, fontSize: 11, color: "#E6EDF3",
                    }}
                    formatter={(value: unknown, key: unknown) => [
                      value as number,
                      key === "count" ? "Reports" : "Precursors",
                    ]}
                    labelFormatter={(_label: unknown, payload: readonly any[] | undefined) =>
                      payload?.[0]?.payload?.full ?? ""
                    }
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={16} onClick={(d: any) => setSelected(d.rule)}>
                    {chartData.map((d) => (
                      <Cell
                        key={d.rule}
                        cursor="pointer"
                        fill={selected === d.rule ? "#5598e7" : "#3987e5"}
                        fillOpacity={selected && selected !== d.rule ? 0.4 : 1}
                      />
                    ))}
                    <LabelList dataKey="count" position="right" fill="#9FB0C0" fontSize={10} />
                  </Bar>
                  <Bar dataKey="precursors" radius={[0, 4, 4, 0]} barSize={16} fill={STATUS.serious}
                    onClick={(d: any) => setSelected(d.rule)} />
                </BarChart>
              </ResponsiveContainer>

              <div className="mt-2 flex flex-wrap items-center gap-4">
                <span className="inline-flex items-center gap-1.5 text-2xs text-ink-muted">
                  <span className="size-2.5 rounded-sm bg-series-1" /> All reports
                </span>
                <span className="inline-flex items-center gap-1.5 text-2xs text-ink-muted">
                  <span className="size-2.5 rounded-sm" style={{ background: STATUS.serious }} /> Precursors
                </span>
                {lsr.data && lsr.data.unassigned > 0 && (
                  <span className="ml-auto text-2xs text-ink-faint">
                    {lsr.data.unassigned} report{lsr.data.unassigned === 1 ? "" : "s"} carry no rule
                    (insufficient information)
                  </span>
                )}
              </div>
            </QueryBoundary>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              {selected ? LSR_LABEL[selected] : "Select a rule"}
            </CardTitle>
            <CardDescription>
              {selected
                ? "Which barrier states show up behind this rule, and the recurring failures across the field."
                : "Click a bar to see which barriers fail behind that rule."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selected ? (
              <p className="py-10 text-center text-xs text-ink-faint">No rule selected.</p>
            ) : (
              <>
                <div>
                  <p className="mb-2 text-2xs uppercase tracking-wide text-ink-faint">
                    Barrier state in reports under this rule
                  </p>
                  {drill.loading ? (
                    <Skeleton className="h-24" />
                  ) : drillBarriers.length === 0 ? (
                    <p className="text-xs text-ink-faint">
                      No failing barriers recorded under this rule.
                    </p>
                  ) : (
                    <ul className="space-y-1.5">
                      {drillBarriers.map((b) => {
                        const max = drillBarriers[0].n || 1;
                        return (
                          <li key={b.key} className="space-y-1">
                            <div className="flex items-center justify-between text-2xs">
                              <span className="text-ink">{b.status.replace(/_/g, " ")}</span>
                              <span className="tnum text-ink-faint">{b.n}</span>
                            </div>
                            <div className="h-1.5 overflow-hidden rounded-full bg-surface-raised">
                              <div
                                className="h-full rounded-full"
                                style={{ width: `${(b.n / max) * 100}%`, background: STATUS.serious }}
                              />
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>

                <div>
                  <p className="mb-2 text-2xs uppercase tracking-wide text-ink-faint">
                    Recurring barrier failures across the field
                  </p>
                  <QueryBoundary
                    loading={barriers.loading}
                    offline={barriers.offline}
                    error={barriers.error}
                    empty={selectedBarriers.length === 0}
                    onRetry={barriers.refetch}
                    emptyTitle="No recurring failures"
                    skeleton={<Skeleton className="h-32" />}
                  >
                    <ul className="max-h-72 space-y-1.5 overflow-y-auto pr-1">
                      {selectedBarriers.slice(0, 12).map((p, i) => (
                        <li
                          key={`${p.control_key}-${p.site}-${i}`}
                          className="rounded-md border border-line bg-surface-sunken p-2.5"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <span className="min-w-0 flex-1">
                              <span className="block truncate text-2xs font-medium text-ink" title={p.control_label}>
                                {p.control_label}
                              </span>
                              <span className="text-2xs text-ink-faint">
                                {p.site}
                                {p.energy_source && <> · {ENERGY_LABEL[p.energy_source]}</>}
                              </span>
                            </span>
                            <span className="flex shrink-0 items-center gap-2">
                              <span className="tnum text-2xs font-semibold text-ink">{p.failure_count}×</span>
                              <span
                                className="inline-flex items-center gap-1 text-2xs"
                                style={{ color: TREND_TONE[p.trend] }}
                                title={TREND_LABEL[p.trend]}
                              >
                                <TrendIcon trend={p.trend} />
                              </span>
                            </span>
                          </div>
                          <div className={cn("mt-1.5 flex flex-wrap gap-1")}>
                            {Object.entries(p.statuses).map(([status, n]) => (
                              <span
                                key={status}
                                className="rounded border border-line px-1.5 py-0.5 text-2xs text-ink-muted"
                              >
                                {status.replace(/_/g, " ")} ×{n}
                              </span>
                            ))}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </QueryBoundary>
                </div>

                <button
                  onClick={() => navigate(`/?lsr=${selected}`)}
                  className="text-2xs text-series-1 hover:underline"
                >
                  View reports under this rule →
                </button>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
