import React from "react";
import type { RhythmInterpretation } from "../../../types";

export function TrackingRegions({ regions }: { regions: RhythmInterpretation["tracking"]["regions"] }) {
  return <section><h3 className="text-sm font-semibold text-ink-800">Tracking regions</h3><div className="mt-2 flex min-h-12 overflow-hidden rounded border border-ink-200">{regions.map((region) => { const width = Math.max(3, region.end_sec-region.start_sec); const color = region.status === "tracked" ? "bg-emerald-100 text-emerald-800" : region.status === "uncertain" ? "bg-amber-100 text-amber-800" : "bg-ink-100 text-ink-600"; return <div key={region.region_id} style={{ flexGrow: width }} title={`${region.start_sec.toFixed(2)}–${region.end_sec.toFixed(2)}s · ${region.reason_codes.join(", ")}`} className={`flex min-w-0 items-center justify-center border-r border-white px-1 text-[10px] ${color}`}>{region.status}</div>; })}</div></section>;
}
