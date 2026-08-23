"""Pytest fixtures.

Tests run WITHOUT model weights and WITHOUT requiring the beat-this
package.  The conftest installs a mock engine so the full orchestrator
and API can be exercised deterministically.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

# Ensure backend package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import BeatThisSpec, RuntimeConfig, set_runtime  # noqa: E402
from app.domain.models import AudioData, Spectrogram  # noqa: E402
from app.engines.base import (  # noqa: E402
    EngineCapabilities,
    EngineFrameOutput,
    EngineInfo,
    EngineStatus,
)
from app.events import EventStage  # noqa: E402
from app.events.bus import reset_event_bus  # noqa: E402


@pytest.fixture
def runtime(tmp_path: Path) -> RuntimeConfig:
    rt = RuntimeConfig(
        data_dir=tmp_path / "data",
        upload_dir=tmp_path / "data" / "uploads",
        artifact_dir=tmp_path / "data" / "artifacts",
        checkpoint_dir=tmp_path / "data" / "checkpoints",
        allow_model_download=False,
        max_concurrent_analyses=1,
        job_queue_max=4,
    )
    set_runtime(rt)
    reset_event_bus()
    return rt


@pytest.fixture
def sine_wav(tmp_path: Path) -> Path:
    """Generate a 2-second 440 Hz sine WAV file for audio-pipeline tests."""
    try:
        import soundfile as sf
    except ImportError:
        pytest.skip("soundfile required for audio tests")
    sr = 22050
    t = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
    signal = 0.3 * np.sin(2 * np.pi * 440.0 * t)
    p = tmp_path / "sine.wav"
    sf.write(str(p), signal.astype(np.float32), sr)
    return p


@pytest.fixture
def sine_wav_long(tmp_path: Path) -> Path:
    """A longer (10 s) sine WAV, giving the mock engine enough beats and
    downbeats (5 bars of 4/4) for the tempo curve and meter estimator to
    have something meaningful to compute over.
    """
    try:
        import soundfile as sf
    except ImportError:
        pytest.skip("soundfile required for audio tests")
    sr = 22050
    duration = 10.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    signal = 0.3 * np.sin(2 * np.pi * 440.0 * t)
    p = tmp_path / "sine_long.wav"
    sf.write(str(p), signal.astype(np.float32), sr)
    return p


class MockBeatEngine:
    """Deterministic engine: emits peaks at known times.

    Places a beat every 0.5 s (120 BPM) and a downbeat every 2 s,
    synthesised as gaussian logits so the peak picker finds them.
    """

    name = "mock"
    display_name = "Mock Engine"
    version = "0.0"

    def __init__(self, checkpoint: str = "mock", **kw) -> None:
        self.checkpoint = checkpoint
        self._status = EngineStatus.READY

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(
            name=self.name,
            display_name=self.display_name,
            version=self.version,
            device="cpu",
            status=self._status,
            checkpoint=self.checkpoint,
            checkpoint_available=True,
            capabilities=EngineCapabilities(),
        )

    def load(self) -> None:  # pragma: no cover
        self._status = EngineStatus.READY

    def unload(self) -> None:  # pragma: no cover
        self._status = EngineStatus.UNLOADED

    def infer_frames(self, spectrogram: Spectrogram, reporter) -> EngineFrameOutput:
        from app.events import EventStage

        reporter.started(EventStage.MODEL_LOAD, "Loading mock model")
        reporter.completed(EventStage.MODEL_LOAD, "mock model ready")
        reporter.started(
            EventStage.INFERENCE, "Running mock inference", n_chunks=1
        )
        T = spectrogram.n_frames
        fps = spectrogram.fps
        beat = np.full(T, -5.0, dtype=np.float32)
        down = np.full(T, -5.0, dtype=np.float32)
        # Beats at 0.5, 1.0, 1.5, 2.0... s; downbeats every 2 s.
        beat_times = np.arange(0.5, T / fps, 0.5)
        down_times = np.arange(0.0, T / fps, 2.0)
        for t in beat_times:
            f = int(round(t * fps))
            if 0 <= f < T:
                beat[f] = 8.0
        for t in down_times:
            f = int(round(t * fps))
            if 0 <= f < T:
                down[f] = 8.0
        reporter.completed(EventStage.INFERENCE, "mock inference done")
        return EngineFrameOutput(
            beat_logits=beat,
            downbeat_logits=down,
            fps=fps,
            n_frames=T,
            engine_name=self.name,
            checkpoint=self.checkpoint,
        )


@pytest.fixture
def mock_engine(monkeypatch):
    """Patch the engine factory so all analyses use MockBeatEngine."""
    from app.engines import factory as factory_mod
    from app.analysis import orchestrator as orch_mod

    def _factory(config, runtime, manager=None):
        return MockBeatEngine(checkpoint=config.checkpoint)

    monkeypatch.setattr(factory_mod, "create_engine", _factory)
    monkeypatch.setattr(orch_mod, "create_engine", _factory)
    return MockBeatEngine


class StubFeatureExtractor:
    """Deterministic zero spectrogram — avoids requiring torch in tests."""

    def __init__(self, device: str = "cpu") -> None:
        self.device = device

    def extract(self, audio, reporter):
        reporter.started(EventStage.FEATURE_EXTRACTION, "Stub spectrogram")
        n_frames = int(
            np.ceil(
                len(audio.signal)
                / BeatThisSpec.HOP_LENGTH
            )
        )
        data = np.zeros((n_frames, BeatThisSpec.N_MELS), dtype=np.float32)
        reporter.completed(
            EventStage.FEATURE_EXTRACTION,
            f"Stub spectrogram shape {data.shape}",
            shape=list(data.shape),
        )
        return Spectrogram(
            data=data,
            sample_rate=BeatThisSpec.SAMPLE_RATE,
            hop_length=BeatThisSpec.HOP_LENGTH,
            n_mels=BeatThisSpec.N_MELS,
        )


@pytest.fixture
def stub_features(monkeypatch):
    """Replace LogMelSpectrogram with the no-torch stub."""
    from app.analysis import orchestrator as orch_mod

    monkeypatch.setattr(orch_mod, "LogMelSpectrogram", StubFeatureExtractor)
    return StubFeatureExtractor
