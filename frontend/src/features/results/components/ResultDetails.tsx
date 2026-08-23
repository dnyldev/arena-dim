import React from "react";
import type { AnalysisResult, Job } from "../../../types";
import { api } from "../../../api/client";
import { Badge, Card } from "../../../components/ui";

function fmtMs(v: number | undefined): string { return v == null ? "—" : `${v.toFixed(0)} ms`; }

export function TimingCard({ result }: { result: AnalysisResult }) {
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

export function DownloadsCard({
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

export function ValidationCard({ result }: { result: AnalysisResult }) {
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
