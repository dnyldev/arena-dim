"""Beat This! model lifecycle manager.

Implements the model state machine::

    UNLOADED → LOADING → READY ⇄ IN_USE → (UNLOADED | FAILED)

Responsibilities:

* lazy-load a model on first use,
* cache one model instance per checkpoint (CPU-bound inference makes
  loading duplicates wasteful),
* serialize loading so concurrent requests don't load the same model
  twice,
* report cache/weight status without crashing at startup,
* keep Beat This! import failures as :class:`ModelUnavailableError`
  rather than import-time crashes.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from app.core.config import KNOWN_CHECKPOINTS, RuntimeConfig
from app.core.errors import (
    ModelLoadError,
    ModelUnavailableError,
    ModelWeightsMissingError,
    wrap_exception,
)
from app.engines.base import EngineStatus
from app.engines.beat_this.checkpoints import resolve_checkpoint


class _ModelEntry:
    def __init__(self, checkpoint: str) -> None:
        self.checkpoint = checkpoint
        self.lock = threading.RLock()
        self.status: EngineStatus = EngineStatus.UNLOADED
        self.model: Any | None = None
        self.load_error: str | None = None
        self.local_path: Path | None = None
        self.source: str = "unknown"  # local | download | unknown

    def snapshot(self) -> dict[str, Any]:
        return {
            "checkpoint": self.checkpoint,
            "status": self.status.value,
            "local_path": str(self.local_path) if self.local_path else None,
            "source": self.source,
            "load_error": self.load_error,
        }


class BeatThisModelManager:
    """Process-wide cache and lifecycle manager for Beat This! models."""

    def __init__(self, runtime: RuntimeConfig) -> None:
        self.runtime = runtime
        self._entries: dict[str, _ModelEntry] = {}
        self._global_lock = threading.RLock()
        self._beat_this: Any | None = None
        self._import_error: str | None = None
        self._try_import_beat_this()

    # -- import ----------------------------------------------------------- #

    def _try_import_beat_this(self) -> None:
        try:
            import inspect  # noqa: F401
            from beat_this.model.beat_tracker import BeatThis
            from beat_this.inference import load_checkpoint as _bt_load_ckpt
            from beat_this.utils import replace_state_dict_key
        except Exception as exc:  # noqa: BLE001
            self._import_error = f"{type(exc).__name__}: {exc}"
            return
        self._beat_this = {
            "BeatThis": BeatThis,
            "load_checkpoint": _bt_load_ckpt,
            "replace_state_dict_key": replace_state_dict_key,
        }

    @property
    def beat_this_available(self) -> bool:
        return self._beat_this is not None

    @property
    def import_error(self) -> str | None:
        return self._import_error

    # -- status ----------------------------------------------------------- #

    def entry(self, checkpoint: str) -> _ModelEntry:
        with self._global_lock:
            e = self._entries.get(checkpoint)
            if e is None:
                e = _ModelEntry(checkpoint)
                self._entries[checkpoint] = e
            return e

    def status(self, checkpoint: str) -> EngineStatus:
        return self.entry(checkpoint).status

    def weights_available(self, checkpoint: str) -> tuple[bool, str]:
        """Return (available, source) without triggering a download."""
        path, url = resolve_checkpoint(
            checkpoint, self.runtime, allow_download=False
        )
        if path is not None:
            return True, "local"
        if self.runtime.allow_model_download:
            # We could download on demand but don't probe the network here.
            return False, "downloadable"
        return False, "missing"

    def model_info(self, checkpoint: str) -> dict[str, Any]:
        e = self.entry(checkpoint)
        avail, source = self.weights_available(checkpoint)
        info = KNOWN_CHECKPOINTS.get(checkpoint)
        return {
            "checkpoint": checkpoint,
            "display_name": info.display_name if info else checkpoint,
            "description": info.description if info else None,
            "approx_size_mb": info.approx_size_mb if info else None,
            "is_small": info.is_small if info else False,
            "transformer_dim": info.transformer_dim if info else None,
            "engine_status": e.status.value,
            "weights_available": avail or e.model is not None,
            "weights_source": source if e.model is None else "loaded",
            "local_path": str(e.local_path) if e.local_path else None,
            "device": self.runtime.device,
            "beat_this_installed": self.beat_this_available,
            "import_error": self._import_error,
            "load_error": e.load_error,
        }

    # -- load / unload ---------------------------------------------------- #

    def get_model(self, checkpoint: str) -> Any:
        """Return a ready BeatThis model, loading if necessary."""
        e = self.entry(checkpoint)
        with e.lock:
            if e.model is not None and e.status in (
                EngineStatus.READY,
                EngineStatus.IN_USE,
            ):
                return e.model

            if not self.beat_this_available:
                e.status = EngineStatus.UNAVAILABLE
                e.load_error = self._import_error
                raise ModelUnavailableError(
                    "The 'beat-this' package is not installed. "
                    "Install it with: pip install beat-this",
                    technical_detail=self._import_error or "import failed",
                    recoverable=True,
                )

            e.status = EngineStatus.LOADING
            e.load_error = None
            try:
                model = self._load(checkpoint, e)
            except ModelWeightsMissingError:
                e.status = EngineStatus.FAILED
                raise
            except Exception as exc:
                e.status = EngineStatus.FAILED
                e.load_error = f"{type(exc).__name__}: {exc}"
                raise wrap_exception(
                    exc,
                    stage="model_load",
                    message=f"Failed to load model '{checkpoint}': {exc}",
                    recoverable=True,
                ) from exc
            e.model = model
            e.status = EngineStatus.READY
            return model

    def _load(self, checkpoint: str, e: _ModelEntry) -> Any:
        import inspect

        bt = self._beat_this
        BeatThis = bt["BeatThis"]
        bt_load_checkpoint = bt["load_checkpoint"]
        replace_state_dict_key = bt["replace_state_dict_key"]

        path, url = resolve_checkpoint(checkpoint, self.runtime)
        if path is None and url is None:
            raise ModelWeightsMissingError(
                f"Checkpoint '{checkpoint}' not found and cannot be downloaded.",
                technical_detail=(
                    f"checkpoint_dir={self.runtime.checkpoint_dir}, "
                    f"allow_download={self.runtime.allow_model_download}"
                ),
            )

        source = "local" if path is not None else "download"
        target = str(path) if path is not None else url
        try:
            ckpt = bt_load_checkpoint(target, self.runtime.device)
        except Exception as exc:
            raise ModelLoadError(
                f"Could not load checkpoint '{checkpoint}' from {target}",
                technical_detail=f"{type(exc).__name__}: {exc}",
                recoverable=True,
            ) from exc

        # Mirror the official hparams filtering from inference.load_model.
        sig = inspect.signature(BeatThis).parameters
        hparams = {
            k: v for k, v in ckpt.get("hyper_parameters", {}).items() if k in sig
        }
        model = BeatThis(**hparams)
        state = replace_state_dict_key(ckpt["state_dict"], "model.", "")
        model.load_state_dict(state)
        model.to(self.runtime.device).eval()

        e.local_path = path
        e.source = source
        return model

    def mark_in_use(self, checkpoint: str) -> None:
        e = self.entry(checkpoint)
        with e.lock:
            if e.model is not None and e.status == EngineStatus.READY:
                e.status = EngineStatus.IN_USE

    def mark_idle(self, checkpoint: str) -> None:
        e = self.entry(checkpoint)
        with e.lock:
            if e.status == EngineStatus.IN_USE:
                e.status = EngineStatus.READY

    def unload(self, checkpoint: str) -> None:
        e = self.entry(checkpoint)
        with e.lock:
            e.model = None
            e.status = EngineStatus.UNLOADED
            e.load_error = None

    def unload_all(self) -> None:
        with self._global_lock:
            names = list(self._entries)
        for name in names:
            self.unload(name)


_manager: BeatThisModelManager | None = None
_manager_lock = threading.Lock()


def get_model_manager(runtime: RuntimeConfig | None = None) -> BeatThisModelManager:
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                from app.core.config import get_runtime

                _manager = BeatThisModelManager(runtime or get_runtime())
    return _manager


def reset_model_manager() -> None:
    """Test helper."""
    global _manager
    with _manager_lock:
        _manager = None
