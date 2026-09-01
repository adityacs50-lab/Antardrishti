import { BookOpen, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { cueOf } from "./HighlightedReport";
import { CUE } from "@/lib/theme";
import type { RuleFiring } from "@/types/api";

const CITATION_LABEL: Record<string, string> = {
  EEI_HECA: "EEI High-Energy Control Assessment",
  EEI_SCL: "EEI Safety Classification & Learning Model",
  HALLOWELL_PSJ_2023: "Hallowell, Professional Safety Journal 2023",
  INGAA_HEHC_2024: "INGAA Pipeline High-Energy Hazards Inventory 2024",
  IOGP_459: "IOGP Report 459 — Life-Saving Rules",
  PRAHARI_MODELLING: "prahari modelling decision (not external literature)",
};

/**
 * The audit trail. This component is the product's entire argument: every
 * verdict is a chain of named rules, each citing a published source and the
 * exact characters that triggered it.
 */
export function RuleTrace({
  firings,
  activeRuleId,
  onHoverRule,
}: {
  firings: RuleFiring[];
  activeRuleId?: string | null;
  onHoverRule?: (ruleId: string | null) => void;
}) {
  return (
    <ol className="space-y-1.5" onMouseLeave={() => onHoverRule?.(null)}>
      {firings.map((firing, i) => {
        const kind = cueOf(firing.rule_id);
        const isActive = activeRuleId === firing.rule_id;
        const isPrahari = firing.citation_key === "PRAHARI_MODELLING";
        return (
          <li
            key={`${firing.rule_id}-${i}`}
            onMouseEnter={() => onHoverRule?.(firing.rule_id)}
            className={cn(
              "rounded-md border border-line bg-surface-sunken p-3 transition-colors",
              isActive && "border-line-strong bg-surface-raised",
            )}
          >
            <div className="flex items-start gap-2.5">
              <span
                aria-hidden
                className="mt-1 h-3 w-[3px] shrink-0 rounded-full"
                style={{ backgroundColor: CUE[kind] }}
              />
              <div className="min-w-0 flex-1 space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <code className="rounded bg-surface-raised px-1.5 py-0.5 text-2xs font-semibold text-ink">
                    {firing.rule_id}
                  </code>
                  <span className="inline-flex items-center gap-1 text-2xs text-ink-muted">
                    <ChevronRight className="size-3" />
                    <span className="font-medium text-ink">{firing.conclusion}</span>
                  </span>
                </div>
                <p className="text-xs leading-relaxed text-ink-muted">{firing.description}</p>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pt-0.5">
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 text-2xs",
                      isPrahari ? "text-status-warning" : "text-ink-faint",
                    )}
                    title={
                      isPrahari
                        ? "A prahari modelling decision, not a published source. Flagged so it is never presented as literature."
                        : undefined
                    }
                  >
                    <BookOpen className="size-3" />
                    {CITATION_LABEL[firing.citation_key] ?? firing.citation_key}
                  </span>
                  {firing.spans.length > 0 && (
                    <span className="tnum text-2xs text-ink-faint">
                      {firing.spans.length} span{firing.spans.length === 1 ? "" : "s"} in text
                    </span>
                  )}
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
