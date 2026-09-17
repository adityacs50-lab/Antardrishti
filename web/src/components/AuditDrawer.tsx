import { useState } from "react";
import { Link } from "react-router-dom";
import { Check, ExternalLink, Lock, PenLine } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Sheet, SheetBody, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import { ClassificationBadge } from "@/components/Chips";
import { HighlightLegend, HighlightedReport } from "@/components/HighlightedReport";
import { RuleTrace } from "@/components/RuleTrace";
import { VerdictPanel } from "@/components/VerdictPanel";
import { QueryBoundary } from "@/components/StateViews";
import { ReviewDialog } from "@/components/ReviewDialog";
import { api } from "@/lib/api";
import { useQuery } from "@/lib/useQuery";
import { CLASSIFICATION_LABEL, formatDate } from "@/lib/format";

/**
 * Everything the table row used to hide, one click away instead of a full
 * page navigation: full incident text, the rule engine's breakdown, barrier
 * status, and the confirm/override controls. `/reports/:id` still exists
 * underneath (linked at the bottom) for a shareable, printable deep link —
 * this drawer is the fast path, not a replacement for it.
 */
export function AuditDrawer({
  reportId,
  open,
  onOpenChange,
  onReviewed,
}: {
  reportId: number | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onReviewed: () => void;
}) {
  const detail = useQuery(
    () => (reportId !== null ? api.report(reportId) : Promise.reject(new Error("no report selected"))),
    [reportId],
  );
  const [activeRule, setActiveRule] = useState<string | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);

  const report = detail.data;
  const overridden = !!report && report.effective_classification !== report.verdict.classification;

  return (
    <Sheet
      open={open}
      onOpenChange={(v) => {
        onOpenChange(v);
        if (!v) setActiveRule(null);
      }}
    >
      <SheetContent widthClassName="max-w-2xl">
        <SheetHeader>
          <div className="flex items-start justify-between gap-3 pr-8">
            <div className="min-w-0 space-y-1">
              <SheetTitle className="truncate text-base">
                {report ? report.site : "Audit"}
                {report && (
                  <span className="ml-2 font-mono text-xs font-normal text-ink-faint">
                    {report.report_uid}
                  </span>
                )}
              </SheetTitle>
              <SheetDescription>
                {report ? (
                  <>
                    {formatDate(report.date)}
                    {report.activity && <> · {report.activity}</>}
                    {report.reporter_role && <> · reported by {report.reporter_role}</>}
                  </>
                ) : (
                  "Loading incident…"
                )}
              </SheetDescription>
            </div>
            {report && <ClassificationBadge value={report.effective_classification} />}
          </div>
        </SheetHeader>

        <SheetBody className="space-y-4">
          <QueryBoundary
            loading={detail.loading}
            offline={detail.offline}
            error={detail.error}
            onRetry={detail.refetch}
          >
            {report && (
              <>
                {overridden && (
                  <div className="flex flex-wrap items-center gap-2 rounded-md border border-status-warning/40 bg-status-warning/10 px-3 py-2 text-xs">
                    <PenLine className="size-3.5 shrink-0 text-status-warning" />
                    <span className="text-ink">
                      An HSE officer overrode this to{" "}
                      <strong>{CLASSIFICATION_LABEL[report.effective_classification]}</strong>. The
                      engine's original verdict is preserved below, unedited.
                    </span>
                  </div>
                )}

                <VerdictPanel verdict={report.verdict} />

                <Card>
                  <CardHeader className="space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <CardTitle>Report as submitted</CardTitle>
                      <span className="inline-flex items-center gap-1 text-2xs text-ink-faint">
                        <Lock className="size-3" /> immutable
                      </span>
                    </div>
                    <CardDescription>
                      Every highlight is a character range the rule engine actually used. Hover any
                      highlight to see which rule it fed.
                    </CardDescription>
                    <HighlightLegend />
                  </CardHeader>
                  <CardContent>
                    <HighlightedReport
                      text={report.text}
                      spans={report.evidence_spans}
                      activeRuleId={activeRule}
                      onHoverRule={setActiveRule}
                    />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Rule engine breakdown</CardTitle>
                    <CardDescription>
                      {report.verdict.fired_rules.length} named rules fired, in order. Each cites a
                      published source and the exact spans that triggered it.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <RuleTrace
                      firings={report.verdict.fired_rules}
                      activeRuleId={activeRule}
                      onHoverRule={setActiveRule}
                    />
                  </CardContent>
                </Card>

                <Link
                  to={`/reports/${report.id}`}
                  className="inline-flex items-center gap-1.5 text-2xs text-ink-muted transition-colors hover:text-ink"
                >
                  <ExternalLink className="size-3" /> Open the full report page
                </Link>
              </>
            )}
          </QueryBoundary>
        </SheetBody>

        {report && (
          <SheetFooter>
            <Button variant="confirm" size="sm" onClick={() => setReviewOpen(true)}>
              <Check /> Confirm
            </Button>
            <Button variant="override" size="sm" onClick={() => setReviewOpen(true)}>
              <PenLine /> Override
            </Button>
          </SheetFooter>
        )}

        {report && (
          <ReviewDialog
            report={report}
            open={reviewOpen}
            onOpenChange={setReviewOpen}
            onDone={() => {
              detail.refetch();
              onReviewed();
            }}
          />
        )}
      </SheetContent>
    </Sheet>
  );
}
