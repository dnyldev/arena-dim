"""Beat numbering.

Wraps :func:`beat_this.utils.infer_beat_numbers` when available so
downbeats receive number 1 and subsequent beats count up.  If the
beat_this helper is unavailable (e.g. the package isn't installed), we
provide an equivalent implementation that handles the common case and
raises on inconsistent input.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np

from app.core.errors import ValidationError


def infer_beat_numbers(
    beats: Iterable[float], downbeats: Iterable[float]
) -> list[int]:
    try:
        from beat_this.utils import infer_beat_numbers as _bt_numbers

        return [
            int(x)
            for x in _bt_numbers(
                np.asarray(list(beats), dtype=np.float64),
                np.asarray(list(downbeats), dtype=np.float64),
            )
        ]
    except ImportError:
        return _fallback_numbering(list(beats), list(downbeats))
    except Exception as exc:
        # beat_this raises ValueError when downbeats aren't a subset.
        raise ValidationError(
            f"Could not number beats: {exc}",
            technical_detail=str(exc),
        ) from exc


def _fallback_numbering(beats: list[float], downbeats: list[float]) -> list[int]:
    """Equivalent numbering: downbeats reset to 1, then count up."""
    if not beats:
        return []
    tol = 1e-3
    down_set = {round(d / tol) * tol for d in downbeats}
    numbers: list[int] = []
    count = 1
    for t in beats:
        key = round(t / tol) * tol
        if key in down_set:
            count = 1
        numbers.append(count)
        count += 1
    return numbers
