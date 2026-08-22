"""FastAPI application entry point."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import router
from app.core.config import RuntimeConfig, get_runtime, set_runtime
from app.core.errors import BeatAnalysisError
from app.jobs import JobManager, set_job_manager


def _configure_logging() -> None:
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    runtime = get_runtime()
    runtime.ensure_dirs()
    # Build a fresh job manager for this app instance so tests don't
    # inherit shut-down workers from a previous app.
    jm = JobManager(runtime)
    set_job_manager(jm)
    logging.getLogger("beat_engine").info(
        "Beat Analysis Engine starting (device=%s, version=%s)",
        runtime.device,
        __version__,
    )
    yield
    jm.shutdown(wait=True, timeout=5.0)
    logging.getLogger("beat_engine").info("Beat Analysis Engine stopped")


def create_app(runtime: RuntimeConfig | None = None) -> FastAPI:
    if runtime is not None:
        set_runtime(runtime)
    runtime = get_runtime()

    app = FastAPI(
        title="Beat Analysis Engine",
        version=__version__,
        description=(
            "CPU-only operational dashboard and API for beat / downbeat "
            "analysis powered by Beat This!"
        ),
        lifespan=lifespan,
    )

    origins = list(runtime.cors_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins and origins != ["*"] else ["*"],
        allow_credentials=runtime.allow_credentials and origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.exception_handler(BeatAnalysisError)
    async def _beat_error_handler(request: Request, exc: BeatAnalysisError):
        status = 400
        code = exc.code.value if hasattr(exc.code, "value") else str(exc.code)
        if code in {"MODEL_WEIGHTS_MISSING", "MODEL_UNAVAILABLE", "DEPENDENCY_MISSING"}:
            status = 503
        elif code in {"JOB_NOT_FOUND"}:
            status = 404
        elif code in {"JOB_INVALID_STATE"}:
            status = 409
        return JSONResponse(status_code=status, content={"error": exc.to_dict()})

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_CONFIGURATION",
                    "stage": "api",
                    "message": "Request validation failed",
                    "technical_detail": str(exc.errors()),
                    "recoverable": True,
                }
            },
        )

    @app.get("/", tags=["system"])
    def root():
        return {
            "name": "Beat Analysis Engine",
            "version": __version__,
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


app = create_app()
