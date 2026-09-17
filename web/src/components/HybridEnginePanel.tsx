import { ArrowRight, Brain, Cpu, Scale } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ClassificationBadge } from "@/components/Chips";
import { api } from "@/lib/api";
import { useQuery } from "@/lib/useQuery";
import { pct } from "@/lib/format";
import type { EvidenceSpan, SIFVerdict } from "@/types/api";

/**
 * How this verdict was produced, layer by layer.
 *
 * prahari is neuro-symbolic: the NLP layer EXTRACTS facts, the rule engine
 * DECIDES. There is no probability fusion - the final verdict is the rule
 * engine's alone (CLAUDE.md). So this panel does not invent "ML confidence"
 * or "fused confidence" percentages. It shows what each layer actually
 * contributed to THIS report, plus the measured recall of the pipeline that
 * produced it, which is the honest answer to "how much should I trust this?".
 */
export function HybridEnginePanel({
  verdict,
  spans,
  stacked = false,
}: {
  verdict: SIFVerdict;
  spans: EvidenceSpan[];
  /** Force a vertical layout for narrow sidebars. */
  stacked?: boolean;
}) {
  const health = useQuery(() => api.health(), []);
  const metrics = useQuery(() => api.engineMetrics(), []);

  const neural = health.data?.extractor === "NEURAL";
  const uniqueSpans = new Set(spans.map((s) => `${s.start}:${s.end}`)).size;
  const slots = Math.round(verdict.evidence_completeness * 4);
  const bench = metrics.data?.benchmark;
  const recall = bench?.splits[bench.headline_split].precursor_detection.recall;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle className="inline-flex items-center gap-2">
          <Scale className="size-4 text-series-1" />
          Hybrid engine signal
        </CardTitle>
        <span className="text-2xs text-ink-faint">neuro-symbolic</span>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className={stacked ? "grid gap-2" : "grid items-stretch gap-2 sm:grid-cols-[1fr_auto_1fr_auto_1fr]"}>
          {/* Layer 1 — NLP / ML extraction */}
          <div className="space-y-1.5 border border-line bg-surface-sunken p-3">
            <p className="inline-flex items-center gap-1.5 text-2xs uppercase tracking-wide text-ink-faint">
              <Brain className="size-3.5" style={{ color: "#199e70" }} /> 1 · NLP extraction
            </p>
            {health.loading && !health.data ? (
              <Skeleton className="h-6 w-24" />
            ) : (
              <p className="tnum text-lg font-semibold leading-none text-ink">
                {slots}/4 <span className="text-2xs font-normal text-ink-muted">fact slots</span>
              </p>
            )}
            <p className="text-2xs leading-relaxed text-ink-faint">
              {uniqueSpans} evidence span{uniqueSpans === 1 ? "" : "s"} ·{" "}
              {health.data
                ? neural
                  ? "MuRIL ONNX model + lexicon"
                  : "keyword lexicon (ONNX model not loaded)"
                : "extractor status unknown"}
            </p>
          </div>

          <ArrowRight className={stacked ? "hidden" : "mx-auto hidden size-4 self-center text-ink-faint sm:block"} aria-hidden />

          {/* Layer 2 — deterministic rules */}
          <div className="space-y-1.5 border border-line bg-surface-sunken p-3">
            <p className="inline-flex items-center gap-1.5 text-2xs uppercase tracking-wide text-ink-faint">
              <Cpu className="size-3.5" style={{ color: "#3987e5" }} /> 2 · Rule engine
            </p>
            <p className="tnum text-lg font-semibold leading-none text-ink">
              {verdict.fired_rules.length}{" "}
              <span className="text-2xs font-normal text-ink-muted">named rules fired</span>
            </p>
            <p className="text-2xs leading-relaxed text-ink-faint">
              Deterministic — the same text gives the same verdict, every time.
            </p>
          </div>

          <ArrowRight className={stacked ? "hidden" : "mx-auto hidden size-4 self-center text-ink-faint sm:block"} aria-hidden />

          {/* Result */}
          <div className="space-y-1.5 border border-line-strong p-3">
            <p className="text-2xs uppercase tracking-wide text-ink-faint">Final verdict</p>
            <ClassificationBadge value={verdict.classification} />
            <p className="text-2xs leading-relaxed text-ink-faint">
              Decided by rules only.
              {recall !== undefined && (
                <> This pipeline catches {pct(recall, 1)} of precursors on held-out data.</>
              )}
            </p>
          </div>
        </div>

        <p className="border-t border-line pt-2 text-2xs leading-relaxed text-ink-muted">
          <strong className="font-medium text-ink">Hybrid engine:</strong> rules provide determinism
          &amp; explainability · ML provides generalisation on noisy field language. The model only
          finds the facts; it never outputs a severity or a class.
        </p>
      </CardContent>
    </Card>
  );
}
