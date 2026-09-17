import { FlaskConical } from "lucide-react";
import { LiveAnalysisPanel } from "./LiveAnalysisPanel";

/**
 * The manual ingestion playground. Same engine, same rules as the Triage
 * Queue — the only difference is that nothing typed here is persisted.
 * Kept deliberately separate from "New Report" (Triage Queue's toolbar),
 * which does persist: this tab is for trying an incident out before
 * deciding it belongs in the queue at all.
 */
export function SandboxView() {
  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <h1 className="flex items-center gap-2 text-lg font-semibold tracking-tight text-ink">
          <FlaskConical className="size-5 text-series-1" />
          Live Incident Sandbox
        </h1>
        <p className="max-w-2xl text-xs leading-relaxed text-ink-muted">
          Paste or type an incident to see how the rule engine would score it — the same engine
          that scores the Triage Queue, nothing analysed in the browser. Nothing typed here is
          saved. To actually add a report to the queue, use{" "}
          <span className="font-medium text-ink">New Report</span> on the Triage Queue tab.
        </p>
      </header>

      <LiveAnalysisPanel />
    </div>
  );
}
