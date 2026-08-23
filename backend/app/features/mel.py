"""Log-mel spectrogram extraction.

The parameters here are **fixed** by the Beat This! weights and are
mirrored exactly from the research package:

    sample_rate     = 22050
    n_fft           = 1024
    hop_length      = 441   (→ 50 fps)
    f_min           = 30
    f_max           = 11000
    n_mels          = 128
    mel_scale       = "slaney"
    normalized      = "frame_length"
    power           = 1.0
    log_multiplier  = 1000
    transform       = log1p(multiplier * mel)

We use ``torchaudio.transforms.MelSpectrogram`` directly (CPU) so the
output is numerically identical to the reference implementation.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from app.core.config import BeatThisSpec
from app.core.errors import DependencyMissingError
from app.domain.models import AudioData, Spectrogram
from app.events import EventStage, JobReporter


class LogMelSpectrogram:
    def __init__(self, device: str = "cpu") -> None:
        self.device = device
        try:
            import torch
            import torchaudio
        except Exception as exc:  # noqa: BLE001
            raise DependencyMissingError(
                "Feature extraction requires torch and torchaudio. "
                "Install CPU wheels: pip install torch torchaudio "
                "--index-url https://download.pytorch.org/whl/cpu",
                stage="feature_extraction",
                technical_detail=f"{type(exc).__name__}: {exc}",
                recoverable=True,
            ) from exc
        self._torch = torch
        self._transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=BeatThisSpec.SAMPLE_RATE,
            n_fft=BeatThisSpec.N_FFT,
            hop_length=BeatThisSpec.HOP_LENGTH,
            f_min=BeatThisSpec.F_MIN,
            f_max=BeatThisSpec.F_MAX,
            n_mels=BeatThisSpec.N_MELS,
            mel_scale=BeatThisSpec.MEL_SCALE,
            normalized=BeatThisSpec.MEL_NORM,
            power=BeatThisSpec.POWER,
        ).to(device)

    def extract(
        self, audio: AudioData, reporter: JobReporter
    ) -> Spectrogram:
        reporter.started(
            EventStage.FEATURE_EXTRACTION,
            f"Computing log-mel spectrogram ({BeatThisSpec.N_MELS} mels)",
        )
        t0 = time.perf_counter()
        torch = self._torch
        signal = audio.signal
        if not isinstance(signal, torch.Tensor):
            wav = torch.tensor(np.asarray(signal, dtype=np.float32), device=self.device)
        else:
            wav = signal.to(self.device)
        if wav.ndim == 1:
            wav = wav.unsqueeze(0)  # (1, T)

        with torch.inference_mode():
            mel = self._transform(wav)  # (1, n_mels, T)
            mel = torch.log1p(BeatThisSpec.LOG_MULTIPLIER * mel)
            # Beat This! uses (T, n_mels) after a .T transpose.
            mel = mel.squeeze(0).T.contiguous()
        arr = mel.cpu().numpy().astype(np.float32, copy=False)
        elapsed = (time.perf_counter() - t0) * 1000
        reporter.completed(
            EventStage.FEATURE_EXTRACTION,
            f"Spectrogram shape {arr.shape}",
            elapsed_ms=elapsed,
            shape=list(arr.shape),
            fps=BeatThisSpec.fps(),
        )
        return Spectrogram(
            data=arr,
            sample_rate=BeatThisSpec.SAMPLE_RATE,
            hop_length=BeatThisSpec.HOP_LENGTH,
            n_mels=BeatThisSpec.N_MELS,
        )
