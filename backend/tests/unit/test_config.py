from app.core.config import AnalysisConfig, BeatThisSpec
from app.core.errors import ConfigurationError, UnsupportedParameterError


def test_fps_exact():
    assert BeatThisSpec.fps() == 50.0


def test_seconds_frame_round_trip():
    # Round-trip is only exact to within half a frame (10 ms at 50 fps).
    for s in [0.0, 0.1, 0.5, 1.234, 5.0, 100.0]:
        f = BeatThisSpec.seconds_to_frame(s)
        assert abs(BeatThisSpec.frame_to_seconds(f) - s) <= 0.5 / BeatThisSpec.fps()


def test_defaults():
    c = AnalysisConfig()
    assert c.checkpoint == "final0"
    assert c.dbn is False
    assert c.float16 is False


def test_from_dict_rejects_unknown():
    try:
        AnalysisConfig.from_dict({"nonsense": True, "checkpoint": "final0"})
    except UnsupportedParameterError:
        return
    raise AssertionError("expected UnsupportedParameterError")


def test_validation():
    try:
        AnalysisConfig(checkpoint="")
    except ConfigurationError:
        return
    raise AssertionError("expected ConfigurationError for empty checkpoint")
