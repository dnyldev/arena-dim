import React, { useState } from "react";
import { ShieldCheck } from "lucide-react";
import type { RhythmDecision, RhythmInterpretation } from "../types";
import { DecisionInspector, DecisionLog, SafetyGuarantees, TrackingRegions } from "../features/laboratory";
import { Badge, Card, HelpTooltip } from "./ui";

export function RhythmLaboratory({ interpretation }: { interpretation: RhythmInterpretation }) {
  const [selected, setSelected] = useState<RhythmDecision | null>(null);
  const summary = interpretation.summary;
  const ratios = summary.tracking_ratio ?? {};
  return <div className="space-y-4">
    <Card title={<span className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-brand-600" />Rhythm interpretation</span>} subtitle="Auditable structure analysis; regularity is not claimed as correctness" actions={<HelpTooltip content="Every detection and decision remains inspectable. Correctness stays unknown until human or reference confirmation." />}>
      <div className="flex flex-wrap items-center gap-2 text-xs"><Badge tone={interpretation.mode === "observe_only" ? "info" : interpretation.mode === "off" ? "warn" : "good"}>{interpretation.mode.replace(/_/g, " ")}</Badge><span>{summary.issues ?? 0} issue(s)</span><span>{summary.changed_roles} applied role change(s)</span><span>correctness: <strong>{interpretation.correctness_verdict}</strong></span></div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">{(["tracked", "uncertain", "untracked"] as const).map((status) => <div key={status} className="rounded border border-ink-100 bg-ink-50 p-2"><div className="font-semibold text-ink-800">{((ratios[status] ?? 0)*100).toFixed(1)}%</div><div className="text-ink-500">{status}</div></div>)}</div>
    </Card>
    <Card><div className="space-y-6"><SafetyGuarantees guarantees={interpretation.guarantees} /><TrackingRegions regions={interpretation.tracking.regions} /><div className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(320px,.75fr)]"><DecisionLog decisions={interpretation.decisions} selectedId={selected?.decision_id} onSelect={setSelected} />{selected ? <DecisionInspector decision={selected} onClose={() => setSelected(null)} /> : <div className="flex min-h-32 items-center justify-center rounded-lg border border-dashed border-ink-200 bg-ink-50 text-center text-xs text-ink-500">Select a rule decision to inspect its evidence.</div>}</div></div></Card>
  </div>;
}
