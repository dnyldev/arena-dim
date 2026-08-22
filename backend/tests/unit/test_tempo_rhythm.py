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


def test_tempo_curve_constant_tempo():
    # 40 beats at exactly 120 BPM -> every curve point should read ~120.
    beats = [i * 0.5 for i in range(40)]
    t = TempoAnalyzer().analyze(beats)
    assert t.curve_window_beats == 8
    assert len(t.curve) > 0
    for point in t.curve:
        assert math.isclose(point.bpm, 120.0, rel_tol=1e-6)
        assert 0.0 <= point.time_sec <= beats[-1]
    # Curve timestamps should be non-decreasing (windows slide forward).
    times = [p.time_sec for p in t.curve]
    assert times == sorted(times)


def test_tempo_curve_detects_tempo_change():
    # First half at 120 BPM (0.5s IBI), second half at 150 BPM (0.4s IBI).
    first = [i * 0.5 for i in range(20)]
    second_start = first[-1] + 0.4
    second = [second_start + i * 0.4 for i in range(20)]
    beats = first + second
    t = TempoAnalyzer(curve_window_beats=6).analyze(beats)
    assert len(t.curve) > 0
    early_bpms = [p.bpm for p in t.curve if p.time_sec < first[-1] - 1.0]
    late_bpms = [p.bpm for p in t.curve if p.time_sec > second[0] + 1.0]
    assert early_bpms and late_bpms
    assert math.isclose(sum(early_bpms) / len(early_bpms), 120.0, rel_tol=0.05)
    assert math.isclose(sum(late_bpms) / len(late_bpms), 150.0, rel_tol=0.05)


def test_tempo_curve_short_beat_list_still_yields_a_point():
    # Fewer beats than the default window (8) — should fall back to a
    # single overall-estimate point instead of an empty curve.
    beats = [0.0, 0.5, 1.0]
    t = TempoAnalyzer().analyze(beats)
    assert t.bpm is not None
    assert len(t.curve) == 1
    assert math.isclose(t.curve[0].bpm, 120.0, rel_tol=1e-6)


def test_tempo_curve_empty_for_insufficient_beats():
    assert TempoAnalyzer().analyze([]).curve == ()
    assert TempoAnalyzer().analyze([0.5]).curve == ()
