from app.analysis.numbering import infer_beat_numbers, _fallback_numbering


def test_basic_numbering():
    beats = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    downs = [0.0, 2.0]
    numbers = infer_beat_numbers(beats, downs)
    assert numbers == [1, 2, 3, 4, 1, 2, 3, 4]


def test_fallback_numbering():
    beats = [0.0, 0.5, 1.0, 1.5, 2.0]
    downs = [0.0, 2.0]
    assert _fallback_numbering(beats, downs) == [1, 2, 3, 4, 1]


def test_pickup():
    # Beat 0.5 is a pickup; downbeats at 1.0 and 3.0.
    beats = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    downs = [1.0, 3.0]
    numbers = _fallback_numbering(beats, downs)
    # 0.5 isn't a downbeat in the fallback, so it counts from 1.
    assert numbers[0] == 1
    assert numbers[1] == 1  # downbeat resets
    assert numbers[5] == 1


def test_empty():
    assert infer_beat_numbers([], []) == []
