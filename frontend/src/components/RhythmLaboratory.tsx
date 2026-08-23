import React, { useState } from "react";
import type { RhythmDecision, RhythmInterpretation } from "../types";
import { Badge, Card } from "./Card";

export function RhythmLaboratory({ interpretation }: { interpretation: RhythmInterpretation }) {
  const [expanded, setExpanded] = useState(false);
  const [selected, setSelected] = useState<RhythmDecision | null>(null);
  const summary = interpretation.summary;
  const ratios = summary.tracking_ratio ?? {};

  return (
    <Card
      title="Rhythm interpretation"
      subtitle="Auditable structure analysis; regularity is not claimed as correctness"
      actions={<button type="button" onClick={() => setExpanded((v) => !v)} className="rounded border border-ink-200 px-2 py-1 text-xs text-ink-600 hover:bg-ink-50">{expanded ? "Hide laboratory" : "Open laboratory"}</button>}
    >
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <Badge tone={interpretation.mode === "observe_only" ? "info" : interpretation.mode === "off" ? "warn" : "good"}>{interpretation.mode.replace(/_/g, " ")}</Badge>
        <span>{summary.issues ?? 0} issue(s)</span>
        <span>{summary.changed_roles} applied role change(s)</span>
        <span>correctness: <strong>{interpretation.correctness_verdict}</strong></span>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
        {(["tracked", "uncertain", "untracked"] as const).map((status) => (
          <div key={status} className="rounded border border-ink-100 bg-ink-50 p-2">
            <div className="font-semibold text-ink-800">{((ratios[status] ?? 0) * 100).toFixed(1)}%</div>
            <div className="text-ink-500">{status}</div>
          </div>
        ))}
      </div>
      {expanded && (
        <div className="mt-5 space-y-5 border-t border-ink-100 pt-5">
          <Guarantees interpretation={interpretation} />
          <Regions interpretation={interpretation} />
          <DecisionLog decisions={interpretation.decisions} onSelect={setSelected} />
          {selected && <DecisionInspector decision={selected} onClose={() => setSelected(null)} />}
        </div>
      )}
    </Card>
  );
}

function Guarantees({ interpretation }: { interpretation: RhythmInterpretation }) {
  const g = interpretation.guarantees;
  return (
    <section>
      <h3 className="text-sm font-semibold text-ink-800">Safety guarantees</h3>
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs md:grid-cols-4">
        <Guard ok={g.raw_immutable} text="Raw immutable" />
        <Guard ok={!g.timestamps_changed} text="No moved timestamps" />
        <Guard ok={g.beats_inserted === 0} text="No inserted beats" />
        <Guard ok={g.beats_deleted === 0} text="No deleted beats" />
      </div>
    </section>
  );
}

function Guard({ ok, text }: { ok: boolean; text: string }) {
  return <div className={`rounded border px-2 py-1.5 ${ok ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-rose-200 bg-rose-50 text-rose-700"}`}>{ok ? "✓" : "!"} {text}</div>;
}

function Regions({ interpretation }: { interpretation: RhythmInterpretation }) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-ink-800">Tracking regions</h3>
      <div className="mt-2 flex min-h-12 overflow-hidden rounded border border-ink-200">
        {interpretation.tracking.regions.map((region) => {
          const width = Math.max(3, region.end_sec - region.start_sec);
          const color = region.status === "tracked" ? "bg-emerald-100 text-emerald-800" : region.status === "uncertain" ? "bg-amber-100 text-amber-800" : "bg-ink-100 text-ink-600";
          return <div key={region.region_id} style={{ flexGrow: width }} title={`${region.start_sec.toFixed(2)}–${region.end_sec.toFixed(2)}s · ${region.reason_codes.join(", ")}`} className={`flex min-w-0 items-center justify-center border-r border-white px-1 text-[10px] ${color}`}>{region.status}</div>;
        })}
      </div>
    </section>
  );
}

function DecisionLog({ decisions, onSelect }: { decisions: RhythmDecision[]; onSelect: (d: RhythmDecision) => void }) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-ink-800">Rule log</h3>
      {decisions.length === 0 ? <p className="mt-2 text-xs text-ink-500">No rule decisions were needed.</p> : (
        <div className="mt-2 max-h-64 overflow-auto rounded border border-ink-200">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-ink-50 text-ink-500"><tr><th className="p-2">Rule</th><th>Target</th><th>Decision</th><th>Confidence</th></tr></thead>
            <tbody>{decisions.map((decision) => <tr key={decision.decision_id} onClick={() => onSelect(decision)} className="cursor-pointer border-t border-ink-100 hover:bg-brand-50"><td className="p-2">{decision.rule.id}@{decision.rule.version}</td><td>{decision.target_event_ids.join(", ")}</td><td>{decision.action}</td><td>{(decision.decision_confidence * 100).toFixed(1)}%</td></tr>)}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function DecisionInspector({ decision, onClose }: { decision: RhythmDecision; onClose: () => void }) {
  return (
    <section className="rounded-lg border border-brand-200 bg-brand-50/40 p-4 text-xs">
      <div className="flex justify-between"><h3 className="font-semibold text-ink-900">Decision {decision.decision_id}</h3><button onClick={onClose} aria-label="Close decision inspector">×</button></div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <Evidence title="Evidence for" items={decision.evidence_for} />
        <Evidence title="Evidence against" items={decision.evidence_against} />
      </div>
      <div className="mt-3"><strong>Reasons:</strong> {decision.reason_codes.join(", ")}</div>
      <div className="mt-1"><strong>Thresholds:</strong> {Object.entries(decision.thresholds).map(([k, v]) => `${k}=${v}`).join(" · ")}</div>
      <div className="mt-1"><strong>Alternatives:</strong> {decision.alternatives.length ? decision.alternatives.map((a) => `${a.hypothesis} (${a.score.toFixed(3)})`).join(" · ") : "none"}</div>
      <div className="mt-1"><strong>Mutation applied:</strong> {decision.mutation_applied ? "yes" : "no"}</div>
    </section>
  );
}

function Evidence({ title, items }: { title: string; items: RhythmDecision["evidence_for"] }) {
  return <div><h4 className="font-semibold text-ink-800">{title}</h4><ul className="mt-1 space-y-1">{items.map((item, i) => <li key={`${item.type}-${i}`}>• {item.description}: <span className="font-mono">{String(item.value ?? "—")}</span></li>)}</ul></div>;
}
