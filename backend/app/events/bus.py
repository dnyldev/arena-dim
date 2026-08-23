"""Event bus and a job-scoped progress reporter.

The bus supports two consumers:

* **Subscribers** — in-process callables (the job manager keeps a list
  of events per job; the SSE endpoint subscribes to stream them).
* **Python logging** — every event is logged at an appropriate level.

Subscribers are called synchronously; they must not block.  The SSE
endpoint queues events itself rather than doing work inside the
callback.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Deque

from app.events.models import AnalysisEvent, EventStage, EventStatus

logger = logging.getLogger("beat_engine.events")

EventHandler = Callable[[AnalysisEvent], None]


class EventBus:
    """Thread-safe pub/sub for analysis events."""

    def __init__(self, history_per_job: int = 2000) -> None:
        self._lock = threading.RLock()
        self._handlers: list[EventHandler] = []
        self._history: dict[str, Deque[AnalysisEvent]] = defaultdict(
            lambda: deque(maxlen=history_per_job)
        )

    def subscribe(self, handler: EventHandler) -> Callable[[], None]:
        with self._lock:
            self._handlers.append(handler)

        def unsubscribe() -> None:
            with self._lock:
                try:
                    self._handlers.remove(handler)
                except ValueError:
                    pass

        return unsubscribe

    def publish(self, event: AnalysisEvent) -> None:
        with self._lock:
            self._history[event.job_id].append(event)
            handlers = list(self._handlers)

        # Log — map status to log level.
        level = self._log_level(event)
        logger.log(
            level,
            "[%s] %s/%s %s",
            event.job_id[:8],
            event.stage.value,
            event.status.value,
            event.message,
            extra={"metadata": event.metadata},
        )

        for handler in handlers:
            try:
                handler(event)
            except Exception:  # noqa: BLE001 - a bad subscriber must not kill the pipeline
                logger.exception("Event handler raised; continuing")

    def history(self, job_id: str) -> list[AnalysisEvent]:
        with self._lock:
            return list(self._history.get(job_id, ()))

    def clear(self, job_id: str) -> None:
        with self._lock:
            self._history.pop(job_id, None)

    @staticmethod
    def _log_level(event: AnalysisEvent) -> int:
        if event.status == EventStatus.FAILED:
            return logging.ERROR
        if event.status == EventStatus.WARNING:
            return logging.WARNING
        if event.status == EventStatus.STARTED:
            return logging.INFO
        return logging.DEBUG


_bus: EventBus | None = None
_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        with _bus_lock:
            if _bus is None:
                _bus = EventBus()
    return _bus


def reset_event_bus() -> None:
    """Test helper."""
    global _bus
    with _bus_lock:
        _bus = None


class JobReporter:
    """A :class:`ProgressReporter` bound to a single job id."""

    def __init__(self, job_id: str, bus: EventBus | None = None) -> None:
        self.job_id = job_id
        self._bus = bus or get_event_bus()
        self._stage_starts: dict[EventStage, float] = {}

    def _publish(
        self,
        stage: EventStage,
        status: EventStatus,
        message: str = "",
        progress: float | None = None,
        elapsed_ms: float | None = None,
        metadata: dict | None = None,
    ) -> None:
        self._bus.publish(
            AnalysisEvent(
                job_id=self.job_id,
                stage=stage,
                status=status,
                message=message,
                progress=progress,
                elapsed_ms=elapsed_ms,
                metadata=metadata or {},
            )
        )

    def started(self, stage: EventStage, message: str = "", **metadata: object) -> None:
        self._stage_starts[stage] = time.perf_counter()
        self._publish(stage, EventStatus.STARTED, message, metadata=metadata)

    def progress(
        self, stage: EventStage, progress: float, message: str = "", **metadata: object
    ) -> None:
        self._publish(
            stage, EventStatus.PROGRESS, message, progress=progress, metadata=metadata
        )

    def completed(
        self,
        stage: EventStage,
        message: str = "",
        elapsed_ms: float | None = None,
        **metadata: object,
    ) -> None:
        if elapsed_ms is None and stage in self._stage_starts:
            elapsed_ms = (time.perf_counter() - self._stage_starts.pop(stage)) * 1000.0
        self._publish(
            stage, EventStatus.COMPLETED, message, elapsed_ms=elapsed_ms, metadata=metadata
        )

    def failed(
        self,
        stage: EventStage,
        message: str,
        elapsed_ms: float | None = None,
        **metadata: object,
    ) -> None:
        if elapsed_ms is None and stage in self._stage_starts:
            elapsed_ms = (time.perf_counter() - self._stage_starts.pop(stage)) * 1000.0
        self._publish(
            stage, EventStatus.FAILED, message, elapsed_ms=elapsed_ms, metadata=metadata
        )

    def info(self, stage: EventStage, message: str, **metadata: object) -> None:
        self._publish(stage, EventStatus.INFO, message, metadata=metadata)

    def warning(self, stage: EventStage, message: str, **metadata: object) -> None:
        self._publish(stage, EventStatus.WARNING, message, metadata=metadata)

    def skipped(self, stage: EventStage, message: str = "", **metadata: object) -> None:
        self._publish(stage, EventStatus.SKIPPED, message, metadata=metadata)
