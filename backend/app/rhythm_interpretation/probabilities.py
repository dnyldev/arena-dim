"""Numerically stable evidence helpers."""

from __future__ import annotations

import numpy as np


def sigmoid_logits(logits: object) -> np.ndarray:
    """Convert finite logits to probabilities without overflow."""
    values = np.asarray(logits, dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("Logits must be finite")
    result = np.empty_like(values)
    positive = values >= 0
    result[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exp_values = np.exp(values[~positive])
    result[~positive] = exp_values / (1.0 + exp_values)
    return result
