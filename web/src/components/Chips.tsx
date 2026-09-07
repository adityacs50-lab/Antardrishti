import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  CLASSIFICATION_LABEL, CLASSIFICATION_MEANING, CONTROL_STATUS_LABEL,
  LSR_SHORT, LSR_LABEL, BAND_LABEL,
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

/**
 * The IOGP Life-Saving Rule tag.
 *
 * A bare "No rule assigned" reads like a hole in the tagging. It is not: the
 * nine rules are a fatality-prevention set derived from 405 fatalities, and
 * they simply do not address a report with no identified energy source. Saying
 * which of the two reasons applies turns an apparent gap into a stated
 * engineering decision — which is the difference between a judge nodding and a
 * judge asking why a third of the queue is blank.
 */
export function LsrBadge({
  value,
  energySource,
  classification,
}: {
  value: LifeSavingRule | null;
  energySource?: string | null;
  classification?: SifClassification;
}) {
  if (value) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <span>
            <Badge className="border-series-1/35 bg-series-1/10 text-series-1">
              {LSR_SHORT[value]}
            </Badge>
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <strong>IOGP Life-Saving Rule — {LSR_SHORT[value]}.</strong> {LSR_LABEL[value]}
        </TooltipContent>
      </Tooltip>
    );
  }

  const illegible = classification === "insufficient_information";
  const why = illegible
    ? "This report was too sparse to classify, so it never reached the rule-tagging step. Nothing is being withheld — there was nothing to read."
    : energySource
      ? "No rule was cued in the text and none maps to this energy source."
      : "No energy source was identified in this report. The nine Life-Saving Rules address fatal-potential work; tagging a low-energy report with one would be an invention, so the engine leaves it blank on purpose.";

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span>
          <Badge className="border-dashed text-ink-muted">
            {illegible ? "No rule — unreadable" : "No rule engaged"}
          </Badge>
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">{why}</TooltipContent>
    </Tooltip>
  );
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
