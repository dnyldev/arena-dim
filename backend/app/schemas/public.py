"""Pydantic request/response schemas for the public API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    checkpoint: str = Field(
        default="final0", description="Checkpoint shortname, local path, or URL."
    )
    dbn: bool = Field(default=False, description="Use the optional DBN postprocessor.")
    float16: bool = Field(
        default=False, description="Enable float16 autocast (limited benefit on CPU)."
    )
    want_beats_file: bool = True
    want_json: bool = True
    want_activations: bool = False


class AudioMeta(BaseModel):
    duration_sec: float | None = None
    original_sr: int | None = None
    channels: int | None = None
    processed_sr: int = 22050
    format: str | None = None
    codec: str | None = None


class TempoCurvePointOut(BaseModel):
    time_sec: float
    bpm: float


class TempoOut(BaseModel):
    bpm: float | None = None
    origin: str
    method: str
    median_ibi_sec: float | None = None
    min_bpm: float | None = None
    max_bpm: float | None = None
    curve_window_beats: int | None = None
    curve: list[TempoCurvePointOut] = []


class MeterOut(BaseModel):
    beats_per_bar: int | None = None
    origin: str = "estimated"
    method: str = "downbeat_interval_mode"
    confidence: float | None = None
    per_bar: list[int] = []
    is_stable: bool | None = None


class RhythmOut(BaseModel):
    beat_density_beats_per_second: float | None = None
    mean_ibi_sec: float | None = None
    std_ibi_sec: float | None = None
    irregularity: float | None = None


class ValidationIssueOut(BaseModel):
    level: str
    code: str
    message: str


class ValidationOut(BaseModel):
    ok: bool
    issues: list[ValidationIssueOut] = []


class AnalysisResultOut(BaseModel):
    schema_version: str
    audio: AudioMeta
    engine: dict[str, Any]
    config: dict[str, Any]
    fps: float
    beats: list[float]
    downbeats: list[float]
    beat_numbers: list[int]
    tempo: TempoOut
    rhythm: RhythmOut
    meter: MeterOut
    counts: dict[str, int]
    timing_ms: dict[str, float]
    validation: ValidationOut
    artifacts: dict[str, str] = {}


class ErrorOut(BaseModel):
    error: dict[str, Any]


class ModelInfoOut(BaseModel):
    checkpoint: str
    display_name: str
    description: str | None = None
    approx_size_mb: float | None = None
    is_small: bool = False
    transformer_dim: int | None = None
    engine_status: str
    weights_available: bool
    weights_source: str
    local_path: str | None = None
    device: str
    beat_this_installed: bool
    import_error: str | None = None
    load_error: str | None = None


class HealthOut(BaseModel):
    status: str
    version: str
    device: str
    cpu_only: bool
    audio_backends: list[str]
    beat_this_installed: bool
    models: list[ModelInfoOut]
    uptime_sec: float


class JobOut(BaseModel):
    id: str
    state: str
    created_at: float
    started_at: float | None = None
    finished_at: float | None = None
    config: dict[str, Any]
    input: Any
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class EventOut(BaseModel):
    job_id: str
    stage: str
    status: str
    timestamp: float
    message: str
    progress: float | None = None
    elapsed_ms: float | None = None
    metadata: dict[str, Any] = {}
