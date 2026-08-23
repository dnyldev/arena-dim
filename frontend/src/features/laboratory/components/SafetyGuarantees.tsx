import React from "react";
import { Check, TriangleAlert } from "lucide-react";
import type { RhythmInterpretation } from "../../../types";

export function SafetyGuarantees({ guarantees }: { guarantees: RhythmInterpretation["guarantees"] }) {
  const items = [[guarantees.raw_immutable, "Raw immutable"], [!guarantees.timestamps_changed, "No moved timestamps"], [guarantees.beats_inserted === 0, "No inserted beats"], [guarantees.beats_deleted === 0, "No deleted beats"]] as const;
  return <section><h3 className="text-sm font-semibold text-ink-800">Safety guarantees</h3><div className="mt-2 grid grid-cols-2 gap-2 text-xs md:grid-cols-4">{items.map(([ok, text]) => <div key={text} className={`flex items-center gap-1.5 rounded border px-2 py-1.5 ${ok ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-rose-200 bg-rose-50 text-rose-700"}`}>{ok ? <Check className="h-3.5 w-3.5" /> : <TriangleAlert className="h-3.5 w-3.5" />}{text}</div>)}</div></section>;
}
