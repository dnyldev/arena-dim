import React, { useState } from "react";
import { Check, Circle, CircleX, LoaderCircle, SkipForward } from "lucide-react";
import type { AnalysisEvent } from "../types";
import { Badge, Button, Card } from "./ui";

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
  const [showTechnical, setShowTechnical] = useState(false);
  const completed = STAGE_ORDER.filter((stage) => stageStatus(stage, events) === "completed").length;
  const overallPct = phase === "completed" ? 100 : Math.round((completed / STAGE_ORDER.length) * 100);
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
      <div className="flex items-center gap-3">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-100"><div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${overallPct}%` }} /></div>
        <span className="w-10 text-right font-mono text-xs text-ink-500">{overallPct}%</span>
        <Button variant="ghost" size="sm" onClick={() => setShowTechnical((value) => !value)}>{showTechnical ? "Hide details" : "Technical details"}</Button>
      </div>
      {showTechnical && <div className="mt-4 grid grid-cols-1 gap-3 border-t border-ink-100 pt-4 md:grid-cols-2">
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-500">
            Stages
          </div>
          <ol className="space-y-1.5">
            {STAGE_ORDER.map((s) => {
              const st = stageStatus(s, events);
              const icon = st === "completed" ? <Check className="h-3.5 w-3.5" /> : st === "running" ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : st === "failed" ? <CircleX className="h-3.5 w-3.5" /> : st === "skipped" ? <SkipForward className="h-3.5 w-3.5" /> : <Circle className="h-3.5 w-3.5" />;
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
      </div>}
    </Card>
  );
}
