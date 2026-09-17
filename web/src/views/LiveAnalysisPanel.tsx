import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Sparkles, Trash2, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, Textarea } from "@/components/ui/input";
import { ClassificationBadge, ConfidencePill, ControlBadge, LsrBadge } from "@/components/Chips";
import { HighlightLegend, HighlightedReport } from "@/components/HighlightedReport";
import { RuleTrace } from "@/components/RuleTrace";
import { HybridEnginePanel } from "@/components/HybridEnginePanel";
import { OfflineState } from "@/components/StateViews";
import { api, ApiError } from "@/lib/api";
import { ENERGY_LABEL } from "@/lib/format";
import { cn } from "@/lib/utils";
import { CLASSIFICATION_TONE } from "@/lib/theme";
import type { AnalyzeResult, SifClassification } from "@/types/api";
import DEMO_SCENARIOS from "@/data/demo-scenarios.json";

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

/**
 * The four one-click judging scenarios. Their text lives in
 * `src/data/demo-scenarios.json`, which `backend/tests/test_demo_scenarios.py`
 * reads too — so each button's declared verdict is verified by the test suite
 * against exactly the text shown here.
 */
const SCENARIOS = DEMO_SCENARIOS as {
  id: string;
  short: string;
  label: string;
  note: string;
  text: string;
  expect: { classification: SifClassification };
}[];

const ALL_PRESETS = [
  ...EXAMPLES,
  ...SCENARIOS.map(({ id, label, note, text }) => ({ id, label, note, text })),
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
    const example = ALL_PRESETS.find((e) => e.id === id);
    if (!example) return;
    setSelected(id);
    setText(example.text);
    // A preset is a deliberate choice, not typing: analyse it now rather than
    // after the typing debounce. The effect below still fires, and its
    // identical request simply lands second.
    window.clearTimeout(debounce.current);
    void run(example.text);
  };

  const note = ALL_PRESETS.find((e) => e.id === selected)?.note;

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
        <div className="space-y-1.5">
          <p className="inline-flex items-center gap-1.5 text-2xs uppercase tracking-wide text-ink-faint">
            <Zap className="size-3" /> Demo scenarios · one click loads and analyses
          </p>
          <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
            {SCENARIOS.map((s) => {
              const tone = CLASSIFICATION_TONE[s.expect.classification];
              const active = selected === s.id;
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => pick(s.id)}
                  aria-pressed={active}
                  className={cn(
                    "group flex flex-col items-start gap-1 border px-3 py-2 text-left transition-all duration-150 hover:-translate-y-px hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40",
                    active ? "border-accent bg-surface-raised" : "border-line bg-surface-sunken",
                  )}
                >
                  <span className="inline-flex items-center gap-1.5 text-xs font-medium text-ink">
                    <span className="size-1.5 rounded-full" style={{ backgroundColor: tone.fg }} aria-hidden />
                    {s.short}
                  </span>
                  <span className="line-clamp-2 text-2xs leading-snug text-ink-faint">{s.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Select
            aria-label="Example report"
            value={selected}
            onChange={(e) => pick(e.target.value)}
            className="max-w-sm flex-1"
          >
            {selected === "" && <option value="">Custom text</option>}
            <optgroup label="DEMO.md runbook">
              {EXAMPLES.map((e) => (
                <option key={e.id} value={e.id}>{e.label}</option>
              ))}
            </optgroup>
            <optgroup label="Demo scenarios">
              {SCENARIOS.map((e) => (
                <option key={e.id} value={e.id}>{e.short} · {e.label}</option>
              ))}
            </optgroup>
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
          onChange={(e) => { setText(e.target.value); if (selected) setSelected(""); }}
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

            <HybridEnginePanel verdict={result.verdict} spans={result.evidence_spans} />

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
