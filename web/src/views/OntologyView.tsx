import { useMemo, useState } from "react";
import { BookOpen, Link2, Search, ShieldCheck, ShieldX, Sparkles, Zap } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { QueryBoundary } from "@/components/StateViews";
import { api } from "@/lib/api";
import { useQuery } from "@/lib/useQuery";
import { CONTROL_STATUS_LABEL, ENERGY_LABEL, LSR_LABEL } from "@/lib/format";
import { CONTROL_TONE } from "@/lib/theme";
import type { Ontology } from "@/types/api";

/**
 * Ontology Explorer. Renders GET /api/ontology, which is read straight from
 * `prahari.domain` — the browser holds no copy of the vocabulary, so this page
 * can only ever describe the rule set the engine actually runs.
 */

const hit = (q: string, ...fields: (string | null | undefined)[]) =>
  !q || fields.some((f) => f?.toLowerCase().includes(q));

function Chip({ children, tone }: { children: React.ReactNode; tone?: string }) {
  return (
    <span
      className="inline-block border px-1.5 py-0.5 text-2xs"
      style={
        tone
          ? { color: tone, borderColor: `${tone}59`, backgroundColor: `${tone}1a` }
          : undefined
      }
    >
      {children}
    </span>
  );
}

function Count({ n }: { n: number }) {
  return <span className="tnum ml-1.5 text-ink-faint">{n}</span>;
}

function EnergyTab({ o, q }: { o: Ontology; q: string }) {
  const rows = o.energy_sources.filter((e) =>
    hit(q, e.label, e.definition, ...e.trigger_phrases, ...e.high_energy_cues.map((c) => c.label)),
  );
  if (!rows.length) return <NoMatch />;
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {rows.map((e) => {
        const phrases = q ? e.trigger_phrases.filter((p) => p.includes(q)) : e.trigger_phrases.slice(0, 10);
        return (
          <Card key={e.value} className="animate-fade-in">
            <CardHeader>
              <CardTitle className="inline-flex items-center gap-2">
                <Zap className="size-3.5 text-cue-energy" /> {e.label}
              </CardTitle>
              <CardDescription>{e.definition}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2.5 text-2xs">
              <div className="space-y-1">
                <p className="uppercase tracking-wide text-ink-faint">
                  Trigger phrases<Count n={e.trigger_phrases.length} />
                </p>
                <div className="flex flex-wrap gap-1">
                  {phrases.map((p) => <Chip key={p} tone="#3987e5">{p}</Chip>)}
                  {!q && e.trigger_phrases.length > phrases.length && (
                    <span className="text-ink-faint">+{e.trigger_phrases.length - phrases.length} more</span>
                  )}
                </div>
              </div>
              {e.high_energy_cues.length > 0 && (
                <p className="text-ink-muted">
                  <span className="text-ink-faint">High-energy cues: </span>
                  {e.high_energy_cues.map((c) => c.label).join(" · ")}
                </p>
              )}
              <div className="flex flex-wrap items-center gap-1">
                <span className="text-ink-faint">Engages:</span>
                {e.life_saving_rules.length
                  ? e.life_saving_rules.map((r) => <Chip key={r}>{LSR_LABEL[r]}</Chip>)
                  : <span className="text-ink-faint">—</span>}
              </div>
              <p className="text-ink-faint">
                {e.direct_controls.length} direct control{e.direct_controls.length === 1 ? "" : "s"} defined
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function BarrierTab({ o, q }: { o: Ontology; q: string }) {
  const rows = o.barrier_states.filter((s) => hit(q, s.value, CONTROL_STATUS_LABEL[s.value], s.meaning));
  return (
    <div className="space-y-3">
      <Card>
        <CardHeader>
          <CardTitle>The three-part direct control test</CardTitle>
          <CardDescription>
            A barrier counts only if all three hold (EEI HECA). Only a <em>verified</em> direct
            control protects.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ol className="list-decimal space-y-1 pl-4 text-xs text-ink-muted">
            {o.direct_control_test.map((t) => <li key={t}>{t}</li>)}
          </ol>
        </CardContent>
      </Card>
      {rows.length === 0 ? <NoMatch /> : (
        <Card>
          <ul className="divide-y divide-line">
            {rows.map((s) => {
              const tone = CONTROL_TONE[s.value];
              return (
                <li key={s.value} className="flex items-start gap-3 px-4 py-3">
                  {s.protective
                    ? <ShieldCheck className="mt-0.5 size-4 shrink-0 text-status-good" />
                    : <ShieldX className="mt-0.5 size-4 shrink-0" style={{ color: tone.fg }} />}
                  <div className="min-w-0 space-y-0.5">
                    <p className="flex flex-wrap items-center gap-2 text-xs font-medium text-ink">
                      {CONTROL_STATUS_LABEL[s.value]}
                      <code className="text-2xs font-normal text-ink-faint">{s.value}</code>
                      <Chip tone={s.protective ? "#0ca30c" : tone.fg}>
                        {s.protective ? "protective" : "not protective"}
                      </Chip>
                    </p>
                    <p className="text-xs leading-relaxed text-ink-muted">{s.meaning}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      )}
    </div>
  );
}

function LsrTab({ o, q }: { o: Ontology; q: string }) {
  const rows = o.life_saving_rules.filter((r) =>
    hit(q, LSR_LABEL[r.value], r.short_name, ...r.statements, ...r.trigger_phrases),
  );
  return (
    <div className="space-y-3">
      {rows.length === 0 ? <NoMatch /> : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((r) => (
            <Card key={r.value} className="animate-fade-in">
              <CardHeader>
                <CardTitle>{LSR_LABEL[r.value]}</CardTitle>
                <CardDescription>{r.short_name}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-2xs">
                <ul className="space-y-1 text-ink-muted">
                  {r.statements.map((s) => <li key={s}>“{s}”</li>)}
                </ul>
                <div className="flex flex-wrap items-center gap-1">
                  <span className="text-ink-faint">Energy:</span>
                  {r.related_energy_sources.map((e) => <Chip key={e} tone="#3987e5">{ENERGY_LABEL[e]}</Chip>)}
                </div>
                <p className="text-ink-faint">
                  {r.trigger_phrases.length} trigger phrases · {r.origin}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      <Card>
        <CardHeader>
          <CardTitle className="inline-flex items-center gap-2">
            <Sparkles className="size-3.5 text-series-4" /> prahari extensions
          </CardTitle>
          <CardDescription>Modelling choices of our own, labelled so nobody credits them to IOGP or EEI.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-3 sm:grid-cols-2">
            {o.prahari_extensions.map((x) => (
              <div key={x.name}>
                <dt className="text-xs font-medium text-ink">{x.name}</dt>
                <dd className="text-2xs leading-relaxed text-ink-muted">{x.detail}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}

function RelationshipsTab({ o, q }: { o: Ontology; q: string }) {
  const rows = o.controls.filter((c) =>
    hit(q, c.label, c.key, c.rationale, c.energy_source ?? "", ...c.life_saving_rules.map((r) => LSR_LABEL[r])),
  );
  if (!rows.length) return <NoMatch />;
  const classLabel = { direct_absolute: "Direct · absolute", direct_mitigating: "Direct · mitigating", indirect: "Indirect" };
  return (
    <Card>
      <CardHeader>
        <CardTitle className="inline-flex items-center gap-2">
          <Link2 className="size-3.5 text-series-3" /> Barrier → energy → Life-Saving Rule
        </CardTitle>
        <CardDescription>
          Each barrier the engine can recognise, the energy it guards against, and the rules that energy engages.
        </CardDescription>
      </CardHeader>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-line-strong text-2xs uppercase tracking-wide text-ink-faint">
              <th className="px-4 py-2 font-medium">Barrier</th>
              <th className="px-4 py-2 font-medium">Class</th>
              <th className="px-4 py-2 font-medium">Energy</th>
              <th className="px-4 py-2 font-medium">Life-Saving Rules</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.key} className="border-b border-line align-top last:border-b-0 hover:bg-surface-raised">
                <td className="max-w-xs px-4 py-2.5">
                  <p className="font-medium text-ink">{c.label}</p>
                  <p className="line-clamp-2 text-2xs text-ink-faint" title={c.rationale}>{c.rationale}</p>
                </td>
                <td className="whitespace-nowrap px-4 py-2.5">
                  <Chip tone={c.control_class === "indirect" ? "#6B7C8F" : "#0ca30c"}>{classLabel[c.control_class]}</Chip>
                </td>
                <td className="whitespace-nowrap px-4 py-2.5 text-ink-muted">
                  {c.energy_source ? ENERGY_LABEL[c.energy_source] : "—"}
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex flex-wrap gap-1">
                    {c.life_saving_rules.map((r) => <Chip key={r}>{LSR_LABEL[r]}</Chip>)}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function RulesTab({ o, q }: { o: Ontology; q: string }) {
  const rows = o.rules.filter((r) => hit(q, r.id, r.stage, r.summary));
  const cls = o.classifications.filter((c) => hit(q, c.label, c.value, c.definition));
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Named rules<Count n={o.rules.length} /></CardTitle>
          <CardDescription>Every rule id that can appear in an audit trail.</CardDescription>
        </CardHeader>
        <ul className="divide-y divide-line">
          {rows.map((r) => (
            <li key={r.id} className="flex items-start gap-3 px-4 py-2.5">
              <code className="w-24 shrink-0 text-2xs font-medium text-series-1">{r.id}</code>
              <div className="min-w-0">
                <p className="text-2xs uppercase tracking-wide text-ink-faint">{r.stage}</p>
                <p className="text-xs leading-relaxed text-ink-muted">{r.summary}</p>
              </div>
            </li>
          ))}
          {rows.length === 0 && <li className="px-4 py-3"><NoMatch /></li>}
        </ul>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>SCL classes<Count n={o.classifications.length} /></CardTitle>
          <CardDescription>What the rule engine can conclude. Precursor classes are what the Triage Queue surfaces.</CardDescription>
        </CardHeader>
        <ul className="divide-y divide-line">
          {cls.map((c) => (
            <li key={c.value} className="px-4 py-2.5">
              <p className="flex items-center gap-2 text-xs font-medium text-ink">
                {c.label}
                {c.precursor && <Chip tone="#ec835a">precursor</Chip>}
              </p>
              <p className="text-2xs leading-relaxed text-ink-muted">{c.definition}</p>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function NoMatch() {
  return <p className="py-6 text-center text-xs text-ink-faint">Nothing matches that search.</p>;
}

export function OntologyView() {
  const ontology = useQuery(() => api.ontology(), []);
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  const o = ontology.data;

  const counts = useMemo(
    () =>
      o && {
        energy: o.energy_sources.length,
        barrier: o.barrier_states.length,
        lsr: o.life_saving_rules.length,
        rel: o.controls.length,
        rules: o.rules.length,
      },
    [o],
  );

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <h1 className="flex items-center gap-2 text-lg font-semibold tracking-tight text-ink">
            <BookOpen className="size-5 text-series-1" />
            Ontology
            {o && (
              <span className="border border-line px-2 py-0.5 text-2xs font-normal text-ink-muted">
                {o.version}
              </span>
            )}
          </h1>
          <p className="max-w-2xl text-xs leading-relaxed text-ink-muted">
            The safety vocabulary the engine reasons with — EEI Energy Wheel, barrier states, IOGP
            Life-Saving Rules and how they connect. Served from the engine itself, not a copy.
          </p>
        </div>
        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-ink-faint" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search phrases, rules, barriers…"
            aria-label="Search the ontology"
            className="h-8 pl-8 text-xs"
          />
        </div>
      </header>

      <QueryBoundary
        loading={ontology.loading}
        offline={ontology.offline}
        error={ontology.error}
        onRetry={ontology.refetch}
      >
        {o && counts && (
          <Tabs defaultValue="energy">
            <TabsList className="flex h-auto w-full flex-wrap justify-start sm:w-auto">
              <TabsTrigger value="energy">Energy sources<Count n={counts.energy} /></TabsTrigger>
              <TabsTrigger value="barrier">Barrier states<Count n={counts.barrier} /></TabsTrigger>
              <TabsTrigger value="lsr">Life-Saving Rules<Count n={counts.lsr} /></TabsTrigger>
              <TabsTrigger value="rel">Relationships<Count n={counts.rel} /></TabsTrigger>
              <TabsTrigger value="rules">Rules &amp; classes<Count n={counts.rules} /></TabsTrigger>
            </TabsList>
            <TabsContent value="energy" className="mt-3"><EnergyTab o={o} q={q} /></TabsContent>
            <TabsContent value="barrier" className="mt-3"><BarrierTab o={o} q={q} /></TabsContent>
            <TabsContent value="lsr" className="mt-3"><LsrTab o={o} q={q} /></TabsContent>
            <TabsContent value="rel" className="mt-3"><RelationshipsTab o={o} q={q} /></TabsContent>
            <TabsContent value="rules" className="mt-3"><RulesTab o={o} q={q} /></TabsContent>
          </Tabs>
        )}
      </QueryBoundary>
    </div>
  );
}
