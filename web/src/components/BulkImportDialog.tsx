import { useRef, useState } from "react";
import { Loader2, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { api, ApiError } from "@/lib/api";
import { chunkUploadFile } from "@/lib/chunkUpload";
import type { BulkResult } from "@/types/api";

function mergeResults(a: BulkResult, b: BulkResult): BulkResult {
  const counts: Record<string, number> = { ...a.classification_counts };
  for (const [k, v] of Object.entries(b.classification_counts)) counts[k] = (counts[k] ?? 0) + v;
  return {
    received: a.received + b.received,
    ingested: a.ingested + b.ingested,
    skipped: a.skipped + b.skipped,
    errors: [...a.errors, ...b.errors],
    classification_counts: counts,
  };
}

interface Props {
  onImported: () => void;
}

/**
 * Bulk-ingest an existing corpus — a CSV or JSONL export of OIL's own
 * reports, one row per report — through the already-working
 * POST /api/reports/bulk endpoint. That endpoint has existed since early in
 * the project (it backs `prahari.cli seed`) but nothing in the UI ever
 * called it; this is the only place a human can drive it without a
 * terminal, which matters once the app is deployed somewhere with no shell
 * (Vercel) and someone other than the person who wrote the code needs to
 * load a real corpus.
 *
 * Expected shape per row: {text, site, date, activity?, reporter_role?,
 * report_uid?} — a CSV needs those as column headers; JSONL is one such
 * object per line (the synthetic-corpus shape with nested metadata is also
 * accepted, per parse_upload's docstring).
 */
export function BulkImportDialog({ onImported }: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<string>();
  const [error, setError] = useState<string>();
  const [result, setResult] = useState<BulkResult>();
  const fileInput = useRef<HTMLInputElement>(null);

  const reset = () => {
    setError(undefined);
    setResult(undefined);
  };

  const run = async (file: File) => {
    setBusy(true);
    setError(undefined);
    setResult(undefined);
    setProgress(undefined);
    try {
      // Vercel's functions hard-cap a request body at 4.5 MB (not
      // configurable) - a real export can easily cross that. Chunking here
      // means the person never has to know or care; each chunk is a
      // complete, independently-valid CSV/JSONL document.
      setProgress("Reading file…");
      // Yield a frame so the label above actually paints before the (possibly
      // multi-second) parse of a large file takes the main thread.
      await new Promise((r) => setTimeout(r, 0));
      const chunks = await chunkUploadFile(file);
      let combined: BulkResult | undefined;
      for (let i = 0; i < chunks.length; i++) {
        setProgress(
          chunks.length > 1 ? `Importing part ${i + 1} of ${chunks.length}…` : "Importing…",
        );
        const chunkFile = new File([chunks[i].blob], chunks[i].name);
        const res = await api.bulkImport(chunkFile);
        combined = combined ? mergeResults(combined, res) : res;
        setResult(combined);
      }
      if (combined && combined.ingested > 0) onImported();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.status === 413
            ? "That file is still too large even after splitting it — try a smaller export."
            : err.message
          : err instanceof Error
            ? err.message
            : "Could not import that file.",
      );
    } finally {
      setBusy(false);
      setProgress(undefined);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next: boolean) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <UploadCloud /> Bulk Import
        </Button>
      </DialogTrigger>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>Bulk import reports</DialogTitle>
          <DialogDescription>
            Upload a CSV or JSONL export — one report per row. Each row runs through the same rule
            engine as everything else here and is persisted, exactly like submitting one at a time.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 px-5 py-4">
          <p className="text-2xs text-ink-faint">
            Expected columns / fields: <code className="text-ink-muted">text</code> (required),{" "}
            <code className="text-ink-muted">site</code>, <code className="text-ink-muted">date</code>,
            {" "}<code className="text-ink-muted">activity</code>,{" "}
            <code className="text-ink-muted">reporter_role</code>.
          </p>

          <input
            ref={fileInput}
            type="file"
            accept=".csv,.jsonl,text/csv,application/json"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void run(file);
            }}
          />
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => fileInput.current?.click()}
            disabled={busy}
          >
            {busy ? <Loader2 className="animate-spin" /> : <UploadCloud />}
            {busy ? (progress ?? "Importing…") : "Choose file…"}
          </Button>

          {error && (
            <p className="rounded-md border border-status-warning/40 bg-status-warning/10 px-3 py-2 text-xs text-status-warning">
              {error}
            </p>
          )}

          {result && (
            <div className="space-y-2 rounded-md border border-line bg-surface-sunken p-3 text-xs">
              <p className="text-ink">
                {result.ingested} of {result.received} rows ingested
                {result.skipped > 0 && `, ${result.skipped} skipped`}.
              </p>
              {/* An import that lands nothing is the one case where the reason
                  must not be hidden behind a disclosure triangle — it is
                  almost always a column-name mismatch, and the server's first
                  error line says exactly which columns it did find. */}
              {result.ingested === 0 && result.errors.length > 0 && (
                <p className="rounded border border-status-warning/40 bg-status-warning/10 px-2 py-1.5 text-status-warning">
                  {result.errors[0]}
                </p>
              )}
              {Object.keys(result.classification_counts).length > 0 && (
                <p className="text-ink-muted">
                  {Object.entries(result.classification_counts)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(" · ")}
                </p>
              )}
              {result.errors.length > 0 && (
                <details>
                  <summary className="cursor-pointer text-ink-faint">
                    {result.errors.length} error{result.errors.length === 1 ? "" : "s"}
                  </summary>
                  <ul className="mt-1 list-disc space-y-0.5 pl-4 text-ink-faint">
                    {result.errors.slice(0, 10).map((e, i) => <li key={i}>{e}</li>)}
                  </ul>
                </details>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button size="sm" onClick={() => setOpen(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
