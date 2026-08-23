import React from "react";
import type { AnalysisRequest, EngineSpec, ModelInfo } from "../types";
import { Badge, HelpTooltip, Switch } from "./ui";

function Toggle({
  checked,
  onChange,
  label,
  help,
  disabled,
  warning,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  help?: string;
  disabled?: boolean;
  warning?: string;
}) {
  return (
    <label className="flex items-start justify-between gap-4 py-2">
      <div>
        <div className="text-sm font-medium text-ink-800">{label}</div>
        {help && <div className="text-xs text-ink-500">{help}</div>}
        {warning && (
          <div className="mt-1 text-xs text-amber-600">{warning}</div>
        )}
      </div>
      <Switch checked={checked} disabled={disabled} onCheckedChange={onChange} aria-label={label} />
    </label>
  );
}

export function ConfigurationPanel({
  config,
  models,
  spec,
  onChange,
  disabled,
}: {
  config: AnalysisRequest;
  models: ModelInfo[];
  spec: EngineSpec | null;
  onChange: (patch: Partial<AnalysisRequest>) => void;
  disabled?: boolean;
}) {
  return (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-ink-800">
          Model checkpoint
        </label>
        <select
          className="w-full rounded-md border border-ink-200 bg-white px-3 py-2 text-sm text-ink-800 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          value={config.checkpoint}
          disabled={disabled}
          onChange={(e) => onChange({ checkpoint: e.target.value })}
        >
          {spec?.known_checkpoints.map((c) => (
            <option key={c.name} value={c.name}>
              {c.display_name} ({c.name}) — ~{c.approx_size_mb} MB
            </option>
          ))}
        </select>
        {models.find((m) => m.checkpoint === config.checkpoint) && (
          <ModelStatus
            model={models.find((m) => m.checkpoint === config.checkpoint)!}
          />
        )}
      </div>

      <div>
        <div className="mb-1 flex items-center gap-2">
          <label className="block text-sm font-medium text-ink-800">
            Rhythm interpretation
          </label>
          <HelpTooltip content="Observe-only explains every proposal without changing output. Conservative apply may reinterpret existing beat roles after strict safety checks." label="Explain rhythm interpretation modes" />
        </div>
        <select
          className="w-full rounded-md border border-ink-200 bg-white px-3 py-2 text-sm text-ink-800"
          value={config.rhythm_interpretation_mode}
          disabled={disabled}
          onChange={(event) => onChange({ rhythm_interpretation_mode: event.target.value as AnalysisRequest["rhythm_interpretation_mode"] })}
        >
          <option value="off">Off — raw output only</option>
          <option value="observe_only">Observe only — explain, never change</option>
          <option value="conservative_apply">Conservative apply — audited changes</option>
        </select>
        <p className="mt-1 text-xs text-ink-500">
          Raw evidence is always preserved. V1 cannot move, insert, or delete beats.
        </p>
      </div>

      <div className="divide-y divide-ink-100 rounded-md border border-ink-200 px-3">
        <Toggle
          label="DBN post-processing"
          help="Uses madmom DBN (HMM). Default is the paper's minimal peak picker."
          checked={config.dbn}
          disabled={disabled}
          onChange={(v) => onChange({ dbn: v })}
          warning={
            config.dbn
              ? "Requires the CPJKU madmom fork installed on the backend."
              : undefined
          }
        />
        <Toggle
          label="Float16 autocast"
          help="Half precision. Benefit on CPU is typically minimal."
          checked={config.float16}
          disabled={disabled}
          onChange={(v) => onChange({ float16: v })}
        />
        <Toggle
          label="Include frame activations"
          help="Exports per-frame logits (.npy). Can be large."
          checked={config.want_activations}
          disabled={disabled}
          onChange={(v) => onChange({ want_activations: v })}
        />
        <Toggle
          label=".beats TSV file"
          help="Downloadable tab-separated beat times + numbers."
          checked={config.want_beats_file}
          disabled={disabled}
          onChange={(v) => onChange({ want_beats_file: v })}
        />
      </div>

      <div className="rounded-md bg-ink-50 px-3 py-2 text-[11px] leading-relaxed text-ink-500">
        <div className="mb-1 font-medium text-ink-600">
          Fixed model parameters (internal)
        </div>
        sr={spec?.sample_rate} · hop={spec?.hop_length} · n_fft=
        {spec?.n_fft} · n_mels={spec?.n_mels} · fps={spec?.fps} · chunk=
        {spec?.chunk_size} frames
        <div className="mt-0.5">
          These are locked because the published weights require these
          exact features.
        </div>
      </div>
    </div>
  );
}

function ModelStatus({ model }: { model: ModelInfo }) {
  const statusTone =
    model.engine_status === "ready"
      ? "good"
      : model.weights_available
      ? "info"
      : "warn";
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
      <Badge tone={statusTone as "good" | "info" | "warn"}>
        engine: {model.engine_status}
      </Badge>
      <Badge tone={model.beat_this_installed ? "good" : "warn"}>
        beat-this: {model.beat_this_installed ? "installed" : "missing"}
      </Badge>
      <Badge tone={model.weights_available ? "good" : "warn"}>
        weights: {model.weights_source}
      </Badge>
      {model.load_error && (
        <span className="text-rose-600">{model.load_error}</span>
      )}
    </div>
  );
}
