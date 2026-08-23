"""Versioned, serialisable settings for rhythm interpretation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .models import InterpretationMode


@dataclass(frozen=True)
class PulseTrackingConfig:
    window_sec: float = 8.0
    hop_sec: float = 2.0
    start_threshold: float = 0.85
    continue_threshold: float = 0.60
    stop_weak_windows: int = 3


@dataclass(frozen=True)
class HypothesisConfig:
    candidate_group_sizes: tuple[int, ...] = (2, 3, 4, 6)
    minimum_winner_margin: float = 0.15


@dataclass(frozen=True)
class MutationConfig:
    apply_threshold: float = 0.90
    suggest_threshold: float = 0.70
    max_changed_downbeat_ratio: float = 0.10
    allow_timestamp_changes: bool = False
    allow_beat_insertion: bool = False
    allow_beat_deletion: bool = False


@dataclass(frozen=True)
class RhythmInterpretationConfig:
    ruleset_id: str = "conservative-rhythm-v1"
    ruleset_version: str = "1.0.0"
    mode: InterpretationMode = InterpretationMode.OBSERVE_ONLY
    pulse_tracking: PulseTrackingConfig = field(default_factory=PulseTrackingConfig)
    hypotheses: HypothesisConfig = field(default_factory=HypothesisConfig)
    mutation: MutationConfig = field(default_factory=MutationConfig)

    def __post_init__(self) -> None:
        p, h, m = self.pulse_tracking, self.hypotheses, self.mutation
        if p.window_sec <= 0 or p.hop_sec <= 0 or p.hop_sec > p.window_sec:
            raise ValueError("Pulse windows require 0 < hop_sec <= window_sec")
        for label, value in (
            ("start_threshold", p.start_threshold),
            ("continue_threshold", p.continue_threshold),
            ("minimum_winner_margin", h.minimum_winner_margin),
            ("apply_threshold", m.apply_threshold),
            ("suggest_threshold", m.suggest_threshold),
            ("max_changed_downbeat_ratio", m.max_changed_downbeat_ratio),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{label} must be between 0 and 1")
        if p.start_threshold <= p.continue_threshold:
            raise ValueError("Starting tracking must be stricter than continuing it")
        if m.apply_threshold <= m.suggest_threshold:
            raise ValueError("Apply threshold must be stricter than suggest threshold")
        if p.stop_weak_windows < 1:
            raise ValueError("stop_weak_windows must be positive")
        if not h.candidate_group_sizes or any(x < 2 for x in h.candidate_group_sizes):
            raise ValueError("Candidate group sizes must contain integers >= 2")
        if m.allow_timestamp_changes or m.allow_beat_insertion or m.allow_beat_deletion:
            raise ValueError("V1 safety charter forbids moving, inserting, or deleting beats")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["mode"] = self.mode.value
        return value
