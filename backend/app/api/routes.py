"""HTTP API routes."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, StreamingResponse

from app.audio.backends import default_backends
from app.core.config import (
    KNOWN_CHECKPOINTS,
    AnalysisConfig,
    BeatThisSpec,
    get_runtime,
)
from app.core.errors import BeatAnalysisError
from app.engines.beat_this import get_model_manager
from app.jobs import get_job_manager
from app.schemas.public import (
    AnalyzeRequest,
    ErrorOut,
    EventOut,
    HealthOut,
    JobOut,
    ModelInfoOut,
)

router = APIRouter(prefix="/api")

_START_TIME = time.time()


# --------------------------------------------------------------------------- #
# Health / status
# --------------------------------------------------------------------------- #


@router.get("/health", response_model=HealthOut, tags=["system"])
def health(request: Request) -> HealthOut:
    runtime = get_runtime()
    mgr = get_model_manager(runtime)
    models = [
        ModelInfoOut(**mgr.model_info(name)) for name in KNOWN_CHECKPOINTS
    ]
    return HealthOut(
        status="ok",
        version=request.app.version,
        device=runtime.device,
        cpu_only=True,
        audio_backends=[b.name for b in default_backends()],
        beat_this_installed=mgr.beat_this_available,
        models=models,
        uptime_sec=round(time.time() - _START_TIME, 3),
    )


@router.get("/models", response_model=list[ModelInfoOut], tags=["models"])
def list_models() -> list[ModelInfoOut]:
    runtime = get_runtime()
    mgr = get_model_manager(runtime)
    return [ModelInfoOut(**mgr.model_info(name)) for name in KNOWN_CHECKPOINTS]


@router.get("/models/{checkpoint:path}", response_model=ModelInfoOut, tags=["models"])
def model_status(checkpoint: str) -> ModelInfoOut:
    runtime = get_runtime()
    mgr = get_model_manager(runtime)
    return ModelInfoOut(**mgr.model_info(checkpoint))


@router.post("/models/preload/{checkpoint:path}", tags=["models"])
def preload_model(checkpoint: str) -> dict[str, Any]:
    runtime = get_runtime()
    mgr = get_model_manager(runtime)
    if not mgr.beat_this_available:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DEPENDENCY_MISSING",
                "message": "beat-this is not installed; cannot preload.",
                "technical_detail": mgr.import_error,
                "recoverable": True,
            },
        )
    try:
        mgr.get_model(checkpoint)
    except BeatAnalysisError as exc:
        raise HTTPException(status_code=502, detail=exc.to_dict()) from exc
    return {"checkpoint": checkpoint, "status": mgr.status(checkpoint).value}


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #


def _parse_config(raw: str | None) -> AnalysisConfig:
    if not raw:
        return AnalysisConfig()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_CONFIGURATION",
                "message": "config must be valid JSON",
                "technical_detail": str(exc),
                "recoverable": True,
            },
        )
    try:
        return AnalysisConfig.from_dict(data)
    except BeatAnalysisError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc


@router.post("/analysis", response_model=JobOut, tags=["analysis"])
async def create_analysis(
    request: Request,
    audio: UploadFile = File(...),
    config: str | None = Form(default=None),
) -> JobOut:
    runtime = get_runtime()
    jm = get_job_manager(runtime)
    cfg = _parse_config(config)

    # Stream upload to disk (bounded size).
    storage = jm.storage
    try:
        audio_input = storage.save_stream(
            audio.file,
            original_filename=audio.filename or "audio",
            content_type=audio.content_type,
        )
    except BeatAnalysisError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc

    try:
        job = jm.submit(audio_input, cfg)
    except BeatAnalysisError as exc:
        storage.cleanup(audio_input)
        raise HTTPException(status_code=429, detail=exc.to_dict()) from exc
    return JobOut(**job.to_dict())


@router.get(
    "/jobs/{job_id}",
    response_model=JobOut,
    responses={404: {"model": ErrorOut}},
    tags=["jobs"],
)
def get_job(job_id: str) -> JobOut:
    jm = get_job_manager(get_runtime())
    try:
        job = jm.get(job_id)
    except BeatAnalysisError as exc:
        raise HTTPException(status_code=404, detail=exc.to_dict()) from exc
    return JobOut(**job.to_dict())


@router.get("/jobs", response_model=list[JobOut], tags=["jobs"])
def list_jobs(limit: int = 50) -> list[JobOut]:
    jm = get_job_manager(get_runtime())
    return [JobOut(**j.to_dict()) for j in jm.list_jobs(limit=limit)]


@router.post("/jobs/{job_id}/cancel", response_model=JobOut, tags=["jobs"])
def cancel_job(job_id: str) -> JobOut:
    jm = get_job_manager(get_runtime())
    try:
        job = jm.cancel(job_id)
    except BeatAnalysisError as exc:
        raise HTTPException(status_code=409, detail=exc.to_dict()) from exc
    return JobOut(**job.to_dict())


@router.get("/jobs/{job_id}/events", response_model=list[EventOut], tags=["jobs"])
def job_events(job_id: str) -> list[EventOut]:
    jm = get_job_manager(get_runtime())
    try:
        events = jm.events(job_id)
    except BeatAnalysisError as exc:
        raise HTTPException(status_code=404, detail=exc.to_dict()) from exc
    return [EventOut(**e) for e in events]


@router.get("/jobs/{job_id}/events/stream", tags=["jobs"])
async def stream_events(job_id: str, request: Request) -> StreamingResponse:
    """Server-Sent Events stream for a single job.

    Replays existing events first, then streams new ones until the job
    reaches a terminal state (or the client disconnects).
    """
    jm = get_job_manager(get_runtime())
    try:
        jm.get(job_id)
    except BeatAnalysisError as exc:
        raise HTTPException(status_code=404, detail=exc.to_dict()) from exc

    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def _handler(event: Any) -> None:
        if event.job_id != job_id:
            return
        loop.call_soon_threadsafe(queue.put_nowait, event.to_dict())

    unsub = jm.bus.subscribe(_handler)
    # Replay history.
    for e in jm.events(job_id):
        await queue.put(e)

    async def event_gen():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    evt = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if evt is None:
                    break
                yield f"data: {json.dumps(evt)}\n\n"
                if evt.get("stage") == "job" and evt.get("status") in (
                    "completed",
                    "failed",
                ):
                    break
        finally:
            unsub()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# --------------------------------------------------------------------------- #
# Artifacts
# --------------------------------------------------------------------------- #


@router.get("/jobs/{job_id}/artifacts/{name}", tags=["artifacts"])
def download_artifact(job_id: str, name: str) -> FileResponse:
    jm = get_job_manager(get_runtime())
    try:
        job = jm.get(job_id)
    except BeatAnalysisError as exc:
        raise HTTPException(status_code=404, detail=exc.to_dict()) from exc
    if not job.result:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ARTIFACT_WRITE_FAILED",
                "message": "No artifacts available (job not completed).",
            },
        )
    path_str = job.result.get("artifacts", {}).get(name)
    if not path_str:
        raise HTTPException(
            status_code=404,
            detail={"code": "ARTIFACT_WRITE_FAILED", "message": f"Unknown artifact '{name}'"},
        )
    path = Path(path_str)
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail={"code": "ARTIFACT_WRITE_FAILED", "message": "Artifact file missing."},
        )
    media_type = "application/octet-stream"
    if name == "json" or path.suffix == ".json":
        media_type = "application/json"
    elif path.suffix == ".beats":
        media_type = "text/tab-separated-values"
    return FileResponse(
        path,
        media_type=media_type,
        filename=path.name,
    )


# --------------------------------------------------------------------------- #
# Spec / constants (for the UI to display)
# --------------------------------------------------------------------------- #


@router.get("/spec", tags=["system"])
def engine_spec() -> dict[str, Any]:
    return {
        "sample_rate": BeatThisSpec.SAMPLE_RATE,
        "hop_length": BeatThisSpec.HOP_LENGTH,
        "n_fft": BeatThisSpec.N_FFT,
        "n_mels": BeatThisSpec.N_MELS,
        "f_min": BeatThisSpec.F_MIN,
        "f_max": BeatThisSpec.F_MAX,
        "fps": BeatThisSpec.fps(),
        "chunk_size": BeatThisSpec.CHUNK_SIZE,
        "border_size": BeatThisSpec.BORDER_SIZE,
        "known_checkpoints": [
            {
                "name": c.name,
                "display_name": c.display_name,
                "description": c.description,
                "approx_size_mb": c.approx_size_mb,
                "is_small": c.is_small,
            }
            for c in KNOWN_CHECKPOINTS.values()
        ],
    }
