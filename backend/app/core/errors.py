"""Error taxonomy for the Beat Analysis Engine.

Every failure that crosses a pipeline boundary should be expressed as a
subclass of :class:`BeatAnalysisError`.  Each error carries a stable
machine-readable ``code``, the ``stage`` at which it occurred, a
user-facing ``message``, a ``technical_detail`` for developers, and a
``recoverable`` flag.

No exception is ever silently swallowed in the pipeline; unexpected
exceptions are wrapped into a :class:`SystemError` with their traceback
preserved in ``technical_detail``.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Stable error codes surfaced to the API / frontend."""

    # Configuration
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    UNSUPPORTED_PARAMETER = "UNSUPPORTED_PARAMETER"

    # Audio
    AUDIO_NOT_FOUND = "AUDIO_NOT_FOUND"
    AUDIO_UNREADABLE = "AUDIO_UNREADABLE"
    AUDIO_UNSUPPORTED_FORMAT = "AUDIO_UNSUPPORTED_FORMAT"
    AUDIO_TOO_LARGE = "AUDIO_TOO_LARGE"
    AUDIO_TOO_SHORT = "AUDIO_TOO_SHORT"
    AUDIO_CORRUPT = "AUDIO_CORRUPT"

    # Model
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    MODEL_WEIGHTS_MISSING = "MODEL_WEIGHTS_MISSING"
    MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"
    MODEL_NOT_READY = "MODEL_NOT_READY"

    # Inference
    INFERENCE_FAILED = "INFERENCE_FAILED"

    # Postprocessing
    POSTPROCESSING_FAILED = "POSTPROCESSING_FAILED"

    # Validation
    VALIDATION_FAILED = "VALIDATION_FAILED"
    EMPTY_RESULT = "EMPTY_RESULT"

    # Artifact / storage
    ARTIFACT_WRITE_FAILED = "ARTIFACT_WRITE_FAILED"
    STORAGE_ERROR = "STORAGE_ERROR"

    # Job lifecycle
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_INVALID_STATE = "JOB_INVALID_STATE"
    JOB_CANCELLED = "JOB_CANCELLED"

    # System
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"


class BeatAnalysisError(Exception):
    """Base class for all engine errors.

    Attributes
    ----------
    code:
        Stable machine-readable code.
    stage:
        Pipeline stage where the error originated.
    message:
        Human-readable, user-safe message.
    technical_detail:
        Developer-oriented detail (may contain exception text).
    recoverable:
        Whether retrying (possibly after a config change) could succeed.
    """

    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    stage: str = "unknown"
    recoverable: bool = False

    def __init__(
        self,
        message: str,
        *,
        stage: str | None = None,
        technical_detail: str | None = None,
        recoverable: bool | None = None,
        code: ErrorCode | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if stage is not None:
            self.stage = stage
        if technical_detail is not None:
            self.technical_detail = technical_detail
        else:
            self.technical_detail = message
        if recoverable is not None:
            self.recoverable = recoverable
        if code is not None:
            self.code = code

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value if isinstance(self.code, ErrorCode) else str(self.code),
            "stage": self.stage,
            "message": self.message,
            "technical_detail": self.technical_detail,
            "recoverable": self.recoverable,
        }

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"[{self.code.value}] {self.stage}: {self.message}"


# --------------------------------------------------------------------------- #
# Concrete errors
# --------------------------------------------------------------------------- #


class ConfigurationError(BeatAnalysisError):
    code = ErrorCode.INVALID_CONFIGURATION
    stage = "configuration"
    recoverable = True


class UnsupportedParameterError(ConfigurationError):
    code = ErrorCode.UNSUPPORTED_PARAMETER


class AudioError(BeatAnalysisError):
    stage = "audio"
    recoverable = True


class AudioNotFoundError(AudioError):
    code = ErrorCode.AUDIO_NOT_FOUND


class AudioUnreadableError(AudioError):
    code = ErrorCode.AUDIO_UNREADABLE


class AudioUnsupportedFormatError(AudioError):
    code = ErrorCode.AUDIO_UNSUPPORTED_FORMAT


class AudioTooLargeError(AudioError):
    code = ErrorCode.AUDIO_TOO_LARGE


class AudioTooShortError(AudioError):
    code = ErrorCode.AUDIO_TOO_SHORT
    recoverable = False


class AudioCorruptError(AudioError):
    code = ErrorCode.AUDIO_CORRUPT


class ModelError(BeatAnalysisError):
    stage = "model"


class ModelUnavailableError(ModelError):
    code = ErrorCode.MODEL_UNAVAILABLE
    recoverable = True


class ModelWeightsMissingError(ModelError):
    code = ErrorCode.MODEL_WEIGHTS_MISSING
    recoverable = True


class ModelLoadError(ModelError):
    code = ErrorCode.MODEL_LOAD_FAILED
    recoverable = True


class ModelNotReadyError(ModelError):
    code = ErrorCode.MODEL_NOT_READY
    recoverable = True


class InferenceError(BeatAnalysisError):
    code = ErrorCode.INFERENCE_FAILED
    stage = "inference"
    recoverable = True


class PostProcessingError(BeatAnalysisError):
    code = ErrorCode.POSTPROCESSING_FAILED
    stage = "postprocessing"
    recoverable = True


class ValidationError(BeatAnalysisError):
    code = ErrorCode.VALIDATION_FAILED
    stage = "validation"
    recoverable = False


class EmptyResultError(ValidationError):
    code = ErrorCode.EMPTY_RESULT
    recoverable = False


class ArtifactError(BeatAnalysisError):
    code = ErrorCode.ARTIFACT_WRITE_FAILED
    stage = "artifacts"
    recoverable = True


class StorageError(BeatAnalysisError):
    code = ErrorCode.STORAGE_ERROR
    stage = "storage"
    recoverable = True


class JobError(BeatAnalysisError):
    stage = "jobs"


class JobNotFoundError(JobError):
    code = ErrorCode.JOB_NOT_FOUND
    recoverable = False


class JobInvalidStateError(JobError):
    code = ErrorCode.JOB_INVALID_STATE
    recoverable = False


class JobCancelledError(JobError):
    code = ErrorCode.JOB_CANCELLED
    recoverable = False


class DependencyMissingError(BeatAnalysisError):
    code = ErrorCode.DEPENDENCY_MISSING
    stage = "startup"
    recoverable = True


class SystemError(BeatAnalysisError):
    code = ErrorCode.INTERNAL_ERROR
    stage = "system"
    recoverable = False


def wrap_exception(
    exc: BaseException,
    *,
    stage: str,
    message: str | None = None,
    recoverable: bool = False,
) -> BeatAnalysisError:
    """Wrap an arbitrary exception into a BeatAnalysisError.

    If ``exc`` is already a :class:`BeatAnalysisError`, its stage is
    left untouched when set, otherwise it is assigned.  The original
    traceback is retained via ``raise ... from exc`` at the call site.
    """
    if isinstance(exc, BeatAnalysisError):
        if exc.stage in ("unknown", "") and stage:
            exc.stage = stage
        return exc
    detail = f"{type(exc).__name__}: {exc}"
    return SystemError(
        message or f"Unexpected error during {stage}: {detail}",
        stage=stage,
        technical_detail=detail,
        recoverable=recoverable,
    )
