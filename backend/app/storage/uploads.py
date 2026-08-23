"""Upload / temporary-file storage.

Security:
* filenames are never trusted; the server chooses the on-disk name,
* the upload directory is created under the configured data dir,
* size is bounded by ``MAX_UPLOAD_MB``,
* path traversal is impossible because the client filename is only
  retained for display, never used as a path component,
* files are cleaned up after the job completes.
"""

from __future__ import annotations

import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.config import RuntimeConfig
from app.core.errors import AudioTooLargeError, StorageError
from app.domain.models import AudioInput


_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def safe_filename(name: str) -> str:
    """Reduce an arbitrary filename to a safe display stem."""
    name = os.path.basename(name)
    name = _SAFE.sub("_", name)
    return name[:120] or "audio"


class UploadStorage:
    def __init__(self, runtime: RuntimeConfig) -> None:
        self.runtime = runtime
        runtime.ensure_dirs()

    def save_stream(
        self,
        stream: BinaryIO,
        original_filename: str,
        content_type: str | None = None,
    ) -> AudioInput:
        max_bytes = self.runtime.max_upload_mb * 1024 * 1024
        job_id = uuid.uuid4().hex
        # Extension is retained for format detection but the path itself
        # is server-generated.
        ext = Path(original_filename).suffix.lower()
        if ext and not re.fullmatch(r"\.[a-z0-9]{1,8}", ext):
            ext = ""
        target = self.runtime.upload_dir / f"{job_id}{ext}"
        bytes_written = 0
        try:
            with open(target, "wb") as out:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        out.close()
                        target.unlink(missing_ok=True)
                        raise AudioTooLargeError(
                            f"Upload exceeds maximum of "
                            f"{self.runtime.max_upload_mb} MB",
                            technical_detail=f"bytes={bytes_written}",
                            recoverable=True,
                        )
                    out.write(chunk)
        except AudioTooLargeError:
            raise
        except OSError as exc:
            raise StorageError(
                f"Could not store upload: {exc}", technical_detail=str(exc)
            ) from exc
        return AudioInput(
            path=target,
            original_filename=safe_filename(original_filename),
            size_bytes=bytes_written,
            content_type=content_type,
        )

    def cleanup(self, audio: AudioInput) -> None:
        try:
            audio.path.unlink(missing_ok=True)
        except OSError:
            pass

    def cleanup_artifacts(self, job_id: str) -> None:
        d = self.runtime.artifact_dir / job_id
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    def purge_old_uploads(self, max_age_seconds: int = 3600) -> int:
        """Best-effort cleanup of stale uploads (e.g. from crashed jobs)."""
        cutoff = time.time() - max_age_seconds
        removed = 0
        for p in self.runtime.upload_dir.iterdir():
            try:
                if p.is_file() and p.stat().st_mtime < cutoff:
                    p.unlink(missing_ok=True)
                    removed += 1
            except OSError:
                continue
        return removed
