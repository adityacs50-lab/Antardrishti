import { AlertTriangle, Inbox, PlugZap, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * The offline state is deliberately loud and empty.
 *
 * This app never substitutes sample data for a live verdict. Showing a
 * fabricated classification in a safety tool — even briefly, even in a demo —
 * is a worse failure than showing nothing.
 */
export function OfflineState({ onRetry }: { onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-status-critical/40 bg-status-critical/5 px-6 py-14 text-center">
      <PlugZap className="size-8 text-status-critical" />
      <div className="space-y-1.5">
        <p className="text-sm font-semibold text-ink">Backend unreachable</p>
        <p className="max-w-md text-xs leading-relaxed text-ink-muted">
          prahari shows no data rather than sample data. Nothing on this screen is ever a
          verdict the engine did not produce.
        </p>
        <code className="mt-2 inline-block rounded border border-line bg-surface-sunken px-2 py-1 text-2xs text-ink-muted">
          cd backend &amp;&amp; uvicorn prahari.main:app --reload
        </code>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw /> Retry
        </Button>
      )}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-line bg-surface px-6 py-12 text-center">
      <AlertTriangle className="size-6 text-status-warning" />
      <p className="text-sm text-ink">Something went wrong</p>
      <p className="max-w-md text-xs text-ink-muted">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw /> Retry
        </Button>
      )}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-line px-6 py-12 text-center">
      <Inbox className="size-6 text-ink-faint" />
      <p className="text-sm text-ink-muted">{title}</p>
      {hint && <p className="max-w-md text-xs text-ink-faint">{hint}</p>}
    </div>
  );
}

export function LoadingRows({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-16 w-full" />
      ))}
    </div>
  );
}

/** Wraps the common loading / offline / error / empty branch set. */
export function QueryBoundary({
  loading, offline, error, empty, onRetry, children, emptyTitle, emptyHint, skeleton,
}: {
  loading: boolean;
  offline: boolean;
  error?: string;
  empty?: boolean;
  onRetry?: () => void;
  children: React.ReactNode;
  emptyTitle?: string;
  emptyHint?: string;
  skeleton?: React.ReactNode;
}) {
  if (loading) return <>{skeleton ?? <LoadingRows />}</>;
  if (offline) return <OfflineState onRetry={onRetry} />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  if (empty) return <EmptyState title={emptyTitle ?? "Nothing here yet"} hint={emptyHint} />;
  return <>{children}</>;
}
