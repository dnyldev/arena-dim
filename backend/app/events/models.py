"""Structured pipeline events.

Every pipeline stage emits :class:`AnalysisEvent` objects through an
:class:`~app.events.bus.EventBus`.  Events are the single source of
truth for:

* the frontend live log panel (via SSE),
* server logs,
* the debug/timing breakdown in the final result,
* tests asserting on pipeline behaviour.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class EventStage(str, Enum):
    """Pipeline stages — order roughly mirrors the orchestrator."""

    VALIDATE = "validate"
    PROBE = "probe"
    AUDIO_LOAD = "audio_load"
    NORMALIZE = "normalize"
    RESAMPLE = "resample"
    FEATURE_EXTRACTION = "feature_extraction"
    MODEL_LOAD = "model_load"
    INFERENCE = "inference"
    POSTPROCESS = "postprocess"
    VALIDATION = "validation"
    TEMPO = "tempo"
    RHYTHM = "rhythm"
    METER = "meter"
    RESULT = "result"
    ARTIFACT = "artifact"
    JOB = "job"
    SYSTEM = "system"


class EventStatus(str, Enum):
    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    INFO = "info"
    WARNING = "warning"


@dataclass
class AnalysisEvent:
    job_id: str
    stage: EventStage
    status: EventStatus
    timestamp: float = field(default_factory=time.time)
    message: str = ""
    progress: float | None = None
    elapsed_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "stage": self.stage.value,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "message": self.message,
            "progress": self.progress,
            "elapsed_ms": self.elapsed_ms,
            "metadata": self.metadata,
        }


class ProgressReporter(Protocol):
    """Interface stages use to report progress."""

    def started(self, stage: EventStage, message: str = "", **metadata: Any) -> None: ...

    def progress(
        self, stage: EventStage, progress: float, message: str = "", **metadata: Any
    ) -> None: ...

    def completed(
        self, stage: EventStage, message: str = "", elapsed_ms: float | None = None, **metadata: Any
    ) -> None: ...

    def failed(
        self,
        stage: EventStage,
        message: str,
        elapsed_ms: float | None = None,
        **metadata: Any,
    ) -> None: ...

    def info(self, stage: EventStage, message: str, **metadata: Any) -> None: ...

    def warning(self, stage: EventStage, message: str, **metadata: Any) -> None: ...

    def skipped(self, stage: EventStage, message: str = "", **metadata: Any) -> None: ...
