import React from "react";
import type { AnalysisEvent } from "../types";
import { Badge, Card } from "./Card";

const STAGE_ORDER = [
  "probe",
  "audio_load",
  "normalize",
  "resample",
  "feature_extraction",
  "model_load",
  "inference",
  "postprocess",
  "validation",
  "tempo",
  "rhythm",
  "artifact",
  "result",
];

function formatTime(ts: number) {
  const d = new Date(ts * 1000);
  return d.toTimeString().slice(0, 8);
}

function stageStatus(stage: string, events: AnalysisEvent[]) {
  const stageEvents = events.filter((e) => e.stage === stage);
  if (stageEvents.some((e) => e.status === "failed")) return "failed";
  if (stageEvents.some((e) => e.status === "completed")) return "completed";
  if (stageEvents.some((e) => e.status === "started")) return "running";
  if (stageEvents.some((e) => e.status === "skipped")) return "skipped";
  return "pending";
}

export function ProcessingPanel({
  events,
  progress,
  phase,
}: {
  events: AnalysisEvent[];
  progress: { stage: string; pct: number | null };
  phase: string;
}) {
  return (
    <Card
      title="Pipeline"
      subtitle="Live stage events from the analysis engine"
      actions={
        phase === "running" || phase === "queued" ? (
          <Badge tone="info">{phase}</Badge>
        ) : null
      }
    >
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-500">
            Stages
          </div>
          <ol className="space-y-1.5">
            {STAGE_ORDER.map((s) => {
              const st = stageStatus(s, events);
              const icon =
                st === "completed"
                  ? "✓"
                  : st === "running"
                  ? "▸"
                  : st === "failed"
                  ? "✕"
                  : st === "skipped"
                  ? "↷"
                  : "○";
              const color =
                st === "completed"
                  ? "text-emerald-600"
                  : st === "running"
                  ? "text-brand-600"
                  : st === "failed"
                  ? "text-rose-600"
                  : "text-ink-400";
              return (
                <li
                  key={s}
                  className="flex items-center gap-2 font-mono text-xs text-ink-700"
                >
                  <span className={`w-4 ${color}`}>{icon}</span>
                  <span className="w-40">{s}</span>
                  {st === "running" && progress.pct != null && (
                    <span className="text-ink-500">
                      {Math.round(progress.pct * 100)}%
                    </span>
                  )}
                </li>
              );
            })}
          </ol>
        </div>

        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-500">
            Event log
          </div>
          <div className="h-64 overflow-y-auto rounded-md border border-ink-100 bg-ink-900 p-3 font-mono text-[11px] leading-relaxed text-ink-100">
            {events.length === 0 && (
              <div className="text-ink-500">Waiting for events…</div>
            )}
            {events.map((e, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-ink-500">[{formatTime(e.timestamp)}]</span>
                <span
                  className={
                    e.status === "failed"
                      ? "text-rose-400"
                      : e.status === "warning"
                      ? "text-amber-300"
                      : e.status === "completed"
                      ? "text-emerald-300"
                      : "text-ink-200"
                  }
                >
                  {e.stage}/{e.status}
                </span>
                <span className="text-ink-300">{e.message}</span>
                {e.elapsed_ms != null && (
                  <span className="ml-auto text-ink-500">
                    {e.elapsed_ms.toFixed(0)}ms
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}
