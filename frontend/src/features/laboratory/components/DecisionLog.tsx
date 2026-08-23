import React from "react";
import type { RhythmDecision } from "../../../types";

export function DecisionLog({ decisions, selectedId, onSelect }: { decisions: RhythmDecision[]; selectedId?: string; onSelect: (decision: RhythmDecision) => void }) {
  return <section><h3 className="text-sm font-semibold text-ink-800">Rule log</h3>{decisions.length === 0 ? <p className="mt-2 text-xs text-ink-500">No rule decisions were needed.</p> : <div className="mt-2 max-h-72 overflow-auto rounded border border-ink-200"><table className="w-full text-left text-xs"><thead className="sticky top-0 bg-ink-50 text-ink-500"><tr><th className="p-2">Rule</th><th>Target</th><th>Decision</th><th>Confidence</th></tr></thead><tbody>{decisions.map((decision) => <tr key={decision.decision_id} onClick={() => onSelect(decision)} aria-selected={selectedId === decision.decision_id} className="cursor-pointer border-t border-ink-100 hover:bg-brand-50 aria-selected:bg-brand-50"><td className="p-2">{decision.rule.id}@{decision.rule.version}</td><td>{decision.target_event_ids.join(", ")}</td><td>{decision.action}</td><td>{(decision.decision_confidence*100).toFixed(1)}%</td></tr>)}</tbody></table></div>}</section>;
}
