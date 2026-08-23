export type JobState =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export interface ModelInfo {
  checkpoint: string;
  display_name: string;
  description: string | null;
  approx_size_mb: number | null;
  is_small: boolean;
  transformer_dim: number | null;
  engine_status: string;
  weights_available: boolean;
  weights_source: string;
  local_path: string | null;
  device: string;
  beat_this_installed: boolean;
  import_error: string | null;
  load_error: string | null;
}

export interface Health {
  status: string;
  version: string;
  device: string;
  cpu_only: boolean;
  audio_backends: string[];
  beat_this_installed: boolean;
  models: ModelInfo[];
  uptime_sec: number;
}

export interface EngineSpec {
  sample_rate: number;
  hop_length: number;
  n_fft: number;
  n_mels: number;
  f_min: number;
  f_max: number;
  fps: number;
  chunk_size: number;
  border_size: number;
  known_checkpoints: {
    name: string;
    display_name: string;
    description: string;
    approx_size_mb: number;
    is_small: boolean;
  }[];
}

export interface AnalysisRequest {
  checkpoint: string;
  dbn: boolean;
  float16: boolean;
  want_beats_file: boolean;
  want_json: boolean;
  want_activations: boolean;
  rhythm_interpretation_mode: "off" | "observe_only" | "conservative_apply";
}

export interface AnalysisEvent {
  job_id: string;
  stage: string;
  status: string;
  timestamp: number;
  message: string;
  progress: number | null;
  elapsed_ms: number | null;
  metadata: Record<string, unknown>;
}

export interface ValidationIssue {
  level: "info" | "warning" | "error";
  code: string;
  message: string;
}

export interface Tempo {
  bpm: number | null;
  origin: string;
  method: string;
  median_ibi_sec: number | null;
  min_bpm: number | null;
  max_bpm: number | null;
}

export interface Rhythm {
  beat_density_beats_per_second: number | null;
  mean_ibi_sec: number | null;
  std_ibi_sec: number | null;
  irregularity: number | null;
}

export interface AudioMeta {
  duration_sec: number;
  original_sr: number;
  channels: number;
  processed_sr: number;
  format: string | null;
  codec: string | null;
}

export interface RhythmDecision {
  decision_id: string;
  actor: { type: string; name: string; version: string | null };
  rule: { id: string; version: string };
  action: "apply" | "suggest" | "abstain" | "reject_issue";
  target_event_ids: string[];
  decision_confidence: number;
  thresholds: Record<string, number>;
  reason_codes: string[];
  evidence_for: { type: string; value: unknown; description: string }[];
  evidence_against: { type: string; value: unknown; description: string }[];
  alternatives: { hypothesis: string; score: number }[];
  mutation_applied: boolean;
}

export interface RhythmInterpretation {
  schema_version: string;
  mode: "off" | "observe_only" | "conservative_apply";
  ruleset: { id: string; version: string; configuration: unknown } | null;
  guarantees: {
    raw_immutable: boolean;
    timestamps_changed: boolean;
    beats_inserted: number;
    beats_deleted: number;
  };
  tracking: {
    regions: {
      region_id: string;
      start_sec: number;
      end_sec: number;
      status: "tracked" | "uncertain" | "untracked";
      status_confidence: number;
      reason_codes: string[];
    }[];
  };
  issues: { issue_id: string; type: string; detection_confidence: number }[];
  decisions: RhythmDecision[];
  summary: {
    tracking_ratio?: Record<string, number>;
    issues?: number;
    actions?: Record<string, number>;
    changed_roles: number;
    structural_effect?: { before: number | null; after: number | null; improved: boolean };
  };
  correctness_verdict: string;
}

export interface AnalysisResult {
  schema_version: string;
  audio: AudioMeta;
  engine: Record<string, unknown>;
  config: Record<string, unknown>;
  fps: number;
  beats: number[];
  downbeats: number[];
  beat_numbers: number[];
  tempo: Tempo;
  rhythm: Rhythm;
  rhythm_interpretation?: RhythmInterpretation | null;
  counts: { beats: number; downbeats: number };
  timing_ms: Record<string, number>;
  validation: { ok: boolean; issues: ValidationIssue[] };
  artifacts: Record<string, string>;
}

export interface ErrorBody {
  code: string;
  stage: string;
  message: string;
  technical_detail: string;
  recoverable: boolean;
}

export interface Job {
  id: string;
  state: JobState;
  created_at: number;
  started_at: number | null;
  finished_at: number | null;
  config: Record<string, unknown>;
  input: unknown;
  result: AnalysisResult | null;
  error: ErrorBody | null;
}
