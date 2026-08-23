import numpy as np

from app.rhythm_interpretation import (
    InterpretationMode,
    RhythmInterpretationConfig,
    RhythmInterpreter,
)


def evidence(beats, down_indices, duration, beat_probability=0.95, down_high=0.95, down_low=0.08, mode=InterpretationMode.OBSERVE_ONLY):
    fps = 50.0
    frames = int(duration * fps) + 2
    beat_logits = np.full(frames, -5.0)
    down_logits = np.full(frames, np.log(down_low / (1 - down_low)))
    beat_logit = np.log(beat_probability / (1 - beat_probability))
    high_logit = np.log(down_high / (1 - down_high))
    for i, t in enumerate(beats):
        beat_logits[round(t * fps)] = beat_logit
        if i in down_indices:
            down_logits[round(t * fps)] = high_logit
    downs = [beats[i] for i in down_indices]
    return RhythmInterpreter(RhythmInterpretationConfig(mode=mode)).analyze(
        beats, downs, duration, fps, beat_logits, down_logits
    )


def test_silent_intro_remains_untracked_and_grid_does_not_backfill():
    beats = [12 + i * 0.5 for i in range(32)]
    result = evidence(beats, set(range(0, 32, 4)), 30)
    regions = result["tracking"]["regions"]
    assert regions[0]["status"] == "untracked"
    assert regions[0]["start_sec"] == 0
    tracked = [r for r in regions if r["status"] == "tracked"]
    assert tracked
    assert tracked[0]["start_sec"] >= 12
    assert all(e["time_sec"] >= 12 for e in result["final"]["events"])


def test_random_sparse_intro_peaks_do_not_establish_tracking():
    beats = [1.1, 2.9, 3.15, 5.8, 6.04, 9.7]
    result = evidence(beats, {0, 3}, 12, beat_probability=0.58)
    assert result["summary"]["tracking_ratio"]["tracked"] == 0
    assert result["hypotheses"] == []
    assert result["decisions"] == []


def test_observe_only_detects_but_never_mutates_unexpected_downbeat():
    beats = [i * 0.5 for i in range(32)]
    downs = set(range(0, 32, 4)) | {2}
    result = evidence(beats, downs, 16)
    assert any(i["type"] == "unexpected_downbeat" for i in result["issues"])
    assert all(not d["mutation_applied"] for d in result["decisions"])
    raw_roles = [e["raw_is_downbeat"] for e in result["raw_model"]["events"]]
    final_roles = [e["is_downbeat"] for e in result["final"]["events"]]
    assert final_roles == raw_roles
    assert result["guarantees"]["timestamps_changed"] is False


def test_every_decision_exposes_rule_evidence_alternatives_and_thresholds():
    beats = [i * 0.5 for i in range(32)]
    result = evidence(beats, set(range(0, 32, 4)) | {2}, 16)
    decision = result["decisions"][0]
    assert decision["rule"]["id"]
    assert decision["rule"]["version"] == "1.0.0"
    assert decision["evidence_for"]
    assert decision["evidence_against"]
    assert "apply" in decision["thresholds"]
    assert "suggest" in decision["thresholds"]


def test_dropout_is_reported_without_inventing_beats():
    beats = [i * 0.5 for i in range(40)]
    downs = {0, 4, 8, 28, 32, 36}
    result = evidence(beats, downs, 20)
    assert any(i["type"] == "downbeat_dropout" for i in result["issues"])
    assert len(result["final"]["events"]) == len(beats)
    assert [e["time_sec"] for e in result["final"]["events"]] == beats


def test_randomized_observation_never_changes_membership_or_timing():
    rng = np.random.default_rng(42)
    for _ in range(100):
        count = int(rng.integers(0, 80))
        intervals = rng.uniform(0.15, 1.8, size=count)
        beats = np.cumsum(intervals).tolist()
        duration = (beats[-1] + 1) if beats else 4.0
        downs = {i for i in range(count) if rng.random() < 0.2}
        result = evidence(beats, downs, duration, beat_probability=0.55)
        raw = result["raw_model"]["events"]
        final = result["final"]["events"]
        assert [event["event_id"] for event in final] == [event["event_id"] for event in raw]
        assert [event["time_sec"] for event in final] == [event["time_sec"] for event in raw]
        assert [event["is_downbeat"] for event in final] == [event["raw_is_downbeat"] for event in raw]
        assert all(not decision["mutation_applied"] for decision in result["decisions"])


def test_off_mode_is_an_explicit_noop_with_raw_evidence():
    beats = [i * 0.5 for i in range(8)]
    result = evidence(beats, {0, 4}, 4, mode=InterpretationMode.OFF)
    assert result["mode"] == "off"
    assert result["tracking"]["regions"] == []
    assert result["raw_model"]["events"]
    assert result["correctness_verdict"] == "unknown"
