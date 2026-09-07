import { Activity, Gauge, ShieldAlert, Stethoscope, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ClassificationBadge, ConfidencePill, ControlBadge, LsrBadge } from "./Chips";
import { CONTROL_STATUS_LABEL, ENERGY_LABEL, INJURY_LABEL, LSR_LABEL } from "@/lib/format";
import type { SIFVerdict } from "@/types/api";

function Row({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 py-2.5">
      <span className="inline-flex items-center gap-2 text-xs text-ink-muted">
        <span className="text-ink-faint">{icon}</span>
        {label}
      </span>
      <span className="text-right text-xs font-medium text-ink">{children}</span>
    </div>
  );
}

export function VerdictPanel({ verdict, reason }: { verdict: SIFVerdict; reason?: string }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle>Verdict</CardTitle>
        <ClassificationBadge value={verdict.classification} />
      </CardHeader>
      <CardContent className="pt-1">
        {reason && (
          <p className="mb-3 rounded-md border border-line bg-surface-sunken p-2.5 text-xs leading-relaxed text-ink-muted">
            {reason}
          </p>
        )}
        <div className="divide-y divide-line">
          <Row icon={<Zap className="size-3.5" />} label="Energy source">
            {verdict.energy_source ? ENERGY_LABEL[verdict.energy_source] : "—"}
            <span className="ml-2 text-2xs font-normal text-ink-faint">
              {verdict.high_energy ? "high energy" : "low energy"}
            </span>
          </Row>
          <Row icon={<Activity className="size-3.5" />} label="Event type">
            {verdict.high_energy_incident ? "Release occurred" : "Condition only"}
          </Row>
          <Row icon={<ShieldAlert className="size-3.5" />} label="Direct control">
            <span className="inline-flex flex-col items-end gap-1">
              <ControlBadge value={verdict.control_status} />
              {verdict.direct_control_key && (
                <span className="text-2xs font-normal text-ink-faint">
                  {verdict.direct_control_key.replace(/_/g, " ")}
                </span>
              )}
            </span>
          </Row>
          <Row icon={<Stethoscope className="size-3.5" />} label="Outcome">
            {INJURY_LABEL[verdict.injury_outcome]}
          </Row>
          <Row icon={<Gauge className="size-3.5" />} label="Evidence">
            <ConfidencePill value={verdict.evidence_completeness} />
          </Row>
        </div>

        <div className="mt-3 space-y-2 border-t border-line pt-3">
          <p className="text-2xs uppercase tracking-wide text-ink-faint">Life-Saving Rule</p>
          <div className="flex flex-wrap items-center gap-1.5">
            <LsrBadge
              value={verdict.primary_lsr}
              energySource={verdict.energy_source}
              classification={verdict.classification}
            />
            {verdict.primary_lsr && (
              <span className="text-2xs text-ink-muted">{LSR_LABEL[verdict.primary_lsr]}</span>
            )}
          </div>
          {verdict.secondary_lsr.length > 0 && (
            <p className="text-2xs text-ink-faint">
              Secondary: {verdict.secondary_lsr.map((r) => LSR_LABEL[r]).join(", ")}
              <span className="ml-1 opacity-70">(a prahari extension, not IOGP)</span>
            </p>
          )}
        </div>

        <p className="mt-3 border-t border-line pt-2 text-2xs text-ink-faint">
          {verdict.engine_version} · {verdict.extractor_version} ·{" "}
          {CONTROL_STATUS_LABEL[verdict.control_status]} control means{" "}
          {verdict.direct_control_effective ? "protected" : "unprotected"}
        </p>
      </CardContent>
    </Card>
  );
}
