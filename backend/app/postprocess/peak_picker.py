"""Beat / downbeat postprocessing.

The :class:`PostProcessor` is a swappable stage between the neural
engine and the final result.  Two implementations are provided:

* :class:`MinimalPeakPostProcessor` — the paper's default, no DBN.
  Exact algorithm from ``beat_this/model/postprocessor.py``:
    1. stack beat/downbeat logits → (T, 2)
    2. max-pool with kernel=7, stride=1, padding=3
    3. keep positions equal to the local max AND logit > 0
    4. deduplicate adjacent peaks (running mean, width=1)
    5. frames → seconds (t = frame / fps)
    6. snap every downbeat to the nearest beat time
    7. np.unique the downbeat array

* :class:`DBNPostProcessor` — optional; requires ``madmom`` from
  ``git+https://github.com/CPJKU/madmom.git``.  Raises a clear error if
  the dependency is missing rather than silently falling back.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np

from app.core.config import BeatThisSpec
from app.core.errors import DependencyMissingError, PostProcessingError
from app.domain.models import BeatEngineRawResult
from app.engines.base import EngineFrameOutput
from app.events import EventStage, JobReporter


@runtime_checkable
class PostProcessor(Protocol):
    name: str

    def process(
        self, frame_output: EngineFrameOutput, reporter: JobReporter
    ) -> BeatEngineRawResult: ...


def deduplicate_peaks(peaks: np.ndarray, width: int = 1) -> np.ndarray:
    """Merge adjacent peaks by running mean.

    Direct port of ``deduplicate_peaks`` in
    ``beat_this/model/postprocessor.py``.
    """
    if len(peaks) == 0:
        return peaks.astype(np.int64)
    peaks = np.asarray(peaks, dtype=np.int64)
    to_keep = np.ones(len(peaks), dtype=bool)
    for i in range(1, len(peaks)):
        if peaks[i] - peaks[i - 1] <= width:
            # Replace this peak index with the midpoint and drop the
            # previous one.  This matches the reference cumulative mean.
            peaks[i] = int(round((peaks[i - 1] * i + peaks[i]) / (i + 1)))
            to_keep[i - 1] = False
    return peaks[to_keep]


def _peak_indices(logits: np.ndarray, pool_kernel: int) -> np.ndarray:
    """Return frame indices that are local maxima above zero.

    Pure-numpy 1-D max-pool so this stage does not require torch.  The
    result is identical to ``F.max_pool1d(kernel=7, stride=1, padding=3)``
    for a 1-D signal: each output position holds the maximum over a
    centered window of ``pool_kernel`` frames, with zero padding at the
    edges.
    """
    x = np.asarray(logits, dtype=np.float32).reshape(-1)
    n = x.shape[0]
    if n == 0:
        return np.array([], dtype=np.int64)
    pad = pool_kernel // 2
    padded = np.concatenate(
        [np.full(pad, -np.inf, dtype=np.float32), x, np.full(pad, -np.inf, dtype=np.float32)]
    )
    # Sliding-window max.
    windows = np.lib.stride_tricks.sliding_window_view(padded, pool_kernel)
    pooled = windows.max(axis=-1)[:n]
    mask = (x == pooled) & (x > BeatThisSpec.PEAK_THRESHOLD_LOGIT)
    return np.nonzero(mask)[0].astype(np.int64)


class MinimalPeakPostProcessor:
    """The paper's default postprocessor (no DBN)."""

    name = "minimal"

    def __init__(self, pool_kernel: int = BeatThisSpec.PEAK_POOL_KERNEL) -> None:
        self.pool_kernel = pool_kernel

    def process(
        self, frame_output: EngineFrameOutput, reporter: JobReporter
    ) -> BeatEngineRawResult:
        reporter.started(
            EventStage.POSTPROCESS,
            f"Minimal peak picking (kernel={self.pool_kernel})",
        )
        try:
            beat_frames = _peak_indices(frame_output.beat_logits, self.pool_kernel)
            down_frames = _peak_indices(
                frame_output.downbeat_logits, self.pool_kernel
            )

            beat_frames = deduplicate_peaks(beat_frames, width=1)
            down_frames = deduplicate_peaks(down_frames, width=1)

            beat_times = (beat_frames / frame_output.fps).astype(np.float64)
            down_times = (down_frames / frame_output.fps).astype(np.float64)

            # Snap every downbeat to the nearest beat time, then unique.
            if len(beat_times) > 0 and len(down_times) > 0:
                idx = np.argmin(
                    np.abs(beat_times[None, :] - down_times[:, None]), axis=1
                )
                down_times = beat_times[idx]
                down_times = np.unique(down_times)
            else:
                down_times = np.array([], dtype=np.float64)

            beat_times = np.sort(beat_times)
        except Exception as exc:
            raise PostProcessingError(
                f"Minimal postprocessing failed: {exc}",
                technical_detail=str(exc),
            ) from exc

        reporter.completed(
            EventStage.POSTPROCESS,
            f"{len(beat_times)} beats, {len(down_times)} downbeats",
            beats=int(len(beat_times)),
            downbeats=int(len(down_times)),
        )
        return BeatEngineRawResult(
            beats=beat_times,
            downbeats=down_times,
            beat_logits=frame_output.beat_logits,
            downbeat_logits=frame_output.downbeat_logits,
            fps=frame_output.fps,
            postprocessor=self.name,
            engine_name=frame_output.engine_name,
            checkpoint=frame_output.checkpoint,
        )


class DBNPostProcessor:
    """Optional DBN post-processor (requires madmom).

    Mirrors ``beat_this.model.postprocessor.PostProcessor`` with
    ``type='dbn'``.  If ``madmom`` is not importable, raises
    :class:`DependencyMissingError` with an actionable message.
    """

    name = "dbn"

    def __init__(
        self,
        beats_per_bar: tuple[int, ...] = BeatThisSpec.DBN_BEATS_PER_BAR,
        min_bpm: float = BeatThisSpec.DBN_MIN_BPM,
        max_bpm: float = BeatThisSpec.DBN_MAX_BPM,
        transition_lambda: float = BeatThisSpec.DBN_TRANSITION_LAMBDA,
        fps: float = BeatThisSpec.fps(),
    ) -> None:
        self.beats_per_bar = list(beats_per_bar)
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm
        self.transition_lambda = transition_lambda
        self.fps = fps
        self._dbn = None

    def _ensure_dbn(self) -> Any:
        if self._dbn is not None:
            return self._dbn
        try:
            from madmom.features.downbeats import DBNDownBeatTrackingProcessor
        except Exception as exc:
            raise DependencyMissingError(
                "DBN postprocessing requires the CPJKU madmom fork. "
                "Install it with: pip install git+https://github.com/CPJKU/madmom.git",
                technical_detail=f"{type(exc).__name__}: {exc}",
                recoverable=True,
            ) from exc
        self._dbn = DBNDownBeatTrackingProcessor(
            beats_per_bar=self.beats_per_bar,
            min_bpm=self.min_bpm,
            max_bpm=self.max_bpm,
            fps=self.fps,
            transition_lambda=self.transition_lambda,
        )
        return self._dbn

    def process(
        self, frame_output: EngineFrameOutput, reporter: JobReporter
    ) -> BeatEngineRawResult:
        reporter.started(EventStage.POSTPROCESS, "DBN postprocessing (madmom)")
        import torch

        dbn = self._ensure_dbn()
        beat = torch.tensor(frame_output.beat_logits, dtype=torch.float32)
        down = torch.tensor(frame_output.downbeat_logits, dtype=torch.float32)
        beat_prob = torch.sigmoid(beat).numpy()
        down_prob = torch.sigmoid(down).numpy()
        eps = 1e-4
        # Combined activation as in the reference: [max(beat-down, eps), down]
        act = np.stack(
            [np.maximum(beat_prob - down_prob, eps), down_prob], axis=1
        )
        act = np.clip(act, eps, 1.0 - eps)
        try:
            result = dbn(act)
        except Exception as exc:
            raise PostProcessingError(
                f"DBN processing failed: {exc}", technical_detail=str(exc)
            ) from exc
        # result is (N, 2): [time, beat_position]; position 1 = downbeat.
        times = result[:, 0].astype(np.float64)
        positions = result[:, 1].astype(int)
        beat_times = times
        down_times = times[positions == 1]
        reporter.completed(
            EventStage.POSTPROCESS,
            f"{len(beat_times)} beats, {len(down_times)} downbeats (DBN)",
            beats=int(len(beat_times)),
            downbeats=int(len(down_times)),
        )
        return BeatEngineRawResult(
            beats=beat_times,
            downbeats=down_times,
            beat_logits=frame_output.beat_logits,
            downbeat_logits=frame_output.downbeat_logits,
            fps=frame_output.fps,
            postprocessor=self.name,
            engine_name=frame_output.engine_name,
            checkpoint=frame_output.checkpoint,
        )


def build_postprocessor(dbn: bool) -> PostProcessor:
    return DBNPostProcessor() if dbn else MinimalPeakPostProcessor()
