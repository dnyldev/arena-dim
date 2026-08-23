"""Rhythmic descriptors.

Currently derives only quantities that are unambiguously supported by
the data:

* beat density (beats / second),
* mean / std inter-beat interval,
* irregularity (coefficient of variation of IBIs).

Time-signature estimation lives in :class:`app.analysis.meter.MeterAnalyzer`
and tempo-change tracking lives in the ``tempo.curve`` field produced by
:class:`app.analysis.tempo.TempoAnalyzer`. Bar-position detection remains a
**future** capability and is deliberately not fabricated here.  The
:class:`RhythmAnalyzer` class is the extension point for further
rhythmic descriptors.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np

from app.domain.models import RhythmInfo


class RhythmAnalyzer:
    def analyze(self, beats: Iterable[float], duration_sec: float) -> RhythmInfo:
        arr = np.asarray(list(beats), dtype=np.float64)
        if arr.size < 2 or duration_sec <= 0:
            return RhythmInfo()
        arr = np.sort(arr)
        ibis = np.diff(arr)
        pos = ibis[ibis > 0]
        if pos.size == 0:
            return RhythmInfo()
        mean_ibi = float(np.mean(pos))
        std_ibi = float(np.std(pos))
        irregularity = float(std_ibi / mean_ibi) if mean_ibi > 0 else None
        return RhythmInfo(
            beat_density_beats_per_second=float(arr.size / duration_sec),
            mean_inter_beat_interval_sec=mean_ibi,
            std_inter_beat_interval_sec=std_ibi,
            irregularity=irregularity,
        )
