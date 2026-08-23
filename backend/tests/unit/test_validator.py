import numpy as np
import pytest

from app.analysis.validator import BeatValidator
from app.core.errors import ValidationError
from app.domain.models import AudioProbe, BeatEngineRawResult


def _raw(beats, downbeats):
    return BeatEngineRawResult(
        beats=np.asarray(beats, dtype=np.float64),
        downbeats=np.asarray(downbeats, dtype=np.float64),
    )


def _audio(duration=10.0):
    return AudioProbe(duration_sec=duration, sample_rate=44100, channels=2)


def test_clean_result_passes():
    beats = [0.5, 1.0, 1.5, 2.0]
    downs = [0.5, 1.5]
    report = BeatValidator().validate(_raw(beats, downs), _audio(10))
    assert report.ok


def test_nan_fails():
    raw = _raw([0.5, float("nan"), 1.5], [0.5])
    with pytest.raises(ValidationError):
        BeatValidator().validate(raw, _audio(10))


def test_negative_fails():
    with pytest.raises(ValidationError):
        BeatValidator().validate(_raw([-0.1, 0.5], [0.5]), _audio(10))


def test_unsorted_fails():
    with pytest.raises(ValidationError):
        BeatValidator().validate(_raw([1.0, 0.5], [0.5]), _audio(10))


def test_downbeat_not_subset_fails():
    with pytest.raises(ValidationError):
        BeatValidator().validate(_raw([0.5, 1.0, 1.5], [0.75]), _audio(10))


def test_out_of_duration_fails():
    with pytest.raises(ValidationError):
        BeatValidator().validate(_raw([0.5, 10.5], [0.5]), _audio(10))


def test_empty_result_is_info_not_error():
    report = BeatValidator().validate(_raw([], []), _audio(10))
    assert report.ok
    assert any(i.code == "empty_result" for i in report.issues)
