import { useRef, useState } from "react";
import { FilePlus2, Loader2, Paperclip } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Input, Textarea } from "@/components/ui/input";
import { ClassificationBadge } from "@/components/Chips";
import { api, ApiError } from "@/lib/api";
import type { IngestResult } from "@/types/api";

const TODAY = () => new Date().toISOString().slice(0, 10);

const EMPTY = { text: "", site: "", date: TODAY(), reporter_role: "", activity: "" };

interface Props {
  /** Known site/activity values, for the datalist suggestions — may be empty
   * on a freshly-seeded or empty database, in which case this is just a
   * free-text field. */
  sites: string[];
  activities: string[];
  onSubmitted: (result: IngestResult) => void;
}

/**
 * Zone 1 of the pitch ("Report Comes In: officer pastes any-language
 * report") made real. Unlike the Live Analysis panel next to the queue —
 * which is a sandbox that deliberately never saves anything — submitting
 * here calls POST /api/reports and actually lands the report in the
 * database, so it can show up in the Triage Queue, the Precursor Map and the
 * accumulation index like any other report.
 */
export function NewReportDialog({ sites, activities, onSubmitted }: Props) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string>();
  const [justAdded, setJustAdded] = useState<IngestResult>();
  const [attachedName, setAttachedName] = useState<string>();
  const fileInput = useRef<HTMLInputElement>(null);

  const set = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }));

  const reset = () => {
    setForm(EMPTY);
    setError(undefined);
    setJustAdded(undefined);
    setAttachedName(undefined);
  };

  const attach = async (file: File) => {
    setExtracting(true);
    setError(undefined);
    try {
      const { text, truncated } = await api.extractText(file);
      set({ text });
      setAttachedName(file.name + (truncated ? " (truncated to 20,000 chars)" : ""));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Could not read that file.",
      );
    } finally {
      setExtracting(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const submit = async () => {
    if (!form.text.trim() || !form.site.trim() || !form.date) {
      setError("Report text, site and date are required.");
      return;
    }
    setBusy(true);
    setError(undefined);
    try {
      const result = await api.submit({
        text: form.text.trim(),
        site: form.site.trim(),
        date: form.date,
        reporter_role: form.reporter_role.trim() || undefined,
        activity: form.activity.trim() || undefined,
      });
      setJustAdded(result);
      onSubmitted(result);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Could not submit the report.",
      );
    } finally {
      setBusy(false);
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
        <Button variant="default" size="sm">
          <FilePlus2 /> New Report
        </Button>
      </DialogTrigger>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>Submit a safety report</DialogTitle>
          <DialogDescription>
            Runs the same rule engine as Live Analysis, but this one is saved — it will appear in
            the Triage Queue if the engine finds uncontrolled fatal potential (PSIF or Exposure).
          </DialogDescription>
        </DialogHeader>

        {justAdded ? (
          <div className="space-y-3 px-5 py-4">
            <div className="flex items-center gap-2">
              <ClassificationBadge value={justAdded.verdict.classification} />
              <span className="text-xs text-ink-muted">
                Report {justAdded.report_uid} saved.
              </span>
            </div>
            <p className="text-xs text-ink-faint">
              {["psif", "exposure"].includes(justAdded.verdict.classification)
                ? "It should now be in the Triage Queue, ranked by triage_rank."
                : "This classification isn't shown in the Triage Queue by default (only PSIF and Exposure are) — it's still saved and visible from the report detail / API."}
            </p>
          </div>
        ) : (
          <div className="space-y-3 px-5 py-4">
            <div className="flex items-center justify-between gap-2">
              <span className="text-2xs text-ink-faint">Report text</span>
              <input
                ref={fileInput}
                type="file"
                accept=".pdf,.txt,application/pdf,text/plain"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void attach(file);
                }}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => fileInput.current?.click()}
                disabled={extracting}
              >
                {extracting ? <Loader2 className="animate-spin" /> : <Paperclip />}
                {extracting ? "Reading…" : "Attach PDF / .txt"}
              </Button>
            </div>
            <Textarea
              value={form.text}
              onChange={(e) => { set({ text: e.target.value }); setAttachedName(undefined); }}
              rows={6}
              placeholder="Paste the report text, in any language, or attach a file above…"
              aria-label="Report text"
              autoFocus
            />
            {attachedName && (
              <p className="text-2xs text-ink-faint">
                Extracted from <span className="text-ink-muted">{attachedName}</span> — review before
                submitting.
              </p>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-2xs text-ink-faint">Site *</label>
                <Input
                  value={form.site}
                  onChange={(e) => set({ site: e.target.value })}
                  list="site-suggestions"
                  placeholder="e.g. Duliajan"
                />
                <datalist id="site-suggestions">
                  {sites.map((s) => <option key={s} value={s} />)}
                </datalist>
              </div>
              <div>
                <label className="mb-1 block text-2xs text-ink-faint">Date *</label>
                <Input type="date" value={form.date} onChange={(e) => set({ date: e.target.value })} />
              </div>
              <div>
                <label className="mb-1 block text-2xs text-ink-faint">Activity</label>
                <Input
                  value={form.activity}
                  onChange={(e) => set({ activity: e.target.value })}
                  list="activity-suggestions"
                  placeholder="optional"
                />
                <datalist id="activity-suggestions">
                  {activities.map((a) => <option key={a} value={a} />)}
                </datalist>
              </div>
              <div>
                <label className="mb-1 block text-2xs text-ink-faint">Reporter role</label>
                <Input
                  value={form.reporter_role}
                  onChange={(e) => set({ reporter_role: e.target.value })}
                  placeholder="optional"
                />
              </div>
            </div>
            {error && (
              <p className="rounded-md border border-status-warning/40 bg-status-warning/10 px-3 py-2 text-xs text-status-warning">
                {error}
              </p>
            )}
          </div>
        )}

        <DialogFooter>
          {justAdded ? (
            <>
              <Button variant="outline" size="sm" onClick={reset}>
                Add another
              </Button>
              <Button size="sm" onClick={() => setOpen(false)}>
                Done
              </Button>
            </>
          ) : (
            <Button size="sm" onClick={() => void submit()} disabled={busy}>
              {busy && <Loader2 className="animate-spin" />}
              Submit report
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
