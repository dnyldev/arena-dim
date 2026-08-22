"""Chunked inference helpers.

These replicate the exact behaviour of Beat This!'s ``split_piece`` and
``aggregate_prediction`` from ``beat_this/inference.py`` so that
long-file inference is numerically equivalent to the reference while
remaining observable through our event system.

Constants match the research package:

    chunk_size    = 1500 frames (30 s at 50 fps)
    border_size   = 6 frames
    overlap_mode  = "keep_first"
    avoid_short_end = True
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.core.config import BeatThisSpec


@dataclass(frozen=True)
class Chunk:
    start_frame: int
    end_frame: int
    """Half-open interval of valid output frames."""
    # The model input covers [input_start, input_end) with zero-pad borders.
    input_start: int
    input_end: int


def split_piece(
    length: int,
    chunk_size: int = BeatThisSpec.CHUNK_SIZE,
    border_size: int = BeatThisSpec.BORDER_SIZE,
    avoid_short_end: bool = True,
) -> list[Chunk]:
    """Split a track of ``length`` frames into overlapping chunks.

    Mirrors ``beat_this.inference.split_piece``.
    """
    if length <= 0:
        return []

    # For short pieces, a single chunk covering the whole thing.
    if length < chunk_size + border_size * 2:
        return [
            Chunk(
                start_frame=0,
                end_frame=length,
                input_start=0,
                input_end=length,
            )
        ]

    # Start positions every (chunk_size - 2*border_size); each chunk
    # carries a border on both sides that is discarded after inference.
    step = chunk_size - 2 * border_size
    starts = list(range(0, length - chunk_size + 1, step))

    # Ensure a final chunk covers the remainder.  Avoid a tiny last
    # chunk by shifting its start left (keep_first resolves overlap).
    last_start = starts[-1] if starts else 0
    if last_start + chunk_size < length:
        starts.append(length - chunk_size)
    elif not starts:
        starts.append(0)

    # Deduplicate while preserving order.
    seen: set[int] = set()
    unique_starts: list[int] = []
    for s in starts:
        if s not in seen:
            seen.add(s)
            unique_starts.append(s)

    chunks: list[Chunk] = []
    for s in unique_starts:
        input_start = max(0, s - border_size)
        input_end = min(length, s + chunk_size + border_size)
        start_frame = s
        end_frame = min(length, s + chunk_size)
        chunks.append(
            Chunk(
                start_frame=start_frame,
                end_frame=end_frame,
                input_start=input_start,
                input_end=input_end,
            )
        )

    if avoid_short_end and len(chunks) >= 2:
        # If the last valid chunk is shorter than border_size, merge it
        # into the previous one.
        last = chunks[-1]
        prev = chunks[-2]
        if last.end_frame - last.start_frame < border_size:
            chunks[-2] = Chunk(
                start_frame=prev.start_frame,
                end_frame=last.end_frame,
                input_start=prev.input_start,
                input_end=last.input_end,
            )
            chunks.pop()

    return chunks


def aggregate_prediction(
    chunks: list[Chunk],
    predictions: list[np.ndarray],
    length: int,
    overlap_mode: str = "keep_first",
    border_size: int = BeatThisSpec.BORDER_SIZE,
) -> np.ndarray:
    """Stitch per-chunk predictions back into one length-``T`` array.

    ``predictions[i]`` is the raw model output over
    ``[chunks[i].input_start, chunks[i].input_end)``.  We only keep the
    central ``[start_frame, end_frame)`` slice and copy it into the
    output.  When slices overlap, ``keep_first`` retains the earlier
    chunk's prediction; the chunking scheme above guarantees overlaps
    occur only in the border regions that both chunks agree on.
    """
    if len(predictions) != len(chunks):
        raise ValueError(
            f"Got {len(predictions)} predictions for {len(chunks)} chunks"
        )
    out = np.full((length,) + predictions[0].shape[1:], np.nan, dtype=np.float32)
    filled = np.zeros(length, dtype=bool)

    for chunk, pred in zip(chunks, predictions):
        # Pred indices correspond to [input_start, input_end).
        pred_start = chunk.start_frame - chunk.input_start
        pred_end = chunk.end_frame - chunk.input_start
        central = pred[pred_start:pred_end]
        target = slice(chunk.start_frame, chunk.end_frame)
        if overlap_mode == "keep_first":
            mask = ~filled[target]
            out[target][mask] = central[mask]
            filled[target] = True
        elif overlap_mode == "keep_last":
            out[target] = central
            filled[target] = True
        else:
            raise ValueError(f"Unknown overlap_mode {overlap_mode!r}")

    if not filled.all():
        # Any still-NaN positions should not happen with the current
        # splitter; guard against them with zeros.
        out = np.where(np.isnan(out), 0.0, out)
    return out
