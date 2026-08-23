import numpy as np
import pytest

from app.rhythm_interpretation import (
    Actor,
    AuditTrail,
    DecisionAction,
    Evidence,
    InterpretationMode,
    ProposedChange,
    RhythmInterpretationConfig,
    RuleDecision,
    RuleIdentity,
    TrackingRegion,
    TrackingStatus,
    sigmoid_logits,
)


def decision(**overrides):
    values = {
        "decision_id": "decision-1",
        "actor": Actor("rule_engine", "rhythm-interpreter", "1.0.0"),
        "rule": RuleIdentity("unexpected-downbeat", "1.0.0"),
        "stage": "rhythm_interpretation",
        "action": DecisionAction.ABSTAIN,
        "target_event_ids": ("beat-1",),
        "decision_confidence": 0.58,
        "thresholds": {"apply": 0.9, "suggest": 0.7},
        "reason_codes": ("alternatives_too_close",),
        "evidence_for": (Evidence("meter_consistency", 0.9, "Supports grouping"),),
    }
    values.update(overrides)
    return RuleDecision(**values)


def test_sigmoid_is_stable_and_preserves_shape():
    result = sigmoid_logits(np.array([-1000.0, 0.0, 1000.0]))
    assert result.shape == (3,)
    assert result[0] == pytest.approx(0.0)
    assert result[1] == pytest.approx(0.5)
    assert result[2] == pytest.approx(1.0)


def test_sigmoid_rejects_non_finite_evidence():
    with pytest.raises(ValueError, match="finite"):
        sigmoid_logits([0.0, np.nan])


def test_config_defaults_to_observation_and_forbids_destructive_changes():
    config = RhythmInterpretationConfig()
    assert config.mode is InterpretationMode.OBSERVE_ONLY
    assert config.to_dict()["mutation"] == {
        "apply_threshold": 0.9,
        "suggest_threshold": 0.7,
        "max_changed_downbeat_ratio": 0.1,
        "allow_timestamp_changes": False,
        "allow_beat_insertion": False,
        "allow_beat_deletion": False,
    }


def test_v1_config_cannot_enable_timestamp_changes():
    from app.rhythm_interpretation.config import MutationConfig

    with pytest.raises(ValueError, match="forbids"):
        RhythmInterpretationConfig(mutation=MutationConfig(allow_timestamp_changes=True))


def test_audit_trail_is_append_only_and_rejects_duplicate_ids():
    trail = AuditTrail()
    original = decision()
    trail.append(original)
    snapshot = trail.records
    assert snapshot == (original,)
    with pytest.raises(ValueError, match="Duplicate"):
        trail.append(original)
    assert trail.records == snapshot


def test_only_apply_can_report_mutation():
    with pytest.raises(ValueError, match="Only an apply"):
        decision(mutation_applied=True, proposed_change=ProposedChange("is_downbeat", True, False))


def test_applied_change_requires_explicit_description():
    with pytest.raises(ValueError, match="describe"):
        decision(action=DecisionAction.APPLY, mutation_applied=True)


def test_decision_serialization_exposes_action_rule_and_evidence():
    value = decision().to_dict()
    assert value["action"] == "abstain"
    assert value["rule"] == {"id": "unexpected-downbeat", "version": "1.0.0"}
    assert value["evidence_for"][0]["type"] == "meter_consistency"


def test_region_must_explain_classification():
    with pytest.raises(ValueError, match="explain"):
        TrackingRegion("r1", 0, 8, TrackingStatus.UNTRACKED, 0.9, ())


def test_valid_untracked_region_is_explicit_not_a_no_beat_claim():
    region = TrackingRegion(
        "r1",
        0,
        8,
        TrackingStatus.UNTRACKED,
        0.9,
        ("insufficient_periodic_pulse",),
    )
    assert region.to_dict()["status"] == "untracked"
