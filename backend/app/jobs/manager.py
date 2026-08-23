"""In-memory job manager.

Implements the job state machine::

    QUEUED → RUNNING → COMPLETED
                     ↘ FAILED
                     ↘ CANCELLED

Concurrency is bounded by ``max_concurrent_analyses`` (default 1 — CPU
inference is heavy).  Excess jobs are queued up to ``job_queue_max``.
The manager runs jobs on a worker thread, captures the
:class:`BeatAnalysisResult` or :class:`BeatAnalysisError`, and records
all events for the debug panel.
"""

from __future__ import annotations

import queue
import threading
import time
import traceback
from dataclasses import asdict
from typing import Any

from app.analysis.orchestrator import AnalysisOrchestrator
from app.core.config import AnalysisConfig, RuntimeConfig
from app.core.errors import (
    BeatAnalysisError,
    JobCancelledError,
    JobInvalidStateError,
    JobNotFoundError,
    wrap_exception,
)
from app.domain.models import AudioInput, Job, JobState
from app.events import EventStage, JobReporter, get_event_bus
from app.storage import UploadStorage


class JobManager:
    def __init__(
        self,
        runtime: RuntimeConfig,
        orchestrator: AnalysisOrchestrator | None = None,
        storage: UploadStorage | None = None,
    ) -> None:
        self.runtime = runtime
        self.storage = storage or UploadStorage(runtime)
        self.orchestrator = orchestrator or AnalysisOrchestrator(runtime)
        self.bus = get_event_bus()
        self._jobs: dict[str, Job] = {}
        self._lock = threading.RLock()
        self._queue: queue.Queue[str] = queue.Queue(maxsize=runtime.job_queue_max)
        self._slots = threading.Semaphore(runtime.max_concurrent_analyses)
        self._stop = threading.Event()
        self._workers: list[threading.Thread] = []
        self._pending_audio: dict[str, AudioInput] = {}
        self._start_workers()

    # -- worker plumbing ------------------------------------------------- #

    def _start_workers(self) -> None:
        for i in range(max(1, self.runtime.max_concurrent_analyses)):
            t = threading.Thread(
                target=self._worker_loop, name=f"analysis-worker-{i}", daemon=True
            )
            t.start()
            self._workers.append(t)

    def shutdown(self, wait: bool = True, timeout: float = 5.0) -> None:
        self._stop.set()
        for _ in self._workers:
            self._queue.put(None)  # wake workers
        if wait:
            deadline = time.time() + timeout
            for t in self._workers:
                remaining = max(0.0, deadline - time.time())
                t.join(timeout=remaining)

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            try:
                job_id = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if job_id is None:
                return
            try:
                self._slots.acquire()
                try:
                    self._run_job(job_id)
                finally:
                    self._slots.release()
            except Exception:  # noqa: BLE001
                # Last-resort guard; _run_job handles errors itself.
                traceback.print_exc()
            finally:
                self._queue.task_done()

    # -- public API ------------------------------------------------------ #

    def submit(self, audio: AudioInput, config: AnalysisConfig) -> Job:
        with self._lock:
            if len(self._jobs) >= self.runtime.job_queue_max * 4:
                # Prevent unbounded history growth.
                self._prune_history()
            job = Job(config=asdict(config), input=audio.original_filename)
            self._jobs[job.id] = job
        reporter = JobReporter(job.id, self.bus)
        reporter.info(
            EventStage.JOB,
            f"Job queued for {audio.original_filename}",
            config=asdict(config),
        )
        try:
            self._queue.put_nowait(job.id)
        except queue.Full as exc:
            job.state = JobState.FAILED
            job.finished_at = time.time()
            job.error = {
                "code": "JOB_QUEUE_FULL",
                "stage": "jobs",
                "message": "Analysis queue is full; try again later.",
                "recoverable": True,
            }
            reporter.failed(EventStage.JOB, "Queue full")
            raise JobInvalidStateError(
                "Analysis queue is full", technical_detail=str(exc)
            ) from exc
        self._pending_audio[job.id] = audio
        return job

    def get(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        return job

    def list_jobs(self, limit: int = 50) -> list[Job]:
        with self._lock:
            jobs = sorted(
                self._jobs.values(), key=lambda j: j.created_at, reverse=True
            )
        return jobs[:limit]

    def events(self, job_id: str) -> list[dict[str, Any]]:
        self.get(job_id)
        return [e.to_dict() for e in self.bus.history(job_id)]

    def cancel(self, job_id: str) -> Job:
        job = self.get(job_id)
        with self._lock:
            if job.state in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
                raise JobInvalidStateError(
                    f"Cannot cancel job in state {job.state.value}"
                )
            job.cancel_requested = True
        return job

    # -- internal -------------------------------------------------------- #

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            audio = self._pending_audio.pop(job_id, None)
        if job is None or audio is None:
            return

        reporter = JobReporter(job_id, self.bus)
        if job.cancel_requested:
            self._mark_cancelled(job, reporter)
            return

        job.state = JobState.RUNNING
        job.started_at = time.time()
        reporter.info(EventStage.JOB, "Job started")
        config = AnalysisConfig.from_dict(job.config)

        try:
            result = self.orchestrator.run(job_id, audio, config, reporter)
        except BeatAnalysisError as exc:
            self._mark_failed(job, exc, reporter)
            return
        except Exception as exc:  # noqa: BLE001
            wrapped = wrap_exception(
                exc, stage="system", message=f"Unexpected failure: {exc}"
            )
            self._mark_failed(job, wrapped, reporter)
            return
        finally:
            # Clean up the uploaded temp file regardless of outcome.
            self.storage.cleanup(audio)

        with self._lock:
            job.state = JobState.COMPLETED
            job.finished_at = time.time()
            job.result = result.to_public_dict()
        reporter.completed(
            EventStage.JOB,
            "Job completed",
            total_ms=(job.finished_at - job.created_at) * 1000,
        )

    def _mark_failed(
        self, job: Job, exc: BeatAnalysisError, reporter: JobReporter
    ) -> None:
        # Report on the failing stage if it is one of our known stages;
        # always also surface the failure on the JOB stage so the SSE
        # "job finished" condition fires.
        try:
            stage = EventStage(exc.stage)
        except ValueError:
            stage = EventStage.SYSTEM
        reporter.failed(
            stage,
            exc.message,
            code=exc.code.value if hasattr(exc.code, "value") else str(exc.code),
        )
        with self._lock:
            job.state = JobState.FAILED
            job.finished_at = time.time()
            job.error = exc.to_dict()

    def _mark_cancelled(self, job: Job, reporter: JobReporter) -> None:
        with self._lock:
            job.state = JobState.CANCELLED
            job.finished_at = time.time()
            job.error = {
                "code": "JOB_CANCELLED",
                "stage": "jobs",
                "message": "Job was cancelled",
                "recoverable": False,
            }
        reporter.info(EventStage.JOB, "Job cancelled")

    def _prune_history(self) -> None:
        cutoff = time.time() - self.runtime.job_ttl_seconds
        with self._lock:
            stale = [
                jid
                for jid, job in self._jobs.items()
                if job.finished_at is not None and job.finished_at < cutoff
            ]
            for jid in stale:
                self.bus.clear(jid)
                self.storage.cleanup_artifacts(jid)
                del self._jobs[jid]


_manager: JobManager | None = None
_manager_lock = threading.Lock()


def get_job_manager(runtime: RuntimeConfig | None = None) -> JobManager:
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                from app.core.config import get_runtime

                _manager = JobManager(runtime or get_runtime())
    return _manager


def reset_job_manager() -> None:
    """Test helper — shuts down and clears the singleton."""
    global _manager
    with _manager_lock:
        if _manager is not None:
            _manager.shutdown(wait=False)
        _manager = None


def set_job_manager(jm: JobManager) -> None:
    """Explicitly inject a manager (used by create_app / tests)."""
    global _manager
    with _manager_lock:
        if _manager is not None:
            _manager.shutdown(wait=False)
        _manager = jm
