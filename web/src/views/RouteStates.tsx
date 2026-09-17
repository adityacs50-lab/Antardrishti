import { Link, isRouteErrorResponse, useRouteError } from "react-router-dom";
import { AlertTriangle, Compass, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

/** Unknown URL inside the app. */
export function NotFoundView() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 border border-dashed border-line px-6 py-20 text-center">
      <Compass className="size-7 text-ink-faint" />
      <p className="text-sm font-semibold text-ink">Page not found</p>
      <p className="max-w-sm text-xs text-ink-muted">
        That address does not match any screen in prahari.
      </p>
      <Button asChild variant="outline" size="sm">
        <Link to="/">Back to the Triage Queue</Link>
      </Button>
    </div>
  );
}

/**
 * Last line of defence for a render crash or a failed lazy chunk. A chunk
 * that 404s almost always means the app was redeployed while this tab was
 * open, and a reload fixes it — so that is the one action offered.
 */
export function RouteErrorView() {
  const error = useRouteError();
  const message = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : error instanceof Error
      ? error.message
      : String(error);
  const stale = /dynamically imported module|Loading chunk|Importing a module script failed/i.test(message);

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-5">
      <div role="alert" className="flex max-w-md flex-col items-center gap-3 border border-line bg-surface px-6 py-12 text-center">
        <AlertTriangle className="size-7 text-status-warning" />
        <p className="text-sm font-semibold text-ink">
          {stale ? "A newer version of prahari is available" : "This screen failed to load"}
        </p>
        <p className="text-xs leading-relaxed text-ink-muted">
          {stale
            ? "The app was updated while this tab was open. Reload to continue."
            : "Nothing was saved or changed. Reload the page; if it happens again, note the message below."}
        </p>
        {!stale && (
          <code className="max-w-full break-words border border-line bg-surface-sunken px-2 py-1 text-2xs text-ink-muted">
            {message}
          </code>
        )}
        <div className="flex gap-2">
          <Button size="sm" onClick={() => window.location.reload()}>
            <RefreshCw /> Reload
          </Button>
          <Button asChild variant="outline" size="sm">
            <a href="/">Triage Queue</a>
          </Button>
        </div>
      </div>
    </div>
  );
}
