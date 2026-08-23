import numpy as np

from app.events import JobReporter
from app.events.bus import EventBus
from app.postprocess import MinimalPeakPostProcessor, deduplicate_peaks
from app.engines.base import EngineFrameOutput


def _reporter():
    return JobReporter("test", EventBus())


def test_deduplicate_peaks_adjacent():
    peaks = np.array([10, 11, 20, 21, 22], dtype=np.int64)
    out = deduplicate_peaks(peaks, width=1)
    # Adjacent peaks get merged into one.
    assert len(out) < len(peaks)
    assert 20 in out or np.isclose(out, 21).any()


def test_minimal_peak_picker_finds_clear_peaks():
    fps = 50.0
    T = 500  # 10 s
    beat = np.full(T, -5.0, dtype=np.float32)
    down = np.full(T, -5.0, dtype=np.float32)
    # Beats at frame 50, 100, 150, ... (1 s apart → 60 BPM)
    for f in [50, 100, 150, 200, 250, 300, 350, 400, 450]:
        beat[f] = 10.0
    # Downbeats every 2 s.
    for f in [100, 200, 300, 400]:
        down[f] = 10.0
    fo = EngineFrameOutput(
        beat_logits=beat,
        downbeat_logits=down,
        fps=fps,
        n_frames=T,
        engine_name="test",
        checkpoint="test",
    )
    result = MinimalPeakPostProcessor().process(fo, _reporter())
    expected_beats = np.array([50, 100, 150, 200, 250, 300, 350, 400, 450]) / fps
    np.testing.assert_allclose(result.beats, expected_beats, atol=1e-6)
    # Downbeats snap to beats.
    expected_downs = np.array([100, 200, 300, 400]) / fps
    np.testing.assert_allclose(result.downbeats, expected_downs, atol=1e-6)
    # Downbeats must be a subset of beats.
    for d in result.downbeats:
        assert np.any(np.isclose(result.beats, d))


def test_no_peaks_when_all_negative():
    T = 100
    logits = np.full(T, -2.0, dtype=np.float32)
    fo = EngineFrameOutput(
        beat_logits=logits,
        downbeat_logits=logits,
        fps=50.0,
        n_frames=T,
        engine_name="test",
        checkpoint="test",
    )
    result = MinimalPeakPostProcessor().process(fo, _reporter())
    assert len(result.beats) == 0
    assert len(result.downbeats) == 0
