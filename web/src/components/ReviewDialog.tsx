import { useEffect, useState } from "react";
import { Check, PenLine } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input, Select, Textarea } from "@/components/ui/input";
import { api } from "@/lib/api";
import { CLASSIFICATION_LABEL } from "@/lib/format";
import type { ReportDetail, SifClassification } from "@/types/api";

const CLASSES: SifClassification[] = [
  "hsif", "lsif", "psif", "capacity", "exposure", "success",
  "low_severity", "insufficient_information",
];

/**
 * The confirm/override flow, extracted so it is one component reachable from
 * two doors: the full Report Detail page, and the Triage Queue's Audit
 * drawer. A reviewer gets identical controls either way — this refactor
 * moves *where* the audit trail is reached, never what it does.
 */
export function ReviewDialog({
  report, open, onOpenChange, onDone, initialMode = "confirm",
}: {
  report: ReportDetail;
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onDone: () => void;
  /** Which decision the dialog opens on — the button the reviewer pressed. */
  initialMode?: "confirm" | "override";
}) {
  const [mode, setMode] = useState<"confirm" | "override">(initialMode);
  const [role, setRole] = useState("HSE Officer");
  const [reason, setReason] = useState("");
  const [corrected, setCorrected] = useState<SifClassification>(report.verdict.classification);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  // Every opening starts clean, on the decision the reviewer chose, for the
  // report currently on screen.
  useEffect(() => {
    if (!open) return;
    setMode(initialMode);
    setReason("");
    setError(undefined);
    setCorrected(report.verdict.classification);
  }, [open, initialMode, report.id, report.verdict.classification]);

  // An override has to change something, or it is a confirm in disguise and
  // would distort the reviewer-agreement figure.
  const unchanged = mode === "override" && corrected === report.verdict.classification;
  const reasonOk = reason.trim().length >= 3;

  const submit = async () => {
    setBusy(true);
    setError(undefined);
    try {
      await api.review(report.id, {
        reviewer_role: role,
        decision: mode,
        reason,
        ...(mode === "override" ? { corrected_classification: corrected } : {}),
      });
      onOpenChange(false);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{mode === "confirm" ? "Confirm verdict" : "Override verdict"}</DialogTitle>
          <DialogDescription>
            Your decision is stored as a new record. The engine's verdict is never edited or
            deleted, so an auditor can always see what the system said before a human touched it.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 px-5 py-4">
          <div className="flex gap-2">
            <Button
              variant={mode === "confirm" ? "confirm" : "outline"}
              size="sm"
              onClick={() => setMode("confirm")}
            >
              <Check /> Confirm
            </Button>
            <Button
              variant={mode === "override" ? "override" : "outline"}
              size="sm"
              onClick={() => setMode("override")}
            >
              <PenLine /> Override
            </Button>
          </div>

          <label className="block space-y-1">
            <span className="text-2xs text-ink-muted">Your role</span>
            <Input value={role} onChange={(e) => setRole(e.target.value)} />
          </label>

          {mode === "override" && (
            <label className="block space-y-1">
              <span className="text-2xs text-ink-muted">Corrected classification</span>
              <Select value={corrected} onChange={(e) => setCorrected(e.target.value as SifClassification)}>
                {CLASSES.map((c) => (
                  <option key={c} value={c}>
                    {CLASSIFICATION_LABEL[c]}{c === report.verdict.classification ? " (engine)" : ""}
                  </option>
                ))}
              </Select>
            </label>
          )}

          <label className="block space-y-1">
            <span className="text-2xs text-ink-muted">
              Reason <span className="text-ink-faint">(required, at least 3 characters)</span>
            </span>
            <Textarea
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={
                mode === "confirm"
                  ? "e.g. Agreed — harness was genuinely absent."
                  : "e.g. Harness was worn; the reporter omitted it from the write-up."
              }
            />
          </label>

          {unchanged && (
            <p className="text-2xs text-status-warning">
              Pick a classification different from the engine's{" "}
              ({CLASSIFICATION_LABEL[report.verdict.classification]}) to override.
            </p>
          )}
          {error && <p role="alert" className="text-xs text-status-critical">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button
            size="sm"
            variant={mode === "confirm" ? "confirm" : "override"}
            disabled={busy || !reasonOk || unchanged}
            onClick={submit}
          >
            {busy ? "Saving…" : mode === "confirm" ? "Confirm verdict" : "Save override"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
