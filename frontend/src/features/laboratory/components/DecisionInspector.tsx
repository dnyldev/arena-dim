import React from "react";
import { X } from "lucide-react";
import type { RhythmDecision } from "../../../types";
import { Button } from "../../../components/ui";

export function DecisionInspector({ decision, onClose }: { decision: RhythmDecision; onClose: () => void }) {
  return <section className="rounded-lg border border-brand-200 bg-brand-50/40 p-4 text-xs"><div className="flex items-center justify-between"><h3 className="font-semibold text-ink-900">Decision {decision.decision_id}</h3><Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose} aria-label="Close decision inspector"><X className="h-3.5 w-3.5" /></Button></div><div className="mt-3 grid gap-3 md:grid-cols-2"><Evidence title="Evidence for" items={decision.evidence_for} /><Evidence title="Evidence against" items={decision.evidence_against} /></div><dl className="mt-3 grid gap-1"><Row label="Reasons" value={decision.reason_codes.join(", ")} /><Row label="Thresholds" value={Object.entries(decision.thresholds).map(([k,v]) => `${k}=${v}`).join(" · ")} /><Row label="Alternatives" value={decision.alternatives.length ? decision.alternatives.map((a) => `${a.hypothesis} (${a.score.toFixed(3)})`).join(" · ") : "none"} /><Row label="Mutation applied" value={decision.mutation_applied ? "yes" : "no"} /></dl></section>;
}
function Evidence({ title, items }: { title: string; items: RhythmDecision["evidence_for"] }) { return <div><h4 className="font-semibold text-ink-800">{title}</h4><ul className="mt-1 space-y-1">{items.map((item,i) => <li key={`${item.type}-${i}`}>• {item.description}: <span className="font-mono">{String(item.value ?? "—")}</span></li>)}</ul></div>; }
function Row({ label, value }: { label: string; value: string }) { return <div><dt className="inline font-semibold">{label}: </dt><dd className="inline">{value}</dd></div>; }
