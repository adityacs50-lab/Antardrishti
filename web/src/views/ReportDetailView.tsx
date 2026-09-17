import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Check, History, Lock, PenLine } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ClassificationBadge } from "@/components/Chips";
import { HighlightLegend, HighlightedReport } from "@/components/HighlightedReport";
import { RuleTrace } from "@/components/RuleTrace";
import { VerdictPanel } from "@/components/VerdictPanel";
import { HybridEnginePanel } from "@/components/HybridEnginePanel";
import { QueryBoundary } from "@/components/StateViews";
import { ReviewDialog } from "@/components/ReviewDialog";
import { api } from "@/lib/api";
import { useQuery } from "@/lib/useQuery";
import { CLASSIFICATION_LABEL, formatDate } from "@/lib/format";

export function ReportDetailView() {
  const { id } = useParams();
  const reportId = Number(id);
  const detail = useQuery(() => api.report(reportId), [reportId]);
  const [activeRule, setActiveRule] = useState<string | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);

  const report = detail.data;
  const overridden =
    !!report && report.effective_classification !== report.verdict.classification;

  return (
    <div className="space-y-4">
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-xs text-ink-muted transition-colors hover:text-ink"
      >
        <ArrowLeft className="size-3.5" /> Back to triage
      </Link>

      <QueryBoundary
        loading={detail.loading}
        offline={detail.offline}
        error={detail.error}
        onRetry={detail.refetch}
      >
        {report && (
          <>
            <header className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <h1 className="text-lg font-semibold tracking-tight text-ink">
                  {report.site}
                  <span className="ml-2 font-mono text-xs font-normal text-ink-faint">
                    {report.report_uid}
                  </span>
                </h1>
                <p className="text-xs text-ink-muted">
                  {formatDate(report.date)}
                  {report.activity && <> · {report.activity}</>}
                  {report.reporter_role && <> · reported by {report.reporter_role}</>}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="confirm" size="sm" onClick={() => setReviewOpen(true)}>
                  <Check /> Confirm
                </Button>
                <Button variant="override" size="sm" onClick={() => setReviewOpen(true)}>
                  <PenLine /> Override
                </Button>
              </div>
            </header>

            {overridden && (
              <div className="flex flex-wrap items-center gap-2 rounded-md border border-status-warning/40 bg-status-warning/10 px-3 py-2 text-xs">
                <PenLine className="size-3.5 text-status-warning" />
                <span className="text-ink">
                  An HSE officer overrode this to{" "}
                  <strong>{CLASSIFICATION_LABEL[report.effective_classification]}</strong>. The
                  engine's original verdict is preserved below, unedited.
                </span>
              </div>
            )}

            <div className="grid gap-4 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
              <div className="space-y-4">
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
                    <CardTitle>Why the engine said that</CardTitle>
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
              </div>

              <div className="space-y-4 lg:sticky lg:top-[76px] lg:self-start">
                <VerdictPanel verdict={report.verdict} />
                <HybridEnginePanel verdict={report.verdict} spans={report.evidence_spans} stacked />

                <Card>
                  <CardHeader>
                    <CardTitle className="inline-flex items-center gap-2">
                      <History className="size-4" /> Review history
                    </CardTitle>
                    <CardDescription>
                      Corrections are stored beside the verdict, never over it.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {report.reviews.length === 0 ? (
                      <p className="text-xs text-ink-faint">Not yet reviewed by a human.</p>
                    ) : (
                      <ol className="space-y-2.5">
                        {report.reviews.map((review) => (
                          <li key={review.id} className="rounded-md border border-line bg-surface-sunken p-2.5">
                            <div className="mb-1 flex flex-wrap items-center gap-2">
                              <span
                                className="text-2xs font-semibold uppercase tracking-wide"
                                style={{ color: review.decision === "confirm" ? "#0ca30c" : "#fab219" }}
                              >
                                {review.decision}
                              </span>
                              <span className="text-2xs text-ink-muted">{review.reviewer_role}</span>
                              {review.corrected_classification && (
                                <ClassificationBadge value={review.corrected_classification} />
                              )}
                            </div>
                            <p className="text-xs leading-relaxed text-ink-muted">{review.reason}</p>
                          </li>
                        ))}
                      </ol>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>

            <ReviewDialog
              report={report}
              open={reviewOpen}
              onOpenChange={setReviewOpen}
              onDone={detail.refetch}
            />
          </>
        )}
      </QueryBoundary>
    </div>
  );
}
