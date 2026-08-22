"""Tempo analysis.

Beat This! does not output tempo.  We derive two things from the
inter-beat intervals (IBIs):

* a single scalar tempo, per the Research Package §4.E / §18:

      tempo_bpm = 60.0 / median(IBI)

* a **tempo curve** — a windowed/rolling local tempo estimate over
  time, for songs whose tempo drifts or changes.  Each point is the
  median BPM of a sliding window of consecutive beats, anchored at the
  center time of that window.  A median (not mean) is used so a single
  spurious/missed beat inside the window does not distort the local
  estimate.

Both are explicitly marked ``ValueOrigin.DERIVED`` so consumers
(frontend, JSON) know neither is a native model output.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np

from app.domain.models import TempoCurvePoint, TempoEstimate, ValueOrigin

# Sliding window size, in beats, used for the local tempo curve.
# 8 beats is roughly 2 bars in common 4/4 music -- short enough to
# track genuine tempo drift, long enough to smooth over a single
# missed/spurious beat detection.
DEFAULT_CURVE_WINDOW_BEATS = 8


class TempoAnalyzer:
    """Compute a median-IBI tempo estimate and a windowed tempo curve."""

    def __init__(self, curve_window_beats: int = DEFAULT_CURVE_WINDOW_BEATS) -> None:
        self.curve_window_beats = curve_window_beats

    def analyze(self, beats: Iterable[float]) -> TempoEstimate:
        arr = np.asarray(list(beats), dtype=np.float64)
        if arr.size < 2:
            return TempoEstimate(
                bpm=None,
                origin=ValueOrigin.DERIVED,
                method="median_ibi",
                median_ibi_sec=None,
                curve_window_beats=self.curve_window_beats,
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
                curve_window_beats=self.curve_window_beats,
            )
        median_ibi = float(np.median(pos))
        bpm = 60.0 / median_ibi
        bpms = (60.0 / pos).tolist()
        curve = self._tempo_curve(arr)
        return TempoEstimate(
            bpm=float(bpm),
            origin=ValueOrigin.DERIVED,
            method="median_ibi",
            median_ibi_sec=median_ibi,
            min_bpm=float(np.min(bpms)),
            max_bpm=float(np.max(bpms)),
            raw_bpms=tuple(round(b, 3) for b in bpms),
            curve=curve,
            curve_window_beats=self.curve_window_beats,
        )

    def _tempo_curve(self, sorted_beats: np.ndarray) -> tuple[TempoCurvePoint, ...]:
        """Sliding-window local tempo estimate over time.

        For each window of ``curve_window_beats`` consecutive beats we
        take the median instantaneous BPM within the window and anchor
        it at the window's center timestamp. Windows advance one beat
        at a time (maximum resolution); with too few beats we fall
        back to a single point using whatever beats are available.
        """
        n = sorted_beats.size
        if n < 2:
            return ()

        window = max(2, min(self.curve_window_beats, n))
        points: list[TempoCurvePoint] = []
        # Each window covers `window` beats -> `window - 1` intervals.
        for start in range(0, n - window + 1):
            end = start + window  # exclusive
            segment = sorted_beats[start:end]
            seg_ibis = np.diff(segment)
            seg_pos = seg_ibis[seg_ibis > 0]
            if seg_pos.size == 0:
                continue
            local_bpm = 60.0 / float(np.median(seg_pos))
            center_time = float(segment[0] + segment[-1]) / 2.0
            points.append(TempoCurvePoint(time_sec=center_time, bpm=local_bpm))

        if not points:
            # Fewer beats than the minimum window: single overall estimate.
            seg_ibis = np.diff(sorted_beats)
            seg_pos = seg_ibis[seg_ibis > 0]
            if seg_pos.size:
                local_bpm = 60.0 / float(np.median(seg_pos))
                center_time = float(sorted_beats[0] + sorted_beats[-1]) / 2.0
                points.append(TempoCurvePoint(time_sec=center_time, bpm=local_bpm))

        return tuple(points)
