"""Tempo analysis.

Beat This! does not output tempo.  We derive it from the inter-beat
intervals (IBIs) as specified in the Research Package §4.E / §18:

    tempo_bpm = 60.0 / median(IBI)

The origin is explicitly marked as ``DERIVED`` so consumers (frontend,
JSON) know it is not a native model output.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np

from app.domain.models import TempoEstimate, ValueOrigin


class TempoAnalyzer:
    """Compute a median-I-B-I tempo estimate from beat times."""

    def analyze(self, beats: Iterable[float]) -> TempoEstimate:
        arr = np.asarray(list(beats), dtype=np.float64)
        if arr.size < 2:
            return TempoEstimate(
                bpm=None,
                origin=ValueOrigin.DERIVED,
                method="median_ibi",
                median_ibi_sec=None,
            )
        arr = np.sort(arr)
        ibis = np.diff(arr)
        # Guard against non-positive intervals (duplicates).
        pos = ibis[ibis > 0]
        if pos.size == 0:
            return TempoEstimate(
                bpm=None,
                origin=ValueOrigin.DERIVED,
                method="median_ibi",
                median_ibi_sec=None,
            )
        median_ibi = float(np.median(pos))
        bpm = 60.0 / median_ibi
        bpms = (60.0 / pos).tolist()
        return TempoEstimate(
            bpm=float(bpm),
            origin=ValueOrigin.DERIVED,
            method="median_ibi",
            median_ibi_sec=median_ibi,
            min_bpm=float(np.min(bpms)),
            max_bpm=float(np.max(bpms)),
            raw_bpms=tuple(round(b, 3) for b in bpms),
        )
