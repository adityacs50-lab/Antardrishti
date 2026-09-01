import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Sparkles, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, Textarea } from "@/components/ui/input";
import { ClassificationBadge, ConfidencePill, ControlBadge, LsrBadge } from "@/components/Chips";
import { HighlightLegend, HighlightedReport } from "@/components/HighlightedReport";
import { RuleTrace } from "@/components/RuleTrace";
import { OfflineState } from "@/components/StateViews";
import { api, ApiError } from "@/lib/api";
import { ENERGY_LABEL } from "@/lib/format";
import type { AnalyzeResult } from "@/types/api";

/** Three reports chosen to show the range, including a code-mixed one. */
/**
 * The three demo reports, in the order DEMO.md presents them.
 *
 * They are in the dropdown rather than only in the runbook on purpose: pasting
 * into a textarea on stage depends on a clipboard that may not survive a
 * screen-share, a remote desktop or a borrowed laptop. One click cannot fail
 * that way. The textarea still accepts anything a judge wants to type.
 */
const EXAMPLES: { id: string; label: string; note: string; text: string }[] = [
  {
    id: "1-low",
    label: "1 · Cut finger in the workshop",
    note: "Real injury, zero fatal potential — the case a severity model over-ranks",
    text:
      "On 03.07.2026, Sri R. Das (fitter) was cutting GI sheet at the workshop, " +
      "Duliajan. Hand gloves were not worn while doing the job. The blade slipped " +
      "and he sustained a cut on the left index finger. First aid was given at the " +
      "installation and he resumed duty.",
  },
  {
    id: "2-psif",
    label: "2 · Pumping unit guard missing, Moran",
    note: "Nobody hurt, fatal potential real — the case a severity model scores as nothing",
    text:
      "On 28.08.2026 at abt 1115 hrs, Sri B. Gogoi (fitter) was attending the belt " +
      "of the pumping unit at Well No. 214, Moran. The machine guard was missing " +
      "from the drive and the unit was not isolated at the panel. The belt started " +
      "on auto while he was still inside the guard area. There was no injury to any " +
      "personnel. Job stopped and area barricaded.",
  },
  {
    id: "3-codemix",
    label: "3 · Casing lowering (Assamese / Hindi mixed)",
    note: "Code-mixed field writing — the register the engine actually has to read",
    text:
      "Rig no 33 Duliajan t kaam kori asil, casing lowering job cholise. Load " +
      "approx 2500 kg abut 4 mtr height t thakil. Sling ka condition kharab tha aur " +
      "koi secondary retention nahi tha. \u0939\u0920\u093e\u0924\u094d the sling parted and the load dropped " +
      "from abt 4 mtr. \u0995\u09cb\u09a8\u09cb \u0986\u0998\u09be\u09a4 \u09b9\u09cb\u09f1\u09be \u09a8\u09be\u0987. supervisor k koisilo, kaam bondho kora hol.",
  },
];

export function LiveAnalysisPanel() {
  const [text, setText] = useState(EXAMPLES[0].text);
  const [selected, setSelected] = useState(EXAMPLES[0].id);
  const [result, setResult] = useState<AnalyzeResult>();
  const [error, setError] = useState<string>();
  const [offline, setOffline] = useState(false);
  const [busy, setBusy] = useState(false);
  const [activeRule, setActiveRule] = useState<string | null>(null);
  const debounce = useRef<number>();

  const run = useCallback(async (value: string) => {
    if (!value.trim()) {
      setResult(undefined);
      setError(undefined);
      return;
    }
    setBusy(true);
    try {
      setResult(await api.analyze(value));
      setError(undefined);
      setOffline(false);
    } catch (err) {
      setResult(undefined);
      setOffline(err instanceof ApiError && err.status === undefined);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }, []);

  // Analyse as you type. The verdict comes from the same engine the queue uses —
  // there is no client-side copy of the rules anywhere in this app.
  useEffect(() => {
    window.clearTimeout(debounce.current);
    debounce.current = window.setTimeout(() => void run(text), 350);
    return () => window.clearTimeout(debounce.current);
  }, [text, run]);

  const pick = (id: string) => {
    const example = EXAMPLES.find((e) => e.id === id);
    if (!example) return;
    setSelected(id);
    setText(example.text);
  };

  const note = EXAMPLES.find((e) => e.id === selected)?.note;

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
        <div className="space-y-1">
          <CardTitle className="inline-flex items-center gap-2">
            <Sparkles className="size-4 text-series-1" />
            Live Analysis
          </CardTitle>
          <CardDescription>
            Paste any report. The verdict comes from the same rule engine that scored the queue —
            nothing is analysed in the browser.
          </CardDescription>
        </div>
        {busy && <Loader2 className="mt-1 size-4 animate-spin text-ink-faint" />}
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Select
            aria-label="Example report"
            value={selected}
            onChange={(e) => pick(e.target.value)}
            className="max-w-sm flex-1"
          >
            {EXAMPLES.map((e) => (
              <option key={e.id} value={e.id}>{e.label}</option>
            ))}
          </Select>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { setText(""); setSelected(""); }}
            disabled={!text}
          >
            <Trash2 /> Clear
          </Button>
        </div>
        {note && <p className="text-2xs italic text-ink-faint">{note}</p>}

        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={6}
          spellCheck={false}
          placeholder="Paste an unsafe-act, unsafe-condition or near-miss report…"
          aria-label="Report text to analyse"
        />

        {offline ? (
          <OfflineState onRetry={() => void run(text)} />
        ) : error ? (
          <p className="rounded-md border border-status-warning/40 bg-status-warning/10 px-3 py-2 text-xs text-status-warning">
            {error}
          </p>
        ) : result ? (
          <div className="animate-fade-in space-y-3">
            <div className="flex flex-wrap items-center gap-2 rounded-md border border-line bg-surface-sunken px-3 py-2.5">
              <ClassificationBadge value={result.verdict.classification} />
              <ControlBadge value={result.verdict.control_status} />
              <LsrBadge value={result.verdict.primary_lsr} />
              {result.verdict.energy_source && (
                <span className="text-2xs text-ink-muted">
                  {ENERGY_LABEL[result.verdict.energy_source]} ·{" "}
                  {result.verdict.high_energy ? "high energy" : "low energy"}
                </span>
              )}
              <span className="ml-auto"><ConfidencePill value={result.verdict.evidence_completeness} /></span>
            </div>

            <p className="text-xs leading-relaxed text-ink-muted">{result.reason}</p>

            <div className="rounded-md border border-line bg-surface-sunken p-3">
              <HighlightLegend className="mb-2.5" />
              <HighlightedReport
                text={result.text}
                spans={result.evidence_spans}
                activeRuleId={activeRule}
                onHoverRule={setActiveRule}
                className="text-sm leading-[1.8]"
              />
            </div>

            <details className="group">
              <summary className="cursor-pointer text-2xs text-ink-muted transition-colors hover:text-ink">
                {result.verdict.fired_rules.length} rules fired — show the audit trail
              </summary>
              <div className="mt-2">
                <RuleTrace
                  firings={result.verdict.fired_rules}
                  activeRuleId={activeRule}
                  onHoverRule={setActiveRule}
                />
              </div>
            </details>
          </div>
        ) : (
          <p className="py-4 text-center text-xs text-ink-faint">
            Type or pick an example to see a verdict.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
