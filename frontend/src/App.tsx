import React, { useMemo, useState } from "react";
import { Card, Badge } from "./components/Card";
import { FilePicker, PickedFile } from "./components/FilePicker";
import { ConfigurationPanel } from "./components/ConfigurationPanel";
import { ProcessingPanel } from "./components/ProcessingPanel";
import { ResultsPanel } from "./components/ResultsPanel";
import { useConfigurationState } from "./state/useConfigurationState";
import { useHealthState } from "./state/useHealthState";
import { useJobState } from "./state/useJobState";

export function App() {
  const { health, spec, models, error: healthError } = useHealthState();
  const { config, update } = useConfigurationState();
  const { job, events, phase, error, progress, start, reset, cancel } =
    useJobState();
  const [picked, setPicked] = useState<PickedFile | null>(null);

  const isBusy =
    phase === "uploading" || phase === "queued" || phase === "running";

  const canAnalyze =
    !!picked && !isBusy && health?.status === "ok" && (health?.beat_this_installed || false);

  const onAnalyze = () => {
    if (!picked) return;
    start(picked.file, config);
  };

  const onReset = () => {
    reset();
    setPicked(null);
  };

  const modelReady = useMemo(() => {
    const m = models.find((mm) => mm.checkpoint === config.checkpoint);
    return m?.engine_status === "ready" || m?.weights_available;
  }, [models, config.checkpoint]);

  return (
    <div className="min-h-screen">
      <Header health={health} />

      <main className="mx-auto max-w-7xl space-y-6 px-6 py-8">
        {healthError && (
          <Banner tone="bad">
            Cannot reach backend: {healthError}
          </Banner>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-1">
            <Card title="Audio" subtitle="Select a file to analyze">
              <FilePicker onPick={setPicked} disabled={isBusy} />
              {picked && (
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-ink-600">
                  <Meta label="filename" value={picked.file.name} />
                  <Meta
                    label="size"
                    value={`${(picked.file.size / (1024 * 1024)).toFixed(2)} MB`}
                  />
                  <Meta
                    label="duration"
                    value={
                      picked.durationSec != null
                        ? `${picked.durationSec.toFixed(2)} s`
                        : "—"
                    }
                  />
                  <Meta label="type" value={picked.file.type || "—"} />
                </div>
              )}
            </Card>

            <Card title="Engine configuration">
              <ConfigurationPanel
                config={config}
                models={models}
                spec={spec}
                onChange={(patch) =>
                  Object.entries(patch).forEach(([k, v]) =>
                    update(k as keyof typeof config, v as never)
                  )
                }
                disabled={isBusy}
              />
            </Card>

            <Card>
              <div className="flex flex-col gap-3">
                <button
                  onClick={onAnalyze}
                  disabled={!canAnalyze}
                  className="w-full rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-ink-300"
                >
                  {isBusy ? "Processing…" : "Analyze"}
                </button>
                {isBusy && (
                  <button
                    onClick={cancel}
                    className="w-full rounded-lg border border-ink-200 bg-white px-4 py-2 text-sm text-ink-700 hover:bg-ink-50"
                  >
                    Cancel
                  </button>
                )}
                {(phase === "completed" || phase === "failed") && (
                  <button
                    onClick={onReset}
                    className="w-full rounded-lg border border-ink-200 bg-white px-4 py-2 text-sm text-ink-700 hover:bg-ink-50"
                  >
                    New analysis
                  </button>
                )}
                {!health?.beat_this_installed && (
                  <Banner tone="warn">
                    The <code>beat-this</code> package is not installed. Start
                    the backend with it to enable real inference.
                  </Banner>
                )}
                {health?.beat_this_installed &&
                  config.checkpoint &&
                  !modelReady &&
                  !isBusy && (
                    <Banner tone="warn">
                      Weights for <strong>{config.checkpoint}</strong> are not
                      cached locally. They will be downloaded on first
                      analysis.
                    </Banner>
                  )}
                {error && <Banner tone="bad">{error}</Banner>}
              </div>
            </Card>
          </div>

          <div className="space-y-6 lg:col-span-2">
            <ProcessingPanel
              events={events}
              progress={progress}
              phase={phase}
            />
            {job?.result && <ResultsPanel job={job} />}
            {phase === "failed" && !job?.result && (
              <Card title="Analysis failed">
                <p className="text-sm text-rose-600">{error}</p>
                {job?.error?.technical_detail && (
                  <pre className="mt-3 overflow-x-auto rounded bg-ink-50 p-3 text-xs text-ink-600">
                    {job.error.technical_detail}
                  </pre>
                )}
              </Card>
            )}
          </div>
        </div>

        <Footer health={health} />
      </main>
    </div>
  );
}

function Header({ health }: { health: ReturnType<typeof useHealthState>["health"] }) {
  return (
    <header className="border-b border-ink-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-ink-900">
            Beat Analysis Engine
          </h1>
          <p className="text-xs text-ink-500">
            CPU-only operational dashboard · powered by Beat This!
          </p>
        </div>
        <div className="flex items-center gap-3">
          {health && (
            <>
              <Badge tone="good">cpu-only</Badge>
              <Badge tone={health.beat_this_installed ? "good" : "warn"}>
                beat-this: {health.beat_this_installed ? "installed" : "missing"}
              </Badge>
              <Badge tone={health.status === "ok" ? "good" : "bad"}>
                api: {health.status}
              </Badge>
              <span className="text-xs text-ink-400">v{health.version}</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-ink-100 bg-ink-50/40 px-2 py-1.5">
      <div className="text-[10px] uppercase tracking-wider text-ink-400">
        {label}
      </div>
      <div className="truncate text-ink-800" title={value}>
        {value}
      </div>
    </div>
  );
}

function Banner({
  children,
  tone = "info",
}: {
  children: React.ReactNode;
  tone?: "info" | "good" | "warn" | "bad";
}) {
  const tones: Record<string, string> = {
    info: "bg-brand-50 text-brand-700 border-brand-200",
    good: "bg-emerald-50 text-emerald-700 border-emerald-200",
    warn: "bg-amber-50 text-amber-700 border-amber-200",
    bad: "bg-rose-50 text-rose-700 border-rose-200",
  };
  return (
    <div className={`rounded-md border px-3 py-2 text-xs ${tones[tone]}`}>
      {children}
    </div>
  );
}

function Footer({
  health,
}: {
  health: ReturnType<typeof useHealthState>["health"];
}) {
  return (
    <footer className="mt-10 border-t border-ink-200 pt-4 text-xs text-ink-400">
      <div className="flex flex-wrap gap-x-6 gap-y-1">
        <span>audio backends: {health?.audio_backends.join(", ") || "—"}</span>
        <span>device: {health?.device}</span>
        <span>uptime: {health?.uptime_sec.toFixed(0)}s</span>
      </div>
    </footer>
  );
}
