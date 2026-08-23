import numpy as np

from app.core.config import BeatThisSpec
from app.engines.beat_this.chunking import aggregate_prediction, split_piece


def test_short_piece_single_chunk():
    chunks = split_piece(100)
    assert len(chunks) == 1
    assert chunks[0].start_frame == 0
    assert chunks[0].end_frame == 100


def test_long_piece_covers_all_frames():
    length = 10000
    chunks = split_piece(length)
    assert len(chunks) > 1
    # Every output frame is covered by at least one central window.
    covered = np.zeros(length, dtype=bool)
    for c in chunks:
        covered[c.start_frame : c.end_frame] = True
    assert covered.all()
    # Each non-final chunk starts on the 1488-frame step grid
    # (chunk_size - 2*border); the final chunk may be shifted left to
    # avoid a short remainder chunk.
    step = BeatThisSpec.CHUNK_SIZE - 2 * BeatThisSpec.BORDER_SIZE
    for i in range(len(chunks) - 1):
        assert chunks[i].start_frame == i * step
    assert chunks[-1].end_frame == length


def test_aggregation_recovers_full_signal():
    """keep_first aggregation must reproduce a known signal end-to-end."""
    length = 10000
    chunks = split_piece(length)
    # Build predictions such that each central position carries a
    # unique value equal to its global frame index.  Input borders can
    # be garbage; aggregation must ignore them.
    preds = []
    for c in chunks:
        pred = np.full(c.input_end - c.input_start, -999.0, dtype=np.float32)
        # Fill the central slice with its true frame indices.
        pred_start = c.start_frame - c.input_start
        pred_end = c.end_frame - c.input_start
        pred[pred_start:pred_end] = np.arange(
            c.start_frame, c.end_frame, dtype=np.float32
        )
        preds.append(pred)
    out = aggregate_prediction(chunks, preds, length)
    np.testing.assert_array_equal(out, np.arange(length, dtype=np.float32))


def test_aggregate_keep_first():
    length = 5000
    chunks = split_piece(length)
    # Each "prediction" is a distinct constant over its full input range.
    preds = []
    for i, c in enumerate(chunks):
        preds.append(np.full(c.input_end - c.input_start, float(i), dtype=np.float32))
    out = aggregate_prediction(chunks, preds, length)
    assert out.shape == (length,)
    # First chunk's central region must retain value 0 under keep_first.
    first = chunks[0]
    assert np.all(out[first.start_frame : first.end_frame] == 0.0)
    # The middle is stitched without NaN.
    assert not np.any(np.isnan(out))
