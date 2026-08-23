import React from "react";
import type { AnalysisResult } from "../../../types";
import { Stat } from "../../../components/ui";

function fmtBpm(bpm: number | null): string { return bpm == null ? "—" : `${bpm.toFixed(2)} BPM`; }

export function SummaryCards({ result }: { result: AnalysisResult }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <Stat
        label="Estimated tempo"
        value={fmtBpm(result.tempo.bpm)}
        hint={`${result.tempo.origin} · ${result.tempo.method}`}
        tone="good"
      />
      <Stat
        label="Beats"
        value={result.counts.beats}
        hint={`${result.fps} fps`}
      />
      <Stat
        label="Downbeats"
        value={result.counts.downbeats}
        hint={
          result.counts.beats > 0
            ? `1 in ${(result.counts.beats / Math.max(1, result.counts.downbeats)).toFixed(1)}`
            : undefined
        }
        tone="default"
      />
      <Stat
        label="Beat density"
        value={
          result.rhythm.beat_density_beats_per_second
            ? `${result.rhythm.beat_density_beats_per_second.toFixed(2)}/s`
            : "—"
        }
        hint={`mean IBI ${
          result.rhythm.mean_ibi_sec
            ? (result.rhythm.mean_ibi_sec * 1000).toFixed(0) + " ms"
            : "—"
        }`}
      />
    </div>
  );
}
