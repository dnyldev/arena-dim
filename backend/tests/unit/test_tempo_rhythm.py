import math

from app.analysis.rhythm import RhythmAnalyzer
from app.analysis.tempo import TempoAnalyzer
from app.domain.models import ValueOrigin


def test_tempo_median_ibi_120bpm():
    # Beats every 0.5 s → 120 BPM
    beats = [i * 0.5 for i in range(20)]
    t = TempoAnalyzer().analyze(beats)
    assert t.bpm is not None
    assert math.isclose(t.bpm, 120.0, rel_tol=1e-6)
    assert t.origin == ValueOrigin.DERIVED
    assert t.method == "median_ibi"
    assert math.isclose(t.median_ibi_sec, 0.5, rel_tol=1e-6)


def test_tempo_insufficient_beats():
    assert TempoAnalyzer().analyze([]).bpm is None
    assert TempoAnalyzer().analyze([0.5]).bpm is None


def test_tempo_filters_zero_intervals():
    beats = [0.0, 0.5, 0.5, 1.0]
    t = TempoAnalyzer().analyze(beats)
    assert t.bpm is not None
    assert math.isclose(t.bpm, 120.0, rel_tol=1e-6)


def test_rhythm_density():
    beats = [0.5 * i for i in range(20)]
    r = RhythmAnalyzer().analyze(beats, duration_sec=10.0)
    assert r.beat_density_beats_per_second == 2.0
    assert r.mean_inter_beat_interval_sec is not None
    assert abs(r.mean_inter_beat_interval_sec - 0.5) < 1e-9
    assert r.std_inter_beat_interval_sec == 0.0
    assert r.irregularity == 0.0
