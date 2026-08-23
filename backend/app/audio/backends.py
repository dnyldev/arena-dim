"""Audio I/O backends.

The audio layer is deliberately independent of ``beat_this`` so that it
can be reused by any future engine.  Two backends are provided:

* :class:`SoundfileBackend` — reads WAV/FLAC/OGG via ``soundfile``
  (libsndfile).  Pure CPU, no external processes.
* :class:`FfmpegBackend` — pipes any format ``ffmpeg`` understands
  through a subprocess and decodes the WAV output with ``soundfile``.

Backends are tried in order; the first that can probe AND decode the
file wins.  The fallback chain is reported through the event system so
failures are never silent.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.core.errors import (
    AudioCorruptError,
    AudioNotFoundError,
    AudioUnreadableError,
    AudioUnsupportedFormatError,
    DependencyMissingError,
)


@dataclass(frozen=True)
class DecodedAudio:
    signal: np.ndarray  # float64, shape (T,) or (T, C)
    sample_rate: int
    channels: int
    format: str | None = None
    codec: str | None = None
    bit_rate: int | None = None


class AudioBackend:
    name = "base"

    def available(self) -> bool:
        raise NotImplementedError

    def probe(self, path: Path) -> dict[str, Any]:
        raise NotImplementedError

    def decode(self, path: Path) -> DecodedAudio:
        raise NotImplementedError


class SoundfileBackend(AudioBackend):
    name = "soundfile"

    def __init__(self) -> None:
        try:
            import soundfile  # noqa: F401

            self._sf = soundfile
            self._available = True
        except Exception:  # noqa: BLE001
            self._sf = None
            self._available = False

    def available(self) -> bool:
        return self._available

    def probe(self, path: Path) -> dict[str, Any]:
        if not self._available:
            raise DependencyMissingError("soundfile is not installed", stage="audio")
        try:
            info = self._sf.info(str(path))
        except Exception as exc:
            raise AudioUnreadableError(
                f"soundfile could not read {path.name}: {exc}",
                technical_detail=str(exc),
            ) from exc
        return {
            "duration_sec": float(info.frames) / float(info.samplerate),
            "sample_rate": int(info.samplerate),
            "channels": int(info.channels),
            "format": info.format,
            "codec": info.subtype,
        }

    def decode(self, path: Path) -> DecodedAudio:
        if not self._available:
            raise DependencyMissingError("soundfile is not installed", stage="audio")
        try:
            signal, sr = self._sf.read(str(path), dtype="float64", always_2d=False)
        except Exception as exc:
            raise AudioCorruptError(
                f"soundfile failed to decode {path.name}",
                technical_detail=str(exc),
            ) from exc
        signal = np.asarray(signal, dtype=np.float64)
        channels = 1 if signal.ndim == 1 else int(signal.shape[1])
        info = self._sf.info(str(path))
        return DecodedAudio(
            signal=signal,
            sample_rate=int(sr),
            channels=channels,
            format=info.format,
            codec=info.subtype,
        )


class FfmpegBackend(AudioBackend):
    """Decode via ``ffmpeg`` subprocess → WAV → soundfile.

    Used as a fallback for formats libsndfile cannot read (e.g. MP3,
    M4A) when ffmpeg is installed on the host.
    """

    name = "ffmpeg"

    def __init__(self) -> None:
        self._ffmpeg = shutil.which("ffmpeg")
        self._ffprobe = shutil.which("ffprobe")
        self._available = self._ffmpeg is not None
        try:
            import soundfile  # noqa: F401

            self._sf = soundfile
        except Exception:  # noqa: BLE001
            self._sf = None

    def available(self) -> bool:
        return self._available and self._sf is not None

    def _run_ffprobe(self, path: Path) -> dict[str, Any]:
        if not self._ffprobe:
            return {}
        cmd = [
            self._ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration,bit_rate:stream=codec_name,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ]
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=30
            )
        except Exception:
            return {}
        import json

        try:
            data = json.loads(out.stdout)
        except Exception:
            return {}
        fmt = data.get("format", {})
        streams = data.get("streams", [])
        audio_stream = next(
            (s for s in streams if s.get("codec_type") == "audio" or "sample_rate" in s),
            streams[0] if streams else {},
        )
        result: dict[str, Any] = {}
        if "duration" in fmt:
            try:
                result["duration_sec"] = float(fmt["duration"])
            except ValueError:
                pass
        if "bit_rate" in fmt:
            try:
                result["bit_rate"] = int(fmt["bit_rate"])
            except ValueError:
                pass
        if audio_stream:
            result["codec"] = audio_stream.get("codec_name")
            if "sample_rate" in audio_stream:
                result["sample_rate"] = int(audio_stream["sample_rate"])
            if "channels" in audio_stream:
                result["channels"] = int(audio_stream["channels"])
        return result

    def probe(self, path: Path) -> dict[str, Any]:
        if not self.available():
            raise DependencyMissingError(
                "ffmpeg or soundfile not available", stage="audio"
            )
        meta = self._run_ffprobe(path)
        if not meta:
            raise AudioUnreadableError(
                f"ffprobe could not read metadata for {path.name}"
            )
        return meta

    def decode(self, path: Path) -> DecodedAudio:
        if not self.available():
            raise DependencyMissingError(
                "ffmpeg or soundfile not available", stage="audio"
            )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            cmd = [
                self._ffmpeg,
                "-v",
                "error",
                "-i",
                str(path),
                "-f",
                "wav",
                "-acodec",
                "pcm_f64le",
                "-y",
                str(tmp_path),
            ]
            try:
                proc = subprocess.run(
                    cmd, capture_output=True, check=True, timeout=600
                )
            except subprocess.CalledProcessError as exc:
                raise AudioCorruptError(
                    f"ffmpeg failed to decode {path.name}",
                    technical_detail=exc.stderr.decode("utf-8", "replace")[:2000],
                ) from exc
            except FileNotFoundError as exc:
                raise AudioUnsupportedFormatError(
                    "ffmpeg is not installed; cannot decode this format. "
                    "Install ffmpeg or upload a WAV file."
                ) from exc
            signal, sr = self._sf.read(str(tmp_path), dtype="float64", always_2d=False)
            signal = np.asarray(signal, dtype=np.float64)
            channels = 1 if signal.ndim == 1 else int(signal.shape[1])
            meta = self._run_ffprobe(path)
            return DecodedAudio(
                signal=signal,
                sample_rate=int(sr),
                channels=channels,
                format=path.suffix.lstrip(".").lower() or None,
                codec=meta.get("codec"),
                bit_rate=meta.get("bit_rate"),
            )
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass


def default_backends() -> list[AudioBackend]:
    """Return the ordered list of audio backends to try."""
    backends: list[AudioBackend] = [SoundfileBackend(), FfmpegBackend()]
    return [b for b in backends if b.available()]


def ensure_any_backend() -> None:
    if not default_backends():
        raise DependencyMissingError(
            "No audio backend available. Install soundfile "
            "(pip install soundfile) and/or ffmpeg.",
            stage="audio",
            recoverable=True,
        )
