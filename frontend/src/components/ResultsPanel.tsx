import React, { useState } from "react";
import type { AnalysisResult, Job } from "../types";
import { api } from "../api/client";
import { Badge, Card, Stat } from "./Card";
import { BeatTimeline } from "./BeatTimeline";
import { TempoCurveChart } from "./TempoCurveChart";

function fmtBpm(bpm: number | null): string {
  return bpm == null ? "—" : `${bpm.toFixed(2)} BPM`;
}

function fmtMs(v: number | undefined): string {
  return v == null ? "—" : `${v.toFixed(0)} ms`;
}

export function ResultsPanel({ job }: { job: Job }) {
  const result = job.result;
  if (!result) return null;

  return (
    <div className="space-y-4">
      <SummaryCards result={result} />
      <Card title="Timeline" subtitle="Beat positions across the audio (D = downbeat)">
        <BeatTimeline result={result} />
      </Card>
      <Card
        title="Tempo curve"
        subtitle="Local BPM over time (sliding window over consecutive beats) — derived, not a native model output"
      >
        <TempoCurveChart
          curve={result.tempo.curve}
          overallBpm={result.tempo.bpm}
          windowBeats={result.tempo.curve_window_beats}
          durationSec={result.audio.duration_sec}
        />
      </Card>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <BeatTable result={result} />
        </div>
        <div className="space-y-4">
          <TimingCard result={result} />
          <DownloadsCard job={job} result={result} />
          <ValidationCard result={result} />
        </div>
      </div>
    </div>
  );
}

function fmtMeter(beatsPerBar: number | null): string {
  // Only the beat count per bar is estimated (from downbeat spacing);
  // the note-value denominator (the "/4" in "4/4") is not observable
  // from beat times alone, so it is intentionally not implied here.
  return beatsPerBar == null ? "—" : `${beatsPerBar} beats/bar`;
}

function SummaryCards({ result }: { result: AnalysisResult }) {
  const meter = result.meter;
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
      <Stat
        label="Estimated tempo"
        value={fmtBpm(result.tempo.bpm)}
        hint={`${result.tempo.origin} · ${result.tempo.method}`}
        tone="good"
      />
      <Stat
        label="Time signature"
        value={fmtMeter(meter.beats_per_bar)}
        hint={
          meter.beats_per_bar == null
            ? "insufficient downbeats"
            : `${meter.origin}${
                meter.confidence != null
                  ? ` · ${(meter.confidence * 100).toFixed(0)}% of bars`
                  : ""
              }${meter.is_stable === false ? " · varies" : ""}`
        }
        tone={
          meter.beats_per_bar == null
            ? "default"
            : meter.is_stable
            ? "good"
            : "warn"
        }
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

function BeatTable({ result }: { result: AnalysisResult }) {
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

function TimingCard({ result }: { result: AnalysisResult }) {
  const t = result.timing_ms;
  const items: [string, number | undefined][] = [
    ["probe", t.probe],
    ["audio prepare", t.audio_prepare],
    ["spectrogram", t.spectrogram],
    ["model + inference", t.model_load_and_inference],
    ["postprocess", t.postprocess],
    ["validation", t.validation],
    ["tempo / rhythm", (t.tempo ?? 0) + (t.rhythm ?? 0)],
    ["artifacts", t.artifacts],
    ["total", t.total],
  ];
  const max = Math.max(...items.map(([, v]) => v ?? 0), 1);
  return (
    <Card title="Timing" subtitle="Per-stage wall clock (ms)">
      <ul className="space-y-1.5 text-xs">
        {items.map(([label, v]) => (
          <li key={label}>
            <div className="flex justify-between text-ink-600">
              <span>{label}</span>
              <span className="font-mono">{fmtMs(v)}</span>
            </div>
            <div className="mt-0.5 h-1 rounded bg-ink-100">
              <div
                className={`h-1 rounded ${
                  label === "total" ? "bg-brand-600" : "bg-brand-400"
                }`}
                style={{ width: `${((v ?? 0) / max) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function DownloadsCard({
  job,
  result,
}: {
  job: Job;
  result: AnalysisResult;
}) {
  const links: [string, string, string][] = [
    ["json", "result.json", "application/json"],
    ["beats", "beats.tsv", "text/tab-separated-values"],
    ["activations", "activations.npy", "application/octet-stream"],
    ["meta", "meta.json", "application/json"],
  ];
  return (
    <Card title="Artifacts" subtitle="Download analysis outputs">
      <ul className="space-y-2 text-sm">
        {links
          .filter(([key]) => result.artifacts[key])
          .map(([key, label]) => (
            <li key={key}>
              <a
                href={api.artifactUrl(job.id, key)}
                className="flex items-center justify-between rounded-md border border-ink-200 bg-white px-3 py-2 text-brand-700 hover:bg-brand-50"
                download
              >
                <span>{label}</span>
                <span aria-hidden>↓</span>
              </a>
            </li>
          ))}
        {Object.keys(result.artifacts).length === 0 && (
          <li className="text-ink-400">No artifacts.</li>
        )}
      </ul>
    </Card>
  );
}

function ValidationCard({ result }: { result: AnalysisResult }) {
  const v = result.validation;
  return (
    <Card title="Validation">
      <div className="flex items-center gap-2">
        <Badge tone={v.ok ? "good" : "bad"}>{v.ok ? "passed" : "failed"}</Badge>
        <span className="text-xs text-ink-500">
          {v.issues.length} issue(s)
        </span>
      </div>
      {v.issues.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs text-ink-600">
          {v.issues.map((iss, i) => (
            <li
              key={i}
              className={
                iss.level === "error"
                  ? "text-rose-600"
                  : iss.level === "warning"
                  ? "text-amber-600"
                  : "text-ink-500"
              }
            >
              · {iss.message}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
