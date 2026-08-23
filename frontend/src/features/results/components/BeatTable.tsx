import React, { useState } from "react";
import type { AnalysisResult } from "../../../types";
import { Badge, Card } from "../../../components/ui";

export function BeatTable({ result }: { result: AnalysisResult }) {
  const [filter, setFilter] = useState<"all" | "downbeats">("all");
  const downSet = new Set(result.downbeats.map((d) => d.toFixed(4)));
  const rows = result.beats
    .map((t, i) => ({
      t,
      number: result.beat_numbers[i] ?? i + 1,
      isDown: downSet.has(t.toFixed(4)),
    }))
    .filter((r) => (filter === "downbeats" ? r.isDown : true));
  return (
    <Card
      title="Beats"
      subtitle={`${rows.length} of ${result.beats.length} shown`}
      actions={
        <div className="flex gap-1 text-xs">
          <button
            onClick={() => setFilter("all")}
            className={`rounded px-2 py-1 ${
              filter === "all"
                ? "bg-brand-600 text-white"
                : "bg-ink-100 text-ink-600"
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter("downbeats")}
            className={`rounded px-2 py-1 ${
              filter === "downbeats"
                ? "bg-brand-600 text-white"
                : "bg-ink-100 text-ink-600"
            }`}
          >
            Downbeats
          </button>
        </div>
      }
    >
      <div className="max-h-96 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-white text-left text-xs uppercase tracking-wider text-ink-500">
            <tr>
              <th className="py-2">#</th>
              <th className="py-2">Time (s)</th>
              <th className="py-2">Beat #</th>
              <th className="py-2 text-right">Type</th>
            </tr>
          </thead>
          <tbody className="font-mono text-xs">
            {rows.map((r, i) => (
              <tr key={i} className="border-t border-ink-100">
                <td className="py-1 text-ink-400">{i + 1}</td>
                <td className="py-1">{r.t.toFixed(6)}</td>
                <td className="py-1">{r.number}</td>
                <td className="py-1 text-right">
                  {r.isDown ? (
                    <Badge tone="info">downbeat</Badge>
                  ) : (
                    <span className="text-ink-300">·</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
