import React, { useMemo, useState } from "react";
import { AlertCircle } from "lucide-react";
import { Button, Card } from "./components/ui";
import { FilePicker, PickedFile } from "./components/FilePicker";
import { ConfigurationPanel } from "./components/ConfigurationPanel";
import { ProcessingPanel } from "./components/ProcessingPanel";
import { ResultsPanel } from "./components/ResultsPanel";
import { HelpDialog } from "./components/HelpDialog";
import { AppHeader, SystemFooter } from "./components/layout/AppHeader";
import { useConfigurationState } from "./state/useConfigurationState";
import { useHealthState } from "./state/useHealthState";
import { useJobState } from "./state/useJobState";

export function App() {
  const { health, spec, models, error: healthError } = useHealthState();
  const { config, update } = useConfigurationState();
  const { job, events, phase, error, progress, start, reset, cancel } =
    useJobState();
  const [picked, setPicked] = useState<PickedFile | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);

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
    <div className="min-h-screen bg-ink-50/60">
      <AppHeader health={health} onOpenHelp={() => setHelpOpen(true)} />
      <HelpDialog open={helpOpen} onClose={() => setHelpOpen(false)} />

      <main className="mx-auto max-w-[1440px] space-y-6 px-4 py-6 sm:px-6 sm:py-8">
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
                <Button onClick={onAnalyze} disabled={!canAnalyze} loading={isBusy} fullWidth>
                  {isBusy ? "Processing" : "Analyze audio"}
                </Button>
                {isBusy && (
                  <Button onClick={cancel} variant="secondary" fullWidth>Cancel</Button>
                )}
                {(phase === "completed" || phase === "failed") && (
                  <Button onClick={onReset} variant="secondary" fullWidth>New analysis</Button>
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

        <SystemFooter health={health} />
      </main>
    </div>
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
    <div className={`flex items-start gap-2 rounded-md border px-3 py-2 text-xs ${tones[tone]}`}>
      <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
      <div>{children}</div>
    </div>
  );
}
