"""Beat engine abstraction.

A :class:`BeatEngine` turns a log-mel spectrogram into per-frame beat
and downbeat **logits**.  It is deliberately narrow:

* It does **not** load audio.
* It does **not** compute spectrograms.
* It does **not** post-process peaks or derive tempo.
* It does **not** know about HTTP, files, or jobs.

This keeps Beat This! replaceable: a future ``AlternativeBeatEngine``,
``EnsembleBeatEngine``, etc. can be plugged in without touching the
API, orchestrator, frontend, result schema, or artifact system.

Concrete engines live under :mod:`app.engines.<name>` and are
constructed via an :class:`EngineFactory`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

import numpy as np


@dataclass(frozen=True)
class EngineCapabilities:
    """What an engine can produce."""

    produces_beats: bool = True
    produces_downbeats: bool = True
    produces_activations: bool = True
    supports_dbn: bool = False  # the Beat This! DBN is in the postprocessor
    supports_half_precision: bool = True
    cpu_only: bool = True


@dataclass(frozen=True)
class EngineFrameOutput:
    """Per-frame logits produced by an engine.

    Arrays have shape ``(T,)`` at the engine's frame rate.
    """

    beat_logits: np.ndarray
    downbeat_logits: np.ndarray
    fps: float
    n_frames: int
    engine_name: str
    checkpoint: str


class EngineStatus(str, Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    IN_USE = "in_use"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"  # dependency missing / cannot even construct


@dataclass(frozen=True)
class EngineInfo:
    name: str
    display_name: str
    version: str
    device: str
    status: EngineStatus
    checkpoint: str
    checkpoint_available: bool
    capabilities: EngineCapabilities
    load_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class BeatEngine(Protocol):
    """The narrow contract every beat engine must satisfy."""

    @property
    def name(self) -> str: ...

    @property
    def info(self) -> EngineInfo: ...

    def load(self) -> None:
        """Prepare the engine (download / load weights).  Idempotent."""
        ...

    def unload(self) -> None:
        """Release weights / memory."""
        ...

    def infer_frames(self, spectrogram: Any) -> EngineFrameOutput:
        """Run the model on a spectrogram and return per-frame logits.

        Parameters
        ----------
        spectrogram:
            A :class:`~app.domain.models.Spectrogram` whose ``data`` is
            a ``(T, 128)`` float32 numpy array.
        """
        ...
