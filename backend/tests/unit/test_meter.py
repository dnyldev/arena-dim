import math

from app.analysis.meter import MeterAnalyzer
from app.domain.models import ValueOrigin


def test_meter_steady_four_four():
    # 4 beats per bar, 6 bars.
    beats = [i * 0.5 for i in range(24)]
    downs = [beats[i] for i in range(0, 24, 4)]
    m = MeterAnalyzer().analyze(beats, downs)
    assert m.beats_per_bar == 4
    assert m.origin == ValueOrigin.ESTIMATED
    assert m.method == "downbeat_interval_mode"
    assert m.confidence == 1.0
    assert m.is_stable is True
    assert m.per_bar == (4, 4, 4, 4, 4)


def test_meter_steady_three_four():
    beats = [i * 0.5 for i in range(18)]
    downs = [beats[i] for i in range(0, 18, 3)]
    m = MeterAnalyzer().analyze(beats, downs)
    assert m.beats_per_bar == 3
    assert math.isclose(m.confidence, 1.0)
    assert m.is_stable is True


def test_meter_mixed_bars_reports_mode_and_lower_confidence():
    # Mostly 4/4 with one irregular 3-beat bar thrown in.
    beats = [i * 0.5 for i in range(20)]
    # Bars: 4,4,3,4,4 beats (downbeats at indices 0,4,8,11,15,19)
    down_idx = [0, 4, 8, 11, 15, 19]
    downs = [beats[i] for i in down_idx]
    m = MeterAnalyzer().analyze(beats, downs)
    assert m.beats_per_bar == 4
    assert m.per_bar == (4, 4, 3, 4, 4)
    assert m.confidence == 4 / 5
    assert m.is_stable is False


def test_meter_insufficient_downbeats():
    m = MeterAnalyzer().analyze([0.0, 0.5, 1.0], [0.0])
    assert m.beats_per_bar is None
    assert m.confidence is None
    assert m.per_bar == ()


def test_meter_no_beats():
    m = MeterAnalyzer().analyze([], [])
    assert m.beats_per_bar is None


def test_meter_ignores_implausible_bar_lengths():
    # One bar spans an implausible 40 beats (beat-tracking glitch);
    # the rest are steady 4/4. The glitch shouldn't determine the mode.
    beats = [i * 0.5 for i in range(4 + 40 + 4 + 4)]
    downs = [beats[0], beats[4], beats[44], beats[48]]
    m = MeterAnalyzer().analyze(beats, downs)
    assert m.beats_per_bar == 4
