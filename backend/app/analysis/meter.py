"""Time-signature (meter) estimation.

Beat This! does not output a time signature; only beat and downbeat
times.  This module reconstructs a *heuristic* estimate of the number
of beats per bar (e.g. 4 for 4/4, 3 for 3/4) purely from the spacing
between consecutive downbeats, using the same ``beat_numbers`` the
orchestrator already computes for display.

This is intentionally **not** treated as ground truth: the result is
always tagged ``ValueOrigin.ESTIMATED`` (see ``docs/architecture.md``
§10 "Derived analysis" and the project rule against fabricating
results).  Consumers should treat ``beats_per_bar`` as a best guess,
not a native model output.

Method
------
For each pair of consecutive downbeats, the number of beats strictly
between them (inclusive of the first, exclusive of the next) gives the
bar length in beats.  We report the mode (most common bar length) as
the overall estimate, its relative frequency as a ``confidence``, and
flag ``is_stable`` when the meter does not change across the piece
(e.g. distinguishing a steady 4/4 tune from one with an irregular bar
or a genuine metre change, such as many prog-rock / Balkan pieces).

Extending this to detect the actual meter *changes* (bar-by-bar) is
supported by the ``per_bar`` field, which already carries the
bar-length sequence -- a future feature (e.g. a "meter timeline" in
the UI) can consume it directly without touching this analyzer.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from app.domain.models import MeterEstimate, ValueOrigin

# Plausible beats-per-bar range for popular/contemporary music. Values
# outside this range are far more likely to be beat-tracking errors
# (missed/spurious downbeats) than a genuine, unusual time signature,
# so we ignore them, weighted-mode style, when they fall outside it.
MIN_BEATS_PER_BAR = 2
MAX_BEATS_PER_BAR = 12


class MeterAnalyzer:
    """Estimate a time signature (beats-per-bar) from beat numbering."""

    def analyze(
        self, beats: Iterable[float], downbeats: Iterable[float]
    ) -> MeterEstimate:
        beats_arr = sorted(float(b) for b in beats)
        downs_arr = sorted(float(d) for d in downbeats)

        if len(downs_arr) < 2 or len(beats_arr) < 2:
            return MeterEstimate(
                beats_per_bar=None,
                confidence=None,
                per_bar=(),
                is_stable=None,
            )

        tol = 1e-3
        down_positions = self._indices_of(beats_arr, downs_arr, tol)
        if len(down_positions) < 2:
            return MeterEstimate(beats_per_bar=None, confidence=None, per_bar=())

        per_bar: list[int] = [
            down_positions[i + 1] - down_positions[i]
            for i in range(len(down_positions) - 1)
        ]
        plausible = [
            n for n in per_bar if MIN_BEATS_PER_BAR <= n <= MAX_BEATS_PER_BAR
        ]
        sample = plausible or per_bar
        if not sample:
            return MeterEstimate(beats_per_bar=None, confidence=None, per_bar=())

        counts = Counter(sample)
        beats_per_bar, mode_count = counts.most_common(1)[0]
        confidence = mode_count / len(sample)
        is_stable = confidence >= 0.9

        return MeterEstimate(
            beats_per_bar=int(beats_per_bar),
            origin=ValueOrigin.ESTIMATED,
            method="downbeat_interval_mode",
            confidence=float(confidence),
            per_bar=tuple(per_bar),
            is_stable=bool(is_stable),
        )

    @staticmethod
    def _indices_of(
        beats: list[float], downbeats: list[float], tol: float
    ) -> list[int]:
        """Index of each downbeat within the sorted beats list."""
        indices: list[int] = []
        j = 0
        n = len(beats)
        for d in downbeats:
            while j < n and beats[j] < d - tol:
                j += 1
            if j < n and abs(beats[j] - d) <= tol:
                indices.append(j)
            # If a downbeat has no matching beat (shouldn't happen once
            # validated), it's simply skipped rather than fabricated.
        return indices
