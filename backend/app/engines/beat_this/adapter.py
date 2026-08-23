"""Beat This! engine adapter.

This is the **only** module in the application that imports or
references ``beat_this`` beyond the model manager.  It implements the
:class:`~app.engines.base.BeatEngine` protocol:

* spectrogram in → per-frame beat/downbeat logits out,
* chunked inference with progress events,
* model acquired from :class:`BeatThisModelManager`,
* device locked to CPU,
* optional float16 autocast.

It does NOT peak-pick, compute tempo, write files, or know about HTTP.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from app.core.config import BeatThisSpec
from app.core.errors import InferenceError, wrap_exception
from app.domain.models import Spectrogram
from app.engines.base import (
    EngineCapabilities,
    EngineFrameOutput,
    EngineInfo,
    EngineStatus,
)
from app.engines.beat_this.chunking import aggregate_prediction, split_piece
from app.engines.beat_this.manager import BeatThisModelManager
from app.events import EventStage, JobReporter


class BeatThisAdapter:
    """Adapter around the Beat This! neural network."""

    name = "beat_this"
    display_name = "Beat This!"
    version = "1.1.0"

    def __init__(
        self,
        checkpoint: str,
        manager: BeatThisModelManager,
        *,
        float16: bool = False,
    ) -> None:
        self.checkpoint = checkpoint
        self.manager = manager
        self.float16 = bool(float16)
        self.device = manager.runtime.device
        if self.device != "cpu":
            # CPU-only is non-negotiable in this build.
            self.device = "cpu"

    # -- BeatEngine protocol --------------------------------------------- #

    @property
    def info(self) -> EngineInfo:
        mi = self.manager.model_info(self.checkpoint)
        status = EngineStatus(mi["engine_status"])
        if not mi["beat_this_installed"] and status == EngineStatus.UNLOADED:
            status = EngineStatus.UNAVAILABLE
        return EngineInfo(
            name=self.name,
            display_name=self.display_name,
            version=self.version,
            device=self.device,
            status=status,
            checkpoint=self.checkpoint,
            checkpoint_available=bool(mi["weights_available"]),
            capabilities=EngineCapabilities(
                produces_beats=True,
                produces_downbeats=True,
                produces_activations=True,
                supports_dbn=False,  # DBN lives in the postprocessor, not here
                supports_half_precision=True,
                cpu_only=True,
            ),
            load_error=mi.get("load_error") or mi.get("import_error"),
            metadata={
                "transformer_dim": mi.get("transformer_dim"),
                "is_small": mi.get("is_small"),
                "local_path": mi.get("local_path"),
                "weights_source": mi.get("weights_source"),
            },
        )

    def load(self) -> None:
        self.manager.get_model(self.checkpoint)

    def unload(self) -> None:
        self.manager.unload(self.checkpoint)

    def infer_frames(
        self,
        spectrogram: Spectrogram,
        reporter: JobReporter,
    ) -> EngineFrameOutput:
        if spectrogram.n_mels != BeatThisSpec.N_MELS:
            raise InferenceError(
                f"Expected {BeatThisSpec.N_MELS} mel bins, got {spectrogram.n_mels}",
                technical_detail="Spectrogram does not match model input spec",
            )

        reporter.started(
            EventStage.MODEL_LOAD, f"Loading model {self.checkpoint}"
        )
        t_load = time.perf_counter()
        model = self.manager.get_model(self.checkpoint)
        self.manager.mark_in_use(self.checkpoint)
        load_ms = (time.perf_counter() - t_load) * 1000.0
        source = self.manager.entry(self.checkpoint).source
        reporter.completed(
            EventStage.MODEL_LOAD,
            f"Model ready (source={source})",
            elapsed_ms=load_ms,
            source=source,
            device=self.device,
            float16=self.float16,
        )

        try:
            return self._run_inference(model, spectrogram, reporter)
        finally:
            self.manager.mark_idle(self.checkpoint)

    # -- internals -------------------------------------------------------- #

    def _run_inference(
        self,
        model: Any,
        spectrogram: Spectrogram,
        reporter: JobReporter,
    ) -> EngineFrameOutput:
        import torch

        data = spectrogram.data
        if not isinstance(data, np.ndarray):
            data = np.asarray(data)
        length = int(data.shape[0])

        chunks = split_piece(length)
        reporter.started(
            EventStage.INFERENCE,
            f"Running inference over {len(chunks)} chunk(s) "
            f"({length} frames @ {spectrogram.fps:.0f} fps)",
            n_chunks=len(chunks),
            n_frames=length,
            chunk_size=BeatThisSpec.CHUNK_SIZE,
        )
        t_inf = time.perf_counter()

        beat_preds: list[np.ndarray] = []
        down_preds: list[np.ndarray] = []
        use_amp = self.float16 and self.device != "cpu"
        # On CPU, torch.autocast is largely a no-op; we still honor the
        # flag but never crash.
        autocast_device = "cpu"

        try:
            for i, chunk in enumerate(chunks):
                block = data[chunk.input_start : chunk.input_end]
                tensor = torch.tensor(block, dtype=torch.float32, device=self.device)
                tensor = tensor.unsqueeze(0)  # (1, T, 128)

                with torch.inference_mode():
                    if self.float16:
                        with torch.autocast(
                            device_type=autocast_device, enabled=True, dtype=torch.float16
                        ):
                            out = model(tensor)
                    else:
                        out = model(tensor)

                beat_preds.append(out["beat"].squeeze(0).detach().float().cpu().numpy())
                down_preds.append(
                    out["downbeat"].squeeze(0).detach().float().cpu().numpy()
                )

                reporter.progress(
                    EventStage.INFERENCE,
                    (i + 1) / len(chunks),
                    f"Chunk {i + 1}/{len(chunks)}",
                    chunk=i + 1,
                    total=len(chunks),
                )
        except Exception as exc:
            raise wrap_exception(
                exc, stage="inference", message="Neural inference failed"
            ) from exc

        beat_full = aggregate_prediction(
            chunks, beat_preds, length, overlap_mode=BeatThisSpec.OVERLAP_MODE
        )
        down_full = aggregate_prediction(
            chunks, down_preds, length, overlap_mode=BeatThisSpec.OVERLAP_MODE
        )

        elapsed = (time.perf_counter() - t_inf) * 1000.0
        reporter.completed(
            EventStage.INFERENCE,
            f"Inference complete ({elapsed:.0f} ms)",
            elapsed_ms=elapsed,
        )

        return EngineFrameOutput(
            beat_logits=beat_full.astype(np.float32),
            downbeat_logits=down_full.astype(np.float32),
            fps=float(spectrogram.fps),
            n_frames=length,
            engine_name=self.name,
            checkpoint=self.checkpoint,
        )
