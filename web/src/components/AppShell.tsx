import { useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { FlaskConical, Grid3x3, ListChecks, Radar, ShieldCheck, ShieldOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useQuery } from "@/lib/useQuery";

/**
 * Header Navigation — exactly two destinations. This is the whole point of
 * the refactor: an HSE officer either triages what already came in, or
 * sandboxes an incident before deciding whether it belongs in the queue at
 * all. Everything else the app can do (site patterns, the Life-Saving Rules
 * reference, a single report's permalink) still exists — see SECONDARY_NAV
 * below — it just no longer competes for the same visual weight as these two.
 */
const PRIMARY_NAV = [
  { to: "/", label: "Triage Queue", icon: ListChecks, end: true },
  { to: "/sandbox", label: "Live Incident Sandbox", icon: FlaskConical, end: true },
];

const SECONDARY_NAV = [
  { to: "/map", label: "Patterns", icon: Grid3x3 },
  { to: "/rules", label: "Rules", icon: ShieldCheck },
];

export function AppShell() {
  const health = useQuery(() => api.health(), []);
  // Prefer last successful health payload while a refetch is in flight so the
  // banner does not flicker "Connecting…" / empty counts during navigation.
  const connected = !!health.data && !health.offline;
  const statusLabel = health.offline
    ? "Offline"
    : health.data
      ? "Online"
      : health.loading
        ? "Connecting…"
        : "Offline";

  // Importing a corpus, submitting a report, or reviewing one changes the
  // report count and the KPI bar. The banner and the KPI bar share no other
  // context, so this window event is what keeps every surface in sync.
  const refetchHealth = health.refetch;
  useEffect(() => {
    const onChanged = () => void refetchHealth();
    window.addEventListener("prahari:data-changed", onChanged);
    return () => window.removeEventListener("prahari:data-changed", onChanged);
  }, [refetchHealth]);

  return (
    <div className="min-h-screen bg-bg">
      {/* Row 1 — compact top banner: brand mark, the two system badges an
          HSE officer checks before trusting a verdict (air-gapped engine
          status, ontology/engine version), and the secondary views kept out
          of the primary tabs' way. */}
      <div className="border-b border-line bg-surface-sunken">
        <div className="mx-auto flex h-9 max-w-[1600px] items-center gap-3 px-5">
          <div className="flex items-center gap-2">
            <Radar className="size-3.5 text-accent" />
            <span className="text-2xs font-medium tracking-tight text-ink">prahari</span>
            <span className="hidden text-2xs text-ink-faint sm:inline">प्रहरी · SIH26165</span>
          </div>

          <div className="ml-auto flex items-center gap-2">
            {/* Air-gapped Engine status. Which extraction path is live is
                stated on screen — a system that claims a model is running
                when it has silently fallen back is worse than one with no
                model at all. */}
            <span
              className="inline-flex items-center gap-1.5 border px-2 py-0.5 text-2xs"
              title={
                health.data
                  ? `${health.data.extractor === "NEURAL" ? "ONNX model" : "Keyword fallback"} · ${health.data.extractor_detail}. Nothing is fetched from the network — the engine runs entirely on this machine.`
                  : "Waiting to reach the local engine"
              }
              style={{
                color: connected ? "#0ca30c" : "#d03b3b",
                borderColor: connected ? "rgb(12 163 12 / 0.35)" : "rgb(208 59 59 / 0.35)",
                backgroundColor: connected ? "rgb(12 163 12 / 0.1)" : "rgb(208 59 59 / 0.1)",
              }}
            >
              {connected ? <ShieldCheck className="size-3" /> : <ShieldOff className="size-3" />}
              <span
                className={cn("size-1.5 rounded-full", !connected && "animate-pulse-ring")}
                style={{ backgroundColor: connected ? "#0ca30c" : "#d03b3b" }}
              />
              Air-gapped Engine · {health.loading && !health.data ? "Connecting…" : statusLabel}
            </span>

            {/* Ontology version — the SCL/LSR rule set this queue was scored
                against. */}
            {health.data && (
              <span
                className="hidden items-center gap-1 border border-line px-2 py-0.5 text-2xs text-ink-muted md:inline-flex"
                title={`${health.data.report_count} reports in the queue · extractor ${health.data.extractor_version}`}
              >
                Ontology v{health.data.engine_version}
              </span>
            )}

            <span className="mx-1 hidden h-4 w-px bg-line lg:block" aria-hidden />

            <nav className="hidden items-center gap-3 lg:flex">
              {SECONDARY_NAV.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }: { isActive: boolean }) =>
                    cn(
                      "inline-flex items-center gap-1 text-2xs transition-colors",
                      isActive ? "text-ink" : "text-ink-faint hover:text-ink-muted",
                    )
                  }
                >
                  <Icon className="size-3" />
                  {label}
                </NavLink>
              ))}
            </nav>
          </div>
        </div>
      </div>

      {/* Row 2 — the primary Header Navigation. Deliberately large and
          unambiguous: two tabs, nothing competing with them. */}
      <header className="sticky top-0 z-40 border-b border-line bg-bg">
        <div className="relative mx-auto flex h-12 max-w-[1600px] items-stretch px-5">
          <div aria-hidden className="absolute inset-y-0 left-0 w-1 bg-accent" />
          <nav className="flex h-full items-stretch gap-0 pl-2">
            {PRIMARY_NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }: { isActive: boolean }) =>
                  cn(
                    "inline-flex items-center gap-2 px-4 text-xs font-medium transition-colors border-b-2",
                    isActive
                      ? "border-accent bg-surface text-ink"
                      : "border-transparent text-ink-muted hover:bg-surface-sunken hover:text-ink",
                  )
                }
              >
                <Icon className="size-3.5" />
                {label}
              </NavLink>
            ))}
          </nav>

          {/* Secondary views, repeated here at small size for narrow
              viewports where the top banner's row hides them. */}
          <nav className="ml-auto flex items-center gap-3 lg:hidden">
            {SECONDARY_NAV.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }: { isActive: boolean }) =>
                  cn(
                    "inline-flex items-center gap-1 text-2xs transition-colors",
                    isActive ? "text-ink" : "text-ink-faint hover:text-ink-muted",
                  )
                }
              >
                <Icon className="size-3" />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] px-5 py-6">
        <Outlet />
      </main>
    </div>
  );
}
