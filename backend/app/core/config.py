"""Centralised configuration.

The configuration is split into two tiers:

* **Public parameters** — values the dashboard user is allowed to change
  per analysis (checkpoint choice, DBN toggle, float16, output options).
* **Internal / fixed parameters** — values the model requires for
  correctness (sample rate, mel parameters, hop length, chunking).
  These are constants and are **never** exposed to the user.

The fixed spectrogram / chunking constants come verbatim from the
Beat This! source (see Technical Research Package §2, §5):

    sample_rate = 22050
    n_fft       = 1024
    hop_length  = 441        → fps = 22050/441 = 50
    n_mels      = 128
    f_min       = 30
    f_max       = 11000
    log_multiplier = 1000
    chunk_size  = 1500 frames (30 s)
    border_size = 6 frames
    peak_pool_kernel = 7

Changing any of these would produce features that do not match the
published weights, so they are deliberately hard-coded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from app.core.errors import ConfigurationError


# --------------------------------------------------------------------------- #
# Fixed Beat This! constants (INTERNAL — not user configurable)
# --------------------------------------------------------------------------- #


class BeatThisSpec:
    """Fixed constants dictated by the Beat This! model weights."""

    # Audio / mel
    SAMPLE_RATE: int = 22050
    N_FFT: int = 1024
    HOP_LENGTH: int = 441
    N_MELS: int = 128
    F_MIN: int = 30
    F_MAX: int = 11000
    LOG_MULTIPLIER: int = 1000
    POWER: float = 1.0
    MEL_SCALE: str = "slaney"
    MEL_NORM: str = "frame_length"

    # Inference chunking
    CHUNK_SIZE: int = 1500      # 30 s at 50 fps
    BORDER_SIZE: int = 6        # frames discarded on each side
    OVERLAP_MODE: str = "keep_first"

    # Postprocessing (minimal peak picker)
    PEAK_POOL_KERNEL: int = 7
    PEAK_THRESHOLD_LOGIT: float = 0.0  # logit > 0 ↔ probability > 0.5

    # DBN (only used when dbn=True)
    DBN_BEATS_PER_BAR: tuple[int, ...] = (3, 4)
    DBN_MIN_BPM: float = 55.0
    DBN_MAX_BPM: float = 215.0
    DBN_TRANSITION_LAMBDA: float = 100.0

    @classmethod
    def fps(cls) -> float:
        """Frames per second = sample_rate / hop_length (exactly 50)."""
        return cls.SAMPLE_RATE / cls.HOP_LENGTH

    @classmethod
    def seconds_to_frame(cls, seconds: float) -> int:
        """Convert seconds to a frame index (nearest, non-negative)."""
        return max(0, round(seconds * cls.fps()))

    @classmethod
    def frame_to_seconds(cls, frame: int) -> float:
        """Convert a frame index to seconds."""
        return frame / cls.fps()


# --------------------------------------------------------------------------- #
# Known checkpoints
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CheckpointInfo:
    name: str
    display_name: str
    description: str
    approx_size_mb: float
    transformer_dim: int
    is_small: bool = False


KNOWN_CHECKPOINTS: dict[str, CheckpointInfo] = {
    "final0": CheckpointInfo(
        "final0", "Final 0", "Full model — primary release checkpoint", 78.0, 512
    ),
    "final1": CheckpointInfo(
        "final1", "Final 1", "Full model — second fold", 78.0, 512
    ),
    "final2": CheckpointInfo(
        "final2", "Final 2", "Full model — third fold", 78.0, 512
    ),
    "small0": CheckpointInfo(
        "small0", "Small 0", "Lightweight model — faster on CPU", 8.1, 128, is_small=True
    ),
    "small1": CheckpointInfo(
        "small1", "Small 1", "Lightweight model — second fold", 8.1, 128, is_small=True
    ),
    "small2": CheckpointInfo(
        "small2", "Small 2", "Lightweight model — third fold", 8.1, 128, is_small=True
    ),
}

DEFAULT_CHECKPOINT = "final0"


# --------------------------------------------------------------------------- #
# Runtime / server configuration (environment-driven)
# --------------------------------------------------------------------------- #


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    val = os.environ.get(name)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ConfigurationError(
            f"Environment variable {name} must be an integer, got {val!r}",
            technical_detail=str(exc),
        )


@dataclass(frozen=True)
class RuntimeConfig:
    """Server / runtime settings sourced from environment variables."""

    host: str = field(default_factory=lambda: os.environ.get("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: _env_int("PORT", 8000))
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip()
            for o in os.environ.get("CORS_ORIGINS", "*").split(",")
            if o.strip()
        )
    )

    # CPU is the only execution target — no CUDA, no GPU auto-detection.
    device: str = "cpu"

    # Storage
    data_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("DATA_DIR", "./data")).resolve()
    )
    upload_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("UPLOAD_DIR", "./data/uploads")
        ).resolve()
    )
    artifact_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("ARTIFACT_DIR", "./data/artifacts")
        ).resolve()
    )
    checkpoint_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("CHECKPOINT_DIR", "./data/checkpoints")
        ).resolve()
    )

    # Limits
    max_upload_mb: int = field(default_factory=lambda: _env_int("MAX_UPLOAD_MB", 500))
    min_audio_seconds: float = field(
        default_factory=lambda: float(os.environ.get("MIN_AUDIO_SECONDS", "0.5"))
    )
    max_audio_seconds: float = field(
        default_factory=lambda: float(os.environ.get("MAX_AUDIO_SECONDS", "1800"))
    )

    # Concurrency — CPU inference is heavy; one analysis at a time by default.
    max_concurrent_analyses: int = field(
        default_factory=lambda: _env_int("MAX_CONCURRENT_ANALYSES", 1)
    )
    job_queue_max: int = field(
        default_factory=lambda: _env_int("JOB_QUEUE_MAX", 4)
    )
    job_ttl_seconds: int = field(
        default_factory=lambda: _env_int("JOB_TTL_SECONDS", 3600)
    )

    # Model download base URL (Beat This! official cloud)
    checkpoint_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "CHECKPOINT_BASE_URL",
            "https://cloud.cp.jku.at/public.php/dav/files/7ik4RrBKTS273gp",
        )
    )

    # Whether to allow the engine to attempt auto-download.
    allow_model_download: bool = field(
        default_factory=lambda: _env_bool("ALLOW_MODEL_DOWNLOAD", True)
    )

    # CORS-friendly
    allow_credentials: bool = True

    def ensure_dirs(self) -> None:
        for d in (
            self.data_dir,
            self.upload_dir,
            self.artifact_dir,
            self.checkpoint_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Per-analysis request configuration (PUBLIC parameters)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AnalysisConfig:
    """User-facing analysis parameters.

    Only these fields may be set by a dashboard user.  The internal
    mel/chunk/peak constants live in :class:`BeatThisSpec` and are
    deliberately absent here.
    """

    checkpoint: str = DEFAULT_CHECKPOINT
    dbn: bool = False
    float16: bool = False
    # Output options
    want_beats_file: bool = True
    want_json: bool = True
    want_activations: bool = False
    # Auditable rhythm interpretation. Observe-only never mutates output.
    rhythm_interpretation_mode: str = "observe_only"

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.checkpoint, str) or not self.checkpoint.strip():
            raise ConfigurationError(
                "Checkpoint name must be a non-empty string.",
                technical_detail=f"checkpoint={self.checkpoint!r}",
            )
        if not isinstance(self.dbn, bool):
            raise ConfigurationError("'dbn' must be a boolean.")
        if not isinstance(self.float16, bool):
            raise ConfigurationError("'float16' must be a boolean.")
        if not isinstance(self.want_activations, bool):
            raise ConfigurationError("'want_activations' must be a boolean.")
        if self.rhythm_interpretation_mode not in {
            "off", "observe_only", "conservative_apply"
        }:
            raise ConfigurationError(
                "'rhythm_interpretation_mode' must be off, observe_only, or conservative_apply."
            )

    def with_overrides(self, **overrides: Any) -> "AnalysisConfig":
        data = asdict(self)
        data.update(overrides)
        return AnalysisConfig(**data)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AnalysisConfig":
        if data is None:
            return cls()
        allowed = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - allowed
        if unknown:
            from app.core.errors import UnsupportedParameterError

            raise UnsupportedParameterError(
                f"Unsupported parameter(s): {', '.join(sorted(unknown))}",
                technical_detail=f"allowed={sorted(allowed)}",
            )
        return cls(**data)

    def is_known_checkpoint(self) -> bool:
        return self.checkpoint in KNOWN_CHECKPOINTS

    def checkpoint_info(self) -> CheckpointInfo | None:
        return KNOWN_CHECKPOINTS.get(self.checkpoint)


# Module-level singleton — populated at application startup.
_runtime: RuntimeConfig | None = None


def get_runtime() -> RuntimeConfig:
    global _runtime
    if _runtime is None:
        _runtime = RuntimeConfig()
    return _runtime


def set_runtime(rt: RuntimeConfig) -> None:
    """Test helper / explicit initialiser."""
    global _runtime
    _runtime = rt
