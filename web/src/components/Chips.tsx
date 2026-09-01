import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  CLASSIFICATION_LABEL, CLASSIFICATION_MEANING, CONTROL_STATUS_LABEL,
  LSR_SHORT, BAND_LABEL,
} from "@/lib/format";
import { BAND_TONE, CLASSIFICATION_TONE, CONTROL_TONE, STATUS } from "@/lib/theme";
import type { Band, ControlStatus, LifeSavingRule, SifClassification } from "@/types/api";
import { cn } from "@/lib/utils";

export function ClassificationBadge({ value, className }: { value: SifClassification; className?: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span>
          <Badge tone={CLASSIFICATION_TONE[value]} dot className={cn("uppercase tracking-wide", className)}>
            {CLASSIFICATION_LABEL[value]}
          </Badge>
        </span>
      </TooltipTrigger>
      <TooltipContent>{CLASSIFICATION_MEANING[value]}</TooltipContent>
    </Tooltip>
  );
}

export function ControlBadge({ value }: { value: ControlStatus }) {
  return (
    <Badge tone={CONTROL_TONE[value]} dot>
      {CONTROL_STATUS_LABEL[value]}
    </Badge>
  );
}

export function LsrBadge({ value }: { value: LifeSavingRule | null }) {
  if (!value) return <Badge className="text-ink-faint">No rule assigned</Badge>;
  return <Badge className="border-series-1/35 bg-series-1/10 text-series-1">{LSR_SHORT[value]}</Badge>;
}

export function BandBadge({ value }: { value: Band }) {
  return (
    <Badge tone={BAND_TONE[value]} dot className="uppercase tracking-wide">
      {BAND_LABEL[value]}
    </Badge>
  );
}

/**
 * Evidence completeness, shown as a 4-segment meter.
 *
 * This is NOT a model confidence score — there is no probability anywhere in
 * prahari. It is the fraction of the four required fact slots (energy,
 * magnitude, control state, outcome) the extractor found evidence for, i.e.
 * how much of the report was legible.
 */
export function ConfidencePill({ value }: { value: number }) {
  const filled = Math.round(value * 4);
  const colour = value >= 1 ? STATUS.good : value >= 0.75 ? STATUS.warning : STATUS.serious;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex items-center gap-1.5">
          <span className="flex gap-[2px]" aria-hidden>
            {[0, 1, 2, 3].map((i) => (
              <span
                key={i}
                className="h-3 w-[3px] rounded-full"
                style={{ backgroundColor: i < filled ? colour : "hsl(var(--border-strong))" }}
              />
            ))}
          </span>
          <span className="tnum text-2xs text-ink-muted">{filled}/4</span>
        </span>
      </TooltipTrigger>
      <TooltipContent>
        <strong>Evidence completeness — not a confidence score.</strong> {filled} of 4 required
        fact slots (energy, magnitude, control state, outcome) were found in the text. It measures
        how legible the report was, not how sure the engine is.
      </TooltipContent>
    </Tooltip>
  );
}
