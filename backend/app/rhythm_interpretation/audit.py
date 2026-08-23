"""Append-only in-memory audit trail used by interpretation stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .models import RuleDecision


@dataclass
class AuditTrail:
    _records: list[RuleDecision] = field(default_factory=list, repr=False)
    _ids: set[str] = field(default_factory=set, repr=False)

    def append(self, decision: RuleDecision) -> None:
        if decision.decision_id in self._ids:
            raise ValueError(f"Duplicate decision id: {decision.decision_id}")
        self._records.append(decision)
        self._ids.add(decision.decision_id)

    def extend(self, decisions: Iterable[RuleDecision]) -> None:
        for decision in decisions:
            self.append(decision)

    @property
    def records(self) -> tuple[RuleDecision, ...]:
        """Return an immutable view; callers cannot rewrite history."""
        return tuple(self._records)

    def to_list(self) -> list[dict]:
        return [record.to_dict() for record in self._records]
