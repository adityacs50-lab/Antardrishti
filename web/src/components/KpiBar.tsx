import { useEffect, type ReactNode } from "react";
import { AlertTriangle, Clock3, MapPinned, Zap } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BandBadge } from "@/components/Chips";
import { api } from "@/lib/api";
import { useQuery } from "@/lib/useQuery";
import { cn } from "@/lib/utils";

function KpiCard({
  icon,
  label,
  value,
  hint,
  loading,
  tone,
  valueClassName,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  loading?: boolean;
  tone: string;
  valueClassName?: string;
}) {
  return (
    <Card className="flex flex-col gap-2 p-4">
      <span className="inline-flex items-center gap-1.5 text-2xs font-medium uppercase tracking-wide text-ink-faint">
        <span style={{ color: tone }}>{icon}</span>
        {label}
      </span>
      {loading ? (
        <Skeleton className="h-7 w-20" />
      ) : (
        <span className={cn("tnum truncate text-2xl font-semibold leading-none text-ink", valueClassName)}>
          {value}
        </span>
      )}
      <span className="truncate text-2xs text-ink-faint">{hint}</span>
    </Card>
  );
}

/**
 * The four numbers an HSE officer checks before opening a single row: how
 * much fatal potential is sitting in the queue, how much of it is unreviewed,
 * and where it keeps recurring. Deliberately global (not scoped to the
 * table's site filter below) — this is the state of the whole queue, not of
 * whatever slice happens to be on screen.
 */
export function KpiBar() {
  const psif = useQuery(() => api.reports({ classification: ["psif"], limit: 1 }), []);
  const exposure = useQuery(() => api.reports({ classification: ["exposure"], limit: 1 }), []);
  const pending = useQuery(
    () => api.reports({ classification: ["psif", "exposure"], reviewed: false, limit: 1 }),
    [],
  );
  const accumulation = useQuery(() => api.accumulation({ window_days: 365 }), []);
  const top = accumulation.data?.cells[0];

  // Ingesting a report, importing a corpus, or confirming/overriding a
  // verdict all change these counts. Same event AppShell listens to for the
  // header's report count, so the whole shell stays in sync from one signal.
  const refetchAll = () => {
    psif.refetch();
    exposure.refetch();
    pending.refetch();
    accumulation.refetch();
  };
  useEffect(() => {
    window.addEventListener("prahari:data-changed", refetchAll);
    return () => window.removeEventListener("prahari:data-changed", refetchAll);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <KpiCard
        icon={<AlertTriangle className="size-3.5" />}
        label="Potential SIFs"
        value={psif.data?.total ?? "—"}
        hint="PSIF — fatal energy, no barrier, nobody hurt yet"
        loading={psif.loading}
        tone="#ec835a"
      />
      <KpiCard
        icon={<Zap className="size-3.5" />}
        label="High-Energy Exposures"
        value={exposure.data?.total ?? "—"}
        hint="Hazard present and uncontrolled"
        loading={exposure.loading}
        tone="#fab219"
      />
      <KpiCard
        icon={<Clock3 className="size-3.5" />}
        label="Pending Review"
        value={pending.data?.total ?? "—"}
        hint="Awaiting an HSE confirm or override"
        loading={pending.loading}
        tone="#3987e5"
      />
      <KpiCard
        icon={<MapPinned className="size-3.5" />}
        label="Top Accumulation Site"
        value={top ? top.site : "—"}
        valueClassName="text-lg"
        hint={
          top ? (
            <span className="inline-flex items-center gap-1.5">
              index {top.index.toFixed(1)} <BandBadge value={top.band} />
            </span>
          ) : accumulation.error ? (
            "Unavailable"
          ) : (
            "No accumulating precursors"
          )
        }
        loading={accumulation.loading}
        tone="#199e70"
      />
    </div>
  );
}
