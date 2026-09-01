import { useMemo } from "react";
import { cn } from "@/lib/utils";
import type { EvidenceSpan } from "@/types/api";

export type CueKind = "energy" | "control" | "context";

/**
 * Which rule produced a span decides its colour.
 *
 * The two the brief names get the two strongest hues: the hazard (energy) and
 * the barrier (control). Everything else is context. Colour is paired with a
 * distinct underline style in index.css, so identity survives colour-blindness,
 * printing and forced-colours mode.
 */
export function cueOf(ruleId: string | null | undefined): CueKind {
  if (!ruleId) return "context";
  if (ruleId.startsWith("R-CTRL") || ruleId.startsWith("R-EFFECT")) return "control";
  if (ruleId.startsWith("R-ENERGY") || ruleId.startsWith("R-HE")) return "energy";
  return "context";
}

/** Overlaps resolve to the most actionable layer: the failed barrier. */
const PRIORITY: Record<CueKind, number> = { control: 3, energy: 2, context: 1 };

interface Segment {
  start: number;
  end: number;
  kind: CueKind | null;
  ruleIds: string[];
}

function segment(text: string, spans: EvidenceSpan[]): Segment[] {
  const n = text.length;
  if (!spans.length || !n) return [{ start: 0, end: n, kind: null, ruleIds: [] }];

  // Per-character winner, so overlapping spans never produce nested markup.
  const kinds = new Array<CueKind | null>(n).fill(null);
  const rules: Array<Set<string>> = Array.from({ length: n }, () => new Set<string>());

  for (const span of spans) {
    const kind = cueOf(span.rule_id);
    const from = Math.max(0, span.start);
    const to = Math.min(n, span.end);
    for (let i = from; i < to; i++) {
      if (span.rule_id) rules[i].add(span.rule_id);
      const current = kinds[i];
      if (current === null || PRIORITY[kind] > PRIORITY[current]) kinds[i] = kind;
    }
  }

  const out: Segment[] = [];
  let cursor = 0;
  const keyOf = (i: number) => `${kinds[i] ?? "-"}|${[...rules[i]].sort().join(",")}`;
  for (let i = 1; i <= n; i++) {
    if (i === n || keyOf(i) !== keyOf(cursor)) {
      out.push({ start: cursor, end: i, kind: kinds[cursor], ruleIds: [...rules[cursor]].sort() });
      cursor = i;
    }
  }
  return out;
}

export function HighlightedReport({
  text,
  spans,
  activeRuleId,
  onHoverRule,
  className,
}: {
  text: string;
  spans: EvidenceSpan[];
  activeRuleId?: string | null;
  onHoverRule?: (ruleId: string | null) => void;
  className?: string;
}) {
  const segments = useMemo(() => segment(text, spans), [text, spans]);

  return (
    <p
      className={cn(
        "whitespace-pre-wrap break-words text-[15px] leading-[1.85] text-ink",
        className,
      )}
      onMouseLeave={() => onHoverRule?.(null)}
    >
      {segments.map((seg, i) => {
        const body = text.slice(seg.start, seg.end);
        if (!seg.kind) return <span key={i}>{body}</span>;
        const isActive = !!activeRuleId && seg.ruleIds.includes(activeRuleId);
        return (
          <span
            key={i}
            className={cn("cue", `cue-${seg.kind}`, isActive && "cue-active")}
            title={seg.ruleIds.join(" · ")}
            onMouseEnter={() => onHoverRule?.(seg.ruleIds[0] ?? null)}
          >
            {body}
          </span>
        );
      })}
    </p>
  );
}

export function HighlightLegend({ className }: { className?: string }) {
  const items: { kind: CueKind; label: string; hint: string }[] = [
    { kind: "energy", label: "Energy cue", hint: "What could hurt someone" },
    { kind: "control", label: "Control state", hint: "The barrier, and whether it held" },
    { kind: "context", label: "Outcome & rule", hint: "Injury, event type, rule triggers" },
  ];
  return (
    <div className={cn("flex flex-wrap items-center gap-x-4 gap-y-1.5", className)}>
      {items.map((item) => (
        <span key={item.kind} className="inline-flex items-center gap-1.5" title={item.hint}>
          <span className={cn("cue", `cue-${item.kind}`, "px-2 py-0")}>&nbsp;</span>
          <span className="text-2xs text-ink-muted">{item.label}</span>
        </span>
      ))}
    </div>
  );
}
