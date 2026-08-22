"""Audio loading, mono mixdown, and resampling.

These operations are independent of any beat engine.  The resampler
uses ``soxr`` (the same library Beat This! uses) when available, with
a fallback to linear interpolation via numpy (lower quality but
available without extra deps).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np

from app.audio.backends import (
    AudioBackend,
    DecodedAudio,
    default_backends,
    ensure_any_backend,
)
from app.core.config import BeatThisSpec, RuntimeConfig
from app.core.errors import (
    AudioNotFoundError,
    AudioTooShortError,
    AudioUnreadableError,
    wrap_exception,
)
from app.domain.models import AudioData, AudioInput, AudioProbe
from app.events import EventStage, JobReporter


class AudioProber:
    def __init__(self, backends: list[AudioBackend] | None = None) -> None:
        self._backends = backends if backends is not None else default_backends()

    def probe(self, audio: AudioInput) -> AudioProbe:
        if not audio.path.exists():
            raise AudioNotFoundError(
                f"Audio file not found: {audio.original_filename}",
                technical_detail=f"path={audio.path}",
            )
        errors: list[str] = []
        for backend in self._backends:
            try:
                meta = backend.probe(audio.path)
                return AudioProbe(
                    duration_sec=float(meta.get("duration_sec", 0.0)),
                    sample_rate=int(meta.get("sample_rate", 0)),
                    channels=int(meta.get("channels", 0)),
                    format=meta.get("format"),
                    codec=meta.get("codec"),
                    bit_rate=meta.get("bit_rate"),
                )
            except Exception as exc:  # try next backend
                errors.append(f"{backend.name}: {exc}")
        raise AudioUnreadableError(
            f"Could not probe audio: {audio.original_filename}. "
            "Install ffmpeg for MP3/M4A support or upload a WAV/FLAC file.",
            technical_detail=" | ".join(errors),
        )


class AudioLoader:
    def __init__(self, backends: list[AudioBackend] | None = None) -> None:
        self._backends = backends if backends is not None else default_backends()

    def load(self, audio: AudioInput, reporter: JobReporter) -> DecodedAudio:
        if not self._backends:
            ensure_any_backend()
        reporter.started(EventStage.AUDIO_LOAD, f"Loading {audio.original_filename}")
        errors: list[str] = []
        for backend in self._backends:
            try:
                decoded = backend.decode(audio.path)
                reporter.info(
                    EventStage.AUDIO_LOAD,
                    f"Decoded with {backend.name} "
                    f"({decoded.sample_rate} Hz, {decoded.channels} ch, "
                    f"{len(decoded.signal)/decoded.sample_rate:.2f}s)",
                    backend=backend.name,
                )
                return decoded
            except Exception as exc:
                errors.append(f"{backend.name}: {exc}")
                continue
        raise AudioUnreadableError(
            f"Could not decode audio: {audio.original_filename}",
            technical_detail=" | ".join(errors),
        )


def to_mono(signal: np.ndarray) -> np.ndarray:
    """Average channels.  Accepts (T,) or (T, C)."""
    if signal.ndim == 1:
        return signal
    if signal.ndim == 2:
        return signal.mean(axis=1)
    raise ValueError(f"Unexpected signal shape {signal.shape}; expected 1-D or 2-D")


class Resampler:
    """Resample mono audio to ``target_sr`` using soxr or a numpy fallback."""

    def __init__(self, target_sr: int = BeatThisSpec.SAMPLE_RATE) -> None:
        self.target_sr = target_sr
        try:
            import soxr

            self._soxr = soxr
        except Exception:  # noqa: BLE001
            self._soxr = None

    def resample(self, signal: np.ndarray, sr: int) -> tuple[np.ndarray, bool]:
        if sr == self.target_sr:
            return signal.astype(np.float32, copy=False), False
        if self._soxr is not None:
            out = self._soxr.resample(signal, sr, self.target_sr)
            return np.asarray(out, dtype=np.float32), True
        # Numpy linear-interpolation fallback (not ideal, but functional).
        duration = len(signal) / sr
        new_len = int(round(duration * self.target_sr))
        old_positions = np.linspace(0.0, duration, num=len(signal), endpoint=False)
        new_positions = np.linspace(0.0, duration, num=new_len, endpoint=False)
        out = np.interp(new_positions, old_positions, signal).astype(np.float32)
        return out, True


class AudioService:
    """High-level façade: probe → load → mono → resample → AudioData."""

    def __init__(
        self,
        runtime: RuntimeConfig,
        prober: AudioProber | None = None,
        loader: AudioLoader | None = None,
        resampler: Resampler | None = None,
    ) -> None:
        self.runtime = runtime
        self.prober = prober or AudioProber()
        self.loader = loader or AudioLoader()
        self.resampler = resampler or Resampler(BeatThisSpec.SAMPLE_RATE)

    def probe(self, audio: AudioInput) -> AudioProbe:
        return self.prober.probe(audio)

    def load_prepared(
        self, audio: AudioInput, probe: AudioProbe, reporter: JobReporter
    ) -> AudioData:
        t0 = time.perf_counter()

        if probe.duration_sec < self.runtime.min_audio_seconds:
            raise AudioTooShortError(
                f"Audio is too short ({probe.duration_sec:.2f}s); "
                f"minimum is {self.runtime.min_audio_seconds:.2f}s.",
                technical_detail=f"duration={probe.duration_sec}",
                recoverable=False,
            )

        decoded = self.loader.load(audio, reporter)
        reporter.completed(
            EventStage.AUDIO_LOAD,
            f"Decoded {len(decoded.signal)} samples",
        )

        reporter.started(EventStage.NORMALIZE, "Mixing down to mono")
        mono = to_mono(decoded.signal)
        reporter.completed(EventStage.NORMALIZE, "Mono mixdown complete")

        reporter.started(
            EventStage.RESAMPLE,
            f"Target sample rate {self.resampler.target_sr} Hz",
        )
        try:
            resampled, did_resample = self.resampler.resample(
                mono, decoded.sample_rate
            )
        except Exception as exc:
            raise wrap_exception(
                exc, stage="resample", message="Resampling failed"
            ) from exc
        if did_resample:
            reporter.info(
                EventStage.RESAMPLE,
                f"Resampled {decoded.sample_rate} → {self.resampler.target_sr}",
            )
        else:
            reporter.info(EventStage.RESAMPLE, "Sample rate already matches target")
        reporter.completed(EventStage.RESAMPLE)

        duration = len(resampled) / self.resampler.target_sr
        return AudioData(
            signal=resampled,
            sample_rate=self.resampler.target_sr,
            original_sr=decoded.sample_rate,
            channels=decoded.channels,
            duration_sec=duration,
            resampled=did_resample,
        )
