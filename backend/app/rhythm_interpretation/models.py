"""Transparent domain records for conservative rhythm interpretation.

These records are deliberately independent from the inference engine.  They
capture observations and decisions without mutating raw model output.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Literal


class TrackingStatus(str, Enum):
    TRACKED = "tracked"
    UNCERTAIN = "uncertain"
    UNTRACKED = "untracked"


class DecisionAction(str, Enum):
    APPLY = "apply"
    SUGGEST = "suggest"
    ABSTAIN = "abstain"
    REJECT_ISSUE = "reject_issue"


class InterpretationMode(str, Enum):
    OFF = "off"
    OBSERVE_ONLY = "observe_only"
    CONSERVATIVE_APPLY = "conservative_apply"


@dataclass(frozen=True)
class Actor:
    type: Literal["model", "rule_engine", "human", "importer", "system"]
    name: str
    version: str | None = None


@dataclass(frozen=True)
class Evidence:
    type: str
    value: float | int | str | bool | None
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AlternativeHypothesis:
    hypothesis: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _probability("alternative score", self.score)


@dataclass(frozen=True)
class ProposedChange:
    field: str
    before: Any
    after: Any


@dataclass(frozen=True)
class RuleIdentity:
    id: str
    version: str

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.version.strip():
            raise ValueError("Rule id and version must be non-empty")


@dataclass(frozen=True)
class RuleDecision:
    """Append-only explanation of one rule evaluation."""

    decision_id: str
    actor: Actor
    rule: RuleIdentity
    stage: str
    action: DecisionAction
    target_event_ids: tuple[str, ...]
    decision_confidence: float
    thresholds: dict[str, float]
    reason_codes: tuple[str, ...]
    evidence_for: tuple[Evidence, ...] = ()
    evidence_against: tuple[Evidence, ...] = ()
    alternatives: tuple[AlternativeHypothesis, ...] = ()
    proposed_change: ProposedChange | None = None
    region_id: str | None = None
    mutation_applied: bool = False

    def __post_init__(self) -> None:
        _probability("decision confidence", self.decision_confidence)
        if not self.decision_id.strip():
            raise ValueError("decision_id must be non-empty")
        if not self.stage.strip():
            raise ValueError("stage must be non-empty")
        if not self.target_event_ids:
            raise ValueError("A decision must identify at least one target event")
        if not self.reason_codes:
            raise ValueError("A decision must include at least one reason code")
        for name, threshold in self.thresholds.items():
            _probability(f"threshold {name}", threshold)
        if self.mutation_applied and self.action is not DecisionAction.APPLY:
            raise ValueError("Only an apply decision may report an applied mutation")
        if self.mutation_applied and self.proposed_change is None:
            raise ValueError("An applied mutation must describe its change")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["action"] = self.action.value
        return value


@dataclass(frozen=True)
class TrackingRegion:
    region_id: str
    start_sec: float
    end_sec: float
    status: TrackingStatus
    status_confidence: float
    reason_codes: tuple[str, ...]
    metrics: dict[str, float | int | None] = field(default_factory=dict)
    start_beat_index: int | None = None
    end_beat_index: int | None = None

    def __post_init__(self) -> None:
        if self.start_sec < 0 or self.end_sec <= self.start_sec:
            raise ValueError("Tracking region must have a positive time range")
        _probability("tracking status confidence", self.status_confidence)
        if not self.reason_codes:
            raise ValueError("Tracking region must explain its classification")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value


def _probability(label: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be between 0 and 1, got {value}")
