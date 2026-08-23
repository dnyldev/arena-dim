"""Checkpoint resolution for Beat This! models.

Resolution order for a given checkpoint name:

1. An explicit filesystem path (if it exists).
2. ``$CHECKPOINT_DIR/<name>.ckpt`` (offline / pre-placed weights).
3. The torch hub cache directory (``~/.cache/torch/hub/checkpoints``)
   populated by a previous auto-download.
4. Auto-download from the official CPJKU cloud URL (if
   ``ALLOW_MODEL_DOWNLOAD`` is true and the network is reachable).

The application never crashes at startup if weights are missing; the
missing condition is reported via :class:`EngineInfo` and fails clearly
when an analysis is attempted.
"""

from __future__ import annotations

import os
from pathlib import Path

from app.core.config import KNOWN_CHECKPOINTS, RuntimeConfig
from app.core.errors import ModelWeightsMissingError


def _torch_hub_dir() -> Path:
    torch_home = os.environ.get("TORCH_HOME")
    if torch_home:
        return Path(torch_home) / "hub" / "checkpoints"
    return Path.home() / ".cache" / "torch" / "hub" / "checkpoints"


def find_local_checkpoint(name: str, runtime: RuntimeConfig) -> Path | None:
    """Return a local path for ``name`` if one exists, else None."""
    p = Path(name)
    if p.is_file():
        return p.resolve()

    candidates = [
        runtime.checkpoint_dir / f"{name}.ckpt",
        runtime.checkpoint_dir / name,
        _torch_hub_dir() / f"beat_this-{name}.ckpt",
        _torch_hub_dir() / f"{name}.ckpt",
    ]
    for c in candidates:
        if c.is_file():
            return c.resolve()
    return None


def checkpoint_url(name: str, runtime: RuntimeConfig) -> str:
    return f"{runtime.checkpoint_base_url.rstrip('/')}/{name}.ckpt"


def resolve_checkpoint(
    name: str, runtime: RuntimeConfig, *, allow_download: bool | None = None
) -> tuple[Path | None, str | None]:
    """Resolve a checkpoint name.

    Returns ``(path_or_None, url_or_None)``.  If a local file exists,
    ``url`` is None.  If no local file exists but downloads are
    allowed, ``path`` is None and ``url`` is set (the caller performs
    the download).  If neither is available, both are None.
    """
    local = find_local_checkpoint(name, runtime)
    if local is not None:
        return local, None

    if allow_download is None:
        allow_download = runtime.allow_model_download

    if allow_download:
        # A full URL was passed as the name — use it directly.
        if name.startswith(("http://", "https://")):
            return None, name
        if name in KNOWN_CHECKPOINTS or name.endswith(".ckpt"):
            return None, checkpoint_url(name, runtime)

    return None, None


def require_resolved(
    name: str, runtime: RuntimeConfig
) -> tuple[Path, str | None]:
    """Like :func:`resolve_checkpoint` but raises if nothing is usable."""
    path, url = resolve_checkpoint(name, runtime)
    if path is None and url is None:
        raise ModelWeightsMissingError(
            f"Checkpoint '{name}' is not available locally and "
            "auto-download is disabled or the name is unknown.",
            technical_detail=(
                f"checkpoint_dir={runtime.checkpoint_dir}, "
                f"allow_download={runtime.allow_model_download}"
            ),
            recoverable=True,
        )
    return path, url
