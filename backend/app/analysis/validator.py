"""Validation of beat / downbeat output.

This layer does not modify Beat This!; it only inspects the result and
reports issues.  A hard failure (e.g. NaNs, downbeats not subset of
beats) raises :class:`ValidationError`; softer issues (empty result,
irregular spacing) are reported but do not block output.
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np

from app.core.errors import EmptyResultError, ValidationError
from app.domain.models import (
    AudioProbe,
    BeatEngineRawResult,
    ValidationIssue,
    ValidationReport,
)


class BeatValidator:
    """Validate the raw engine result against domain invariants."""

    # A BPM outside [10, 500] is physically implausible for music and
    # indicates a defect; it is a warning, not a hard error.
    MIN_PLAUSIBLE_BPM = 10.0
    MAX_PLAUSIBLE_BPM = 500.0

    def validate(
        self, raw: BeatEngineRawResult, audio: AudioProbe | None = None
    ) -> ValidationReport:
        issues: list[ValidationIssue] = []
        hard_errors: list[str] = []

        beats = np.asarray(raw.beats, dtype=np.float64)
        downs = np.asarray(raw.downbeats, dtype=np.float64)

        # 1. Finite / non-NaN
        if not np.all(np.isfinite(beats)):
            hard_errors.append("Beat timestamps contain NaN or Inf")
        if not np.all(np.isfinite(downs)):
            hard_errors.append("Downbeat timestamps contain NaN or Inf")

        # 2. Non-negative
        if beats.size and float(np.nanmin(beats)) < 0:
            hard_errors.append("Negative beat timestamp present")
        if downs.size and float(np.nanmin(downs)) < 0:
            hard_errors.append("Negative downbeat timestamp present")

        # 3. Sorted (non-decreasing)
        if beats.size > 1 and np.any(np.diff(beats) < -1e-9):
            hard_errors.append("Beat timestamps are not sorted")
        if downs.size > 1 and np.any(np.diff(downs) < -1e-9):
            hard_errors.append("Downbeat timestamps are not sorted")

        # 4. Duplicate beats (after snap, exact floats are fine)
        if beats.size > 1:
            uniq = np.unique(beats)
            if uniq.size != beats.size:
                issues.append(
                    ValidationIssue(
                        "warning",
                        "duplicate_beats",
                        f"{beats.size - uniq.size} duplicate beat timestamp(s)",
                    )
                )

        # 5. Bounds check vs audio duration
        if audio is not None and beats.size:
            if float(np.nanmax(beats)) > audio.duration_sec + 0.05:
                hard_errors.append(
                    "Beat timestamp exceeds audio duration "
                    f"({float(np.nanmax(beats)):.3f} > {audio.duration_sec:.3f})"
                )
            if downs.size and float(np.nanmax(downs)) > audio.duration_sec + 0.05:
                hard_errors.append("Downbeat timestamp exceeds audio duration")

        # 6. Downbeats must be a subset of beats
        if beats.size and downs.size:
            # Match with a small tolerance since snapping should make
            # them exact, but guard against float drift.
            tol = 1e-3
            matched = np.any(
                np.abs(beats[None, :] - downs[:, None]) <= tol, axis=1
            )
            if not np.all(matched):
                unmatched = downs[~matched]
                hard_errors.append(
                    f"{len(unmatched)} downbeat(s) are not beats: "
                    f"{unmatched[:5].tolist()}"
                )

        # 7. Implausible intervals (warning only)
        if beats.size > 1:
            ibis = np.diff(beats)
            pos_ibis = ibis[ibis > 0]
            if pos_ibis.size:
                bpms = 60.0 / pos_ibis
                if np.any(bpms < self.MIN_PLAUSIBLE_BPM) or np.any(
                    bpms > self.MAX_PLAUSIBLE_BPM
                ):
                    issues.append(
                        ValidationIssue(
                            "warning",
                            "implausible_interval",
                            "Some inter-beat intervals are outside "
                            f"{self.MIN_PLAUSIBLE_BPM}-{self.MAX_PLAUSIBLE_BPM} BPM",
                        )
                    )

        # 8. Empty result
        if beats.size == 0:
            issues.append(
                ValidationIssue(
                    "info",
                    "empty_result",
                    "No beats detected — audio may be silent or too short",
                )
            )

        if hard_errors:
            for msg in hard_errors:
                issues.append(ValidationIssue("error", "hard_validation", msg))
            raise ValidationError(
                "Beat validation failed: " + "; ".join(hard_errors),
                technical_detail="; ".join(hard_errors),
            )

        return ValidationReport(ok=True, issues=tuple(issues))
