"""Domain objects for the Beat Analysis Engine.

These types form the stable internal representation that flows through
the pipeline.  The API serialisation layer (schemas) maps these to/from
JSON, and the frontend consumes only the serialised form.

The distinction between *native*, *derived*, and *estimated* quantities
is preserved explicitly:

* ``native``    — produced directly by the beat engine (beat times).
* ``derived``   — computed deterministically from native output (tempo).
* ``estimated`` — a heuristic / wrapper-level approximation.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal


# --------------------------------------------------------------------------- #
# Audio
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AudioInput:
    """A reference to an audio file on disk plus basic metadata.

    The engine never trusts a user-supplied filename; the path is a
    server-controlled temp file produced by the storage layer.
    """

    path: Path
    original_filename: str
    size_bytes: int
    content_type: str | None = None


@dataclass(frozen=True)
class AudioProbe:
    """Metadata probed from an audio file without full decoding."""

    duration_sec: float
    sample_rate: int
    channels: int
    format: str | None = None
    codec: str | None = None
    bit_rate: int | None = None


@dataclass
class AudioData:
    """Decoded mono audio at the engine's target sample rate.

    ``signal`` is a 1-D float32 numpy array (mono mixdown).
    ``original_sr`` and ``channels`` preserve the source characteristics
    for reporting.
    """

    signal: Any  # numpy.ndarray, float32, 1-D
    sample_rate: int
    original_sr: int
    channels: int
    duration_sec: float
    resampled: bool = False


# --------------------------------------------------------------------------- #
# Features
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Spectrogram:
    """Log-mel spectrogram matching Beat This! expectations.

    Shape: ``(T, 128)`` where ``T`` is the number of frames at 50 fps.
    """

    data: Any  # numpy.ndarray, shape (T, 128), float32
    sample_rate: int
    hop_length: int
    n_mels: int

    @property
    def fps(self) -> float:
        return self.sample_rate / self.hop_length

    @property
    def n_frames(self) -> int:
        return int(self.data.shape[0])


# --------------------------------------------------------------------------- #
# Engine output
# --------------------------------------------------------------------------- #


@dataclass
class BeatEngineRawResult:
    """Raw output from a :class:`BeatEngine`.

    Times are in seconds and monotonically non-decreasing.  The engine
    is responsible for returning beats and downbeats; optional logits
    are per-frame floats at 50 fps.
    """

    beats: Any  # numpy.ndarray float64
    downbeats: Any  # numpy.ndarray float64
    beat_logits: Any | None = None
    downbeat_logits: Any | None = None
    fps: float = 50.0
    postprocessor: str = "minimal"
    engine_name: str = "unknown"
    checkpoint: str = "unknown"


# --------------------------------------------------------------------------- #
# Tempo / rhythm (derived)
# --------------------------------------------------------------------------- #


class ValueOrigin(str, Enum):
    NATIVE = "native"
    DERIVED = "derived"
    ESTIMATED = "estimated"


@dataclass(frozen=True)
class TempoEstimate:
    bpm: float | None
    origin: ValueOrigin
    method: str
    median_ibi_sec: float | None
    min_bpm: float | None = None
    max_bpm: float | None = None
    raw_bpms: tuple[float, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RhythmInfo:
    """Currently-computed rhythmic descriptors.

    Time signature / bar-position / tempo-change detection are future
    capabilities; they are intentionally not fabricated here.
    """

    beat_density_beats_per_second: float | None = None
    mean_inter_beat_interval_sec: float | None = None
    std_inter_beat_interval_sec: float | None = None
    irregularity: float | None = None


# --------------------------------------------------------------------------- #
# Final result
# --------------------------------------------------------------------------- #


@dataclass
class BeatAnalysisResult:
    """The canonical result object flowing through the engine."""

    audio: AudioProbe
    engine: dict[str, Any]
    config: dict[str, Any]
    beats: list[float]
    downbeats: list[float]
    beat_numbers: list[int]
    tempo: TempoEstimate
    rhythm: RhythmInfo
    timing: dict[str, float]
    validation: dict[str, Any]
    artifacts: dict[str, str] = field(default_factory=dict)
    fps: float = 50.0
    schema_version: str = "1.0"
    counts: dict[str, int] = field(default_factory=dict)
    activations: dict[str, Any] | None = None

    def to_public_dict(self) -> dict[str, Any]:
        """Serialisable representation matching the public JSON schema."""
        return {
            "schema_version": self.schema_version,
            "audio": {
                "duration_sec": round(self.audio.duration_sec, 6),
                "original_sr": self.audio.sample_rate,
                "channels": self.audio.channels,
                "processed_sr": 22050,
                "format": self.audio.format,
                "codec": self.audio.codec,
            },
            "engine": self.engine,
            "config": self.config,
            "fps": self.fps,
            "beats": [round(t, 6) for t in self.beats],
            "downbeats": [round(t, 6) for t in self.downbeats],
            "beat_numbers": self.beat_numbers,
            "tempo": {
                "bpm": round(self.tempo.bpm, 3) if self.tempo.bpm is not None else None,
                "origin": self.tempo.origin.value,
                "method": self.tempo.method,
                "median_ibi_sec": (
                    round(self.tempo.median_ibi_sec, 6)
                    if self.tempo.median_ibi_sec is not None
                    else None
                ),
                "min_bpm": self.tempo.min_bpm,
                "max_bpm": self.tempo.max_bpm,
            },
            "rhythm": {
                "beat_density_beats_per_second": (
                    round(self.rhythm.beat_density_beats_per_second, 6)
                    if self.rhythm.beat_density_beats_per_second is not None
                    else None
                ),
                "mean_ibi_sec": (
                    round(self.rhythm.mean_inter_beat_interval_sec, 6)
                    if self.rhythm.mean_inter_beat_interval_sec is not None
                    else None
                ),
                "std_ibi_sec": (
                    round(self.rhythm.std_inter_beat_interval_sec, 6)
                    if self.rhythm.std_inter_beat_interval_sec is not None
                    else None
                ),
                "irregularity": self.rhythm.irregularity,
            },
            "counts": {
                "beats": len(self.beats),
                "downbeats": len(self.downbeats),
            },
            "timing_ms": {k: round(v * 1000, 3) for k, v in self.timing.items()},
            "validation": self.validation,
            "artifacts": self.artifacts,
        }


# --------------------------------------------------------------------------- #
# Validation report
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ValidationIssue:
    level: Literal["info", "warning", "error"]
    code: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    issues: tuple[ValidationIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "issues": [
                {"level": i.level, "code": i.code, "message": i.message}
                for i in self.issues
            ],
        }


# --------------------------------------------------------------------------- #
# Jobs
# --------------------------------------------------------------------------- #


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state: JobState = JobState.QUEUED
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    config: dict[str, Any] = field(default_factory=dict)
    input: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    cancel_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "state": self.state.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "config": self.config,
            "input": self.input,
            "result": self.result,
            "error": self.error,
        }
