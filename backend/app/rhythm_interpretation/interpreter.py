"""Conservative pulse-region and downbeat interpretation engine.

V1 is intentionally bounded: timestamps and beat membership are immutable;
only the downbeat role of an existing event can ever be interpreted.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from statistics import median
from typing import Any, Iterable

import numpy as np

from .audit import AuditTrail
from .config import RhythmInterpretationConfig
from .models import (
    Actor,
    AlternativeHypothesis,
    DecisionAction,
    Evidence,
    InterpretationMode,
    ProposedChange,
    RuleDecision,
    RuleIdentity,
    TrackingRegion,
    TrackingStatus,
)
from .probabilities import sigmoid_logits


@dataclass(frozen=True)
class BeatEvidence:
    event_id: str
    index: int
    time_sec: float
    raw_is_downbeat: bool
    beat_logit: float | None
    downbeat_logit: float | None
    beat_probability: float | None
    downbeat_probability: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WindowEvidence:
    start_sec: float
    end_sec: float
    beat_indices: tuple[int, ...]
    activation_support: float
    interval_stability: float
    sequence_support: float
    overall: float
    classification: TrackingStatus


class RhythmInterpreter:
    """Explain raw evidence and optionally reinterpret existing beat roles."""

    def __init__(self, config: RhythmInterpretationConfig | None = None) -> None:
        self.config = config or RhythmInterpretationConfig()

    def analyze(
        self,
        beats: Iterable[float],
        downbeats: Iterable[float],
        duration_sec: float,
        fps: float,
        beat_logits: Any | None,
        downbeat_logits: Any | None,
    ) -> dict[str, Any]:
        beat_times = tuple(float(x) for x in beats)
        down_times = tuple(float(x) for x in downbeats)
        events = self._events(beat_times, down_times, fps, beat_logits, downbeat_logits)
        if self.config.mode is InterpretationMode.OFF:
            return self._off_result(events)

        windows = self._windows(events, duration_sec)
        regions = self._regions(windows, duration_sec, events)
        hypotheses = [self._hypotheses(region, events) for region in regions]
        hypotheses = [h for h in hypotheses if h is not None]
        issues = self._issues(regions, hypotheses, events)
        audit = self._decisions(issues, regions, hypotheses, events)
        final_events = self._final_events(events, audit)
        before = self._structure_consistency(events, hypotheses, raw=True)
        after = self._structure_consistency_from_final(final_events, hypotheses)
        return {
            "schema_version": "1.0",
            "mode": self.config.mode.value,
            "ruleset": {
                "id": self.config.ruleset_id,
                "version": self.config.ruleset_version,
                "configuration": self.config.to_dict(),
            },
            "guarantees": {
                "raw_immutable": True,
                "timestamps_changed": False,
                "beats_inserted": 0,
                "beats_deleted": 0,
            },
            "raw_model": {"events": [event.to_dict() for event in events]},
            "tracking": {
                "windows": [self._window_dict(window) for window in windows],
                "regions": [region.to_dict() for region in regions],
            },
            "hypotheses": hypotheses,
            "issues": issues,
            "decisions": audit.to_list(),
            "final": {"events": final_events},
            "summary": self._summary(events, regions, issues, audit, before, after),
            "correctness_verdict": "unknown",
        }

    def _off_result(self, events: tuple[BeatEvidence, ...]) -> dict[str, Any]:
        final = [self._unchanged_event(event) for event in events]
        return {
            "schema_version": "1.0",
            "mode": "off",
            "ruleset": None,
            "guarantees": {"raw_immutable": True, "timestamps_changed": False, "beats_inserted": 0, "beats_deleted": 0},
            "raw_model": {"events": [event.to_dict() for event in events]},
            "tracking": {"windows": [], "regions": []},
            "hypotheses": [], "issues": [], "decisions": [],
            "final": {"events": final},
            "summary": {"changed_roles": 0},
            "correctness_verdict": "unknown",
        }

    def _events(self, beats, downbeats, fps, beat_logits, downbeat_logits):
        down_keys = {round(x, 4) for x in downbeats}
        beat_array = None if beat_logits is None else np.asarray(beat_logits, dtype=np.float64).reshape(-1)
        down_array = None if downbeat_logits is None else np.asarray(downbeat_logits, dtype=np.float64).reshape(-1)
        beat_probs = None if beat_array is None else sigmoid_logits(beat_array)
        down_probs = None if down_array is None else sigmoid_logits(down_array)
        result = []
        for index, time_sec in enumerate(beats):
            frame = max(0, round(time_sec * fps))
            bp = float(beat_probs[frame]) if beat_probs is not None and frame < len(beat_probs) else None
            dp = float(down_probs[frame]) if down_probs is not None and frame < len(down_probs) else None
            bl = float(beat_array[frame]) if beat_array is not None and frame < len(beat_array) else None
            dl = float(down_array[frame]) if down_array is not None and frame < len(down_array) else None
            result.append(BeatEvidence(f"beat-{index:06d}", index, time_sec, round(time_sec, 4) in down_keys, bl, dl, bp, dp))
        return tuple(result)

    def _windows(self, events: tuple[BeatEvidence, ...], duration: float) -> tuple[WindowEvidence, ...]:
        cfg = self.config.pulse_tracking
        if duration <= 0:
            return ()
        starts = list(np.arange(0.0, max(duration - cfg.window_sec, 0.0) + 1e-9, cfg.hop_sec))
        last = max(0.0, duration - cfg.window_sec)
        if not starts or abs(starts[-1] - last) > 1e-6:
            starts.append(last)
        raw = []
        for start in starts:
            end = min(duration, start + cfg.window_sec)
            selected = tuple(e.index for e in events if start <= e.time_sec < end or (end == duration and e.time_sec == end))
            chosen = [events[i] for i in selected]
            intervals = np.diff([e.time_sec for e in chosen])
            if len(intervals) >= 2 and float(np.mean(intervals)) > 0:
                cv = float(np.std(intervals) / np.mean(intervals))
                stability = max(0.0, 1.0 - cv / 0.25)
            else:
                stability = 0.0
            probabilities = [e.beat_probability for e in chosen if e.beat_probability is not None]
            activation = float(np.mean(probabilities)) if probabilities else (0.65 if chosen else 0.0)
            sequence = min(1.0, len(chosen) / 6.0)
            overall = 0.45 * stability + 0.35 * activation + 0.20 * sequence
            raw.append((start, end, selected, activation, stability, sequence, overall))

        statuses: list[TrackingStatus] = []
        tracking = False
        weak = 0
        for *_, score in raw:
            if not tracking and score >= cfg.start_threshold:
                tracking, weak = True, 0
            elif tracking:
                weak = 0 if score >= cfg.continue_threshold else weak + 1
                if weak >= cfg.stop_weak_windows:
                    tracking, weak = False, 0
            if tracking:
                status = TrackingStatus.TRACKED
            elif score >= cfg.continue_threshold:
                status = TrackingStatus.UNCERTAIN
            else:
                status = TrackingStatus.UNTRACKED
            statuses.append(status)
        return tuple(WindowEvidence(*values, status) for values, status in zip(raw, statuses))

    def _regions(self, windows: tuple[WindowEvidence, ...], duration: float, events: tuple[BeatEvidence, ...]) -> tuple[TrackingRegion, ...]:
        if not windows:
            return ()
        regions = []
        start = 0.0
        status = windows[0].classification
        bucket = []
        for index, window in enumerate(windows):
            if window.classification != status and bucket:
                boundary = window.start_sec
                # A look-ahead window may establish tracking before its first
                # actual beat. Never backfill a tracked region into silence.
                if window.classification is TrackingStatus.TRACKED and window.beat_indices:
                    boundary = max(boundary, events[window.beat_indices[0]].time_sec)
                regions.append(self._make_region(len(regions), start, boundary, status, bucket))
                start, status, bucket = boundary, window.classification, []
            bucket.append(window)
        regions.append(self._make_region(len(regions), start, duration, status, bucket))
        return tuple(r for r in regions if r.end_sec > r.start_sec)

    def _make_region(self, index, start, end, status, windows):
        scores = [w.overall for w in windows]
        confidence = float(np.mean(scores)) if status is TrackingStatus.TRACKED else float(np.mean([1.0 - s for s in scores]))
        confidence = max(0.0, min(1.0, confidence))
        beat_indices = sorted({i for window in windows for i in window.beat_indices})
        reasons = {
            TrackingStatus.TRACKED: ("sustained_pulse_support", "stable_local_intervals"),
            TrackingStatus.UNCERTAIN: ("partial_pulse_support", "tracking_start_not_confirmed"),
            TrackingStatus.UNTRACKED: ("insufficient_periodic_pulse", "insufficient_sequence_support"),
        }[status]
        return TrackingRegion(
            f"region-{index:03d}", start, end, status, confidence, reasons,
            metrics={"window_count": len(windows), "mean_score": float(np.mean(scores))},
            start_beat_index=beat_indices[0] if beat_indices else None,
            end_beat_index=beat_indices[-1] if beat_indices else None,
        )

    def _hypotheses(self, region: TrackingRegion, events: tuple[BeatEvidence, ...]):
        if region.status is not TrackingStatus.TRACKED:
            return None
        members = [e for e in events if region.start_sec <= e.time_sec <= region.end_sec]
        if len(members) < 4:
            return None
        candidates = []
        for group in self.config.hypotheses.candidate_group_sizes:
            if len(members) < group:
                continue
            for phase in range(group):
                expected = [e for i, e in enumerate(members) if i % group == phase]
                other = [e for i, e in enumerate(members) if i % group != phase]
                expected_prob = self._mean_down(expected)
                other_prob = self._mean_down(other)
                raw_match = sum(e.raw_is_downbeat for e in expected) / max(1, sum(e.raw_is_downbeat for e in members))
                complexity = min(1.0, len(expected) / 3.0)
                score = 0.5 * expected_prob + 0.2 * (1.0 - other_prob) + 0.2 * raw_match + 0.1 * complexity
                candidates.append({"beats_per_group": group, "phase": phase, "score": round(score, 6), "expected_event_ids": [e.event_id for e in expected], "supporting_event_ids": [e.event_id for e in expected if e.raw_is_downbeat], "contradicting_event_ids": [e.event_id for e in other if e.raw_is_downbeat]})
        candidates.sort(key=lambda x: x["score"], reverse=True)
        if not candidates:
            return None
        winner = candidates[0]
        runner = candidates[1] if len(candidates) > 1 else {"score": 0.0}
        margin = winner["score"] - runner["score"]
        margin_strength = min(
            1.0,
            margin / max(self.config.hypotheses.minimum_winner_margin, 1e-6),
        )
        selection_confidence = max(
            0.0, min(1.0, 0.65 * winner["score"] + 0.35 * margin_strength)
        )
        decision = "selected" if margin >= self.config.hypotheses.minimum_winner_margin else "ambiguous"
        return {"region_id": region.region_id, "selected": winner, "alternatives": candidates[1:5], "winner_margin": round(margin, 6), "selection_confidence": round(selection_confidence, 6), "decision": decision}

    def _mean_down(self, events):
        values = [e.downbeat_probability for e in events if e.downbeat_probability is not None]
        if values:
            return float(np.mean(values))
        return sum(e.raw_is_downbeat for e in events) / max(1, len(events))

    def _issues(self, regions, hypotheses, events):
        result = []
        by_region = {r.region_id: r for r in regions}
        for hypothesis in hypotheses:
            region = by_region[hypothesis["region_id"]]
            members = [e for e in events if region.start_sec <= e.time_sec <= region.end_sec]
            selected = hypothesis["selected"]
            group, phase = selected["beats_per_group"], selected["phase"]
            expected = {e.index for i, e in enumerate(members) if i % group == phase}
            if hypothesis["decision"] == "ambiguous":
                result.append(self._issue("possible_meter_change", region.region_id, [e.event_id for e in members], 0.5, 1.0 - hypothesis["selection_confidence"], {"hypothesis": selected, "alternatives": hypothesis["alternatives"]}))
            for event in members:
                should_down = event.index in expected
                if event.raw_is_downbeat and not should_down:
                    result.append(self._issue("unexpected_downbeat", region.region_id, [event.event_id], 0.6, hypothesis["selection_confidence"], {"raw_downbeat_probability": event.downbeat_probability, "expected_group": group}))
                elif should_down and not event.raw_is_downbeat:
                    result.append(self._issue("missing_downbeat_candidate", region.region_id, [event.event_id], 0.5, hypothesis["selection_confidence"], {"raw_downbeat_probability": event.downbeat_probability, "expected_group": group}))
            expected_events = [e for e in members if e.index in expected]
            missing_runs = self._missing_runs(expected_events)
            for run in missing_runs:
                if len(run) >= 2:
                    result.append(self._issue("downbeat_dropout", region.region_id, [e.event_id for e in run], min(1.0, len(run) / 4), hypothesis["selection_confidence"], {"affected_groups": len(run)}))
        return result

    def _missing_runs(self, expected):
        runs, current = [], []
        for event in expected:
            if not event.raw_is_downbeat:
                current.append(event)
            elif current:
                runs.append(current); current = []
        if current: runs.append(current)
        return runs

    def _issue(self, kind, region_id, targets, severity, confidence, evidence):
        return {"issue_id": f"issue-{kind}-{targets[0]}", "type": kind, "region_id": region_id, "target_event_ids": targets, "severity": round(severity, 6), "detection_confidence": round(confidence, 6), "evidence": evidence}

    def _decisions(self, issues, regions, hypotheses, events):
        trail = AuditTrail()
        region_map = {r.region_id: r for r in regions}
        hypothesis_map = {h["region_id"]: h for h in hypotheses}
        event_map = {e.event_id: e for e in events}
        applied_by_region: dict[str, int] = {}
        for number, issue in enumerate(issues):
            region = region_map[issue["region_id"]]
            hypothesis = hypothesis_map[issue["region_id"]]
            confidence = float(issue["detection_confidence"])
            target = event_map[issue["target_event_ids"][0]]
            proposed = None
            if issue["type"] == "unexpected_downbeat": proposed = ProposedChange("is_downbeat", True, False)
            elif issue["type"] == "missing_downbeat_candidate": proposed = ProposedChange("is_downbeat", False, True)
            alternatives = tuple(AlternativeHypothesis(f"group_{x['beats_per_group']}_phase_{x['phase']}", float(x["score"])) for x in hypothesis["alternatives"][:3])
            raw_opposition = target.downbeat_probability or 0.0 if issue["type"] == "unexpected_downbeat" else 1.0 - (target.downbeat_probability or 0.0)
            region_event_count = sum(
                region.start_sec <= event.time_sec <= region.end_sec for event in events
            )
            change_budget = max(
                1,
                math.floor(
                    region_event_count
                    * self.config.mutation.max_changed_downbeat_ratio
                ),
            )
            budget_available = applied_by_region.get(region.region_id, 0) < change_budget
            can_apply = proposed is not None and region.status is TrackingStatus.TRACKED and hypothesis["decision"] == "selected" and confidence >= self.config.mutation.apply_threshold and raw_opposition < 0.85 and budget_available
            if self.config.mode is InterpretationMode.CONSERVATIVE_APPLY and can_apply:
                action, mutation = DecisionAction.APPLY, True
                applied_by_region[region.region_id] = applied_by_region.get(region.region_id, 0) + 1
            elif confidence >= self.config.mutation.suggest_threshold and proposed is not None:
                action, mutation = DecisionAction.SUGGEST, False
            else:
                action, mutation = DecisionAction.ABSTAIN, False
            evidence_for = (Evidence("structural_hypothesis", hypothesis["selected"]["score"], "Selected grouping supports the proposed role"),)
            evidence_against = (Evidence("raw_model_downbeat_probability", target.downbeat_probability, "Raw model evidence must not be silently discarded"),)
            reasons = [issue["type"], "tracked_region"]
            if hypothesis["decision"] == "ambiguous": reasons.append("alternative_hypotheses_too_close")
            if not budget_available: reasons.append("change_budget_exhausted")
            if self.config.mode is InterpretationMode.OBSERVE_ONLY: reasons.append("observe_only_no_mutation")
            trail.append(RuleDecision(
                decision_id=f"decision-{number:06d}", actor=Actor("rule_engine", "conservative-rhythm-interpreter", self.config.ruleset_version),
                rule=RuleIdentity(issue["type"], "1.0.0"), stage="rhythm_interpretation", action=action,
                target_event_ids=tuple(issue["target_event_ids"]), decision_confidence=confidence,
                thresholds={"apply": self.config.mutation.apply_threshold, "suggest": self.config.mutation.suggest_threshold},
                reason_codes=tuple(reasons), evidence_for=evidence_for, evidence_against=evidence_against,
                alternatives=alternatives, proposed_change=proposed, region_id=region.region_id, mutation_applied=mutation,
            ))
        return trail

    def _final_events(self, events, audit):
        applied = {target: decision for decision in audit.records if decision.mutation_applied for target in decision.target_event_ids}
        result = []
        for event in events:
            decision = applied.get(event.event_id)
            is_down = event.raw_is_downbeat
            source, decision_id = "model", None
            if decision and decision.proposed_change:
                is_down = bool(decision.proposed_change.after)
                source, decision_id = "structure_inference", decision.decision_id
            result.append({"event_id": event.event_id, "time_sec": event.time_sec, "is_downbeat": is_down, "source": source, "decision_id": decision_id})
        return result

    def _unchanged_event(self, event):
        return {"event_id": event.event_id, "time_sec": event.time_sec, "is_downbeat": event.raw_is_downbeat, "source": "model", "decision_id": None}

    def _structure_consistency(self, events, hypotheses, raw):
        return self._consistency([{"event_id": e.event_id, "is_downbeat": e.raw_is_downbeat} for e in events], hypotheses)

    def _structure_consistency_from_final(self, events, hypotheses):
        return self._consistency(events, hypotheses)

    def _consistency(self, event_values, hypotheses):
        expected = set()
        for h in hypotheses:
            expected.update(h["selected"].get("expected_event_ids", ()))
        if not expected: return None
        actual = {x["event_id"] for x in event_values if x["is_downbeat"]}
        return round(len(expected & actual) / len(expected | actual), 6) if expected | actual else None

    def _summary(self, events, regions, issues, audit, before, after):
        duration = max((e.time_sec for e in events), default=0.0)
        by_status = {s.value: 0.0 for s in TrackingStatus}
        total_region = sum(r.end_sec-r.start_sec for r in regions)
        for r in regions: by_status[r.status.value] += r.end_sec-r.start_sec
        percentages = {k: round(v / total_region, 6) if total_region else 0.0 for k, v in by_status.items()}
        actions = {a.value: sum(d.action is a for d in audit.records) for a in DecisionAction}
        return {"raw_beats": len(events), "raw_downbeats": sum(e.raw_is_downbeat for e in events), "tracking_ratio": percentages, "issues": len(issues), "actions": actions, "changed_roles": sum(d.mutation_applied for d in audit.records), "structural_effect": {"before": before, "after": after, "improved": before is not None and after is not None and after > before}}

    def _window_dict(self, window):
        return {"start_sec": round(window.start_sec, 6), "end_sec": round(window.end_sec, 6), "beat_indices": list(window.beat_indices), "scores": {"activation_support": round(window.activation_support, 6), "interval_stability": round(window.interval_stability, 6), "sequence_support": round(window.sequence_support, 6), "overall": round(window.overall, 6)}, "classification": window.classification.value}
