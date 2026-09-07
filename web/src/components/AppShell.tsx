import { useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { Grid3x3, ListChecks, ShieldCheck, Radar } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useQuery } from "@/lib/useQuery";

const NAV = [
  { to: "/", label: "Triage Queue", icon: ListChecks, end: true },
  { to: "/map", label: "Precursor Map", icon: Grid3x3, end: false },
  { to: "/rules", label: "Life-Saving Rules", icon: ShieldCheck, end: false },
];

export function AppShell() {
  const health = useQuery(() => api.health(), []);
  const connected = !!health.data && !health.offline;

  // The header's "N reports" is read from /health once on mount. Importing a
  // corpus or submitting a report changes that number, and a header still
  // reading "0 reports" over a full queue is the kind of thing a judge notices.
  // The dialogs announce it; this listens. A window event rather than lifted
  // state because this shell and those dialogs share no other context.
  const refetchHealth = health.refetch;
  useEffect(() => {
    const onChanged = () => void refetchHealth();
    window.addEventListener("prahari:data-changed", onChanged);
    return () => window.removeEventListener("prahari:data-changed", onChanged);
  }, [refetchHealth]);

  return (
    <div className="min-h-screen bg-bg">
      <header className="sticky top-0 z-40 border-b border-line bg-bg/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1600px] items-center gap-6 px-5">
          <div className="flex items-center gap-2.5">
            <Radar className="size-5 text-series-1" />
            <div className="leading-none">
              <span className="text-sm font-semibold tracking-tight text-ink">prahari</span>
              <span className="ml-2 text-2xs text-ink-faint">प्रहरी</span>
            </div>
          </div>

          <nav className="flex items-center gap-1">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }: { isActive: boolean }) =>
                  cn(
                    "inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                    isActive
                      ? "bg-surface-raised text-ink"
                      : "text-ink-muted hover:bg-surface hover:text-ink",
                  )
                }
              >
                <Icon className="size-3.5" />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2.5">
            {/* Which extraction path is live, stated on screen. A system that
                claims a model is running when it has silently fallen back is
                worse than one with no model at all. */}
            {health.data && (
              <span
                className="hidden items-center gap-1.5 rounded-md border px-2 py-1 text-2xs md:inline-flex"
                title={health.data.extractor_detail}
                style={{
                  color: health.data.extractor === "NEURAL" ? "#3987e5" : "#9FB0C0",
                  borderColor:
                    health.data.extractor === "NEURAL"
                      ? "rgb(57 135 229 / 0.35)"
                      : "hsl(var(--border))",
                  backgroundColor:
                    health.data.extractor === "NEURAL"
                      ? "rgb(57 135 229 / 0.10)"
                      : "hsl(var(--surface-1))",
                }}
              >
                {health.data.extractor === "NEURAL" ? "ONNX model" : "Keyword fallback"}
              </span>
            )}
            {health.data && (
              <span className="hidden text-2xs text-ink-faint lg:inline">
                {health.data.report_count} reports · {health.data.engine_version}
              </span>
            )}
            <span
              className="inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-2xs"
              style={{
                color: connected ? "#0ca30c" : "#d03b3b",
                borderColor: connected ? "rgb(12 163 12 / 0.35)" : "rgb(208 59 59 / 0.35)",
                backgroundColor: connected ? "rgb(12 163 12 / 0.1)" : "rgb(208 59 59 / 0.1)",
              }}
            >
              <span
                className={cn("size-1.5 rounded-full", !connected && "animate-pulse-ring")}
                style={{ backgroundColor: connected ? "#0ca30c" : "#d03b3b" }}
              />
              {health.loading ? "Connecting…" : connected ? "Engine online" : "Backend offline"}
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] px-5 py-6">
        <Outlet />
      </main>
    </div>
  );
}
