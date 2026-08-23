# Conservative Rhythm Interpretation — Product & Engineering Charter

**Status:** Accepted implementation charter  
**Initial mode:** `observe_only`  
**Primary rule:** preserve evidence; never silently rewrite musical output.

## 1. Purpose

Beat-model output is evidence, not unquestionable truth and not disposable noise. The product needs a conservative interpretation layer that can make beat/downbeat presentation coherent while respecting audible timing, ambiguous music, meter changes, free intros/outros, and model uncertainty.

This layer must help us understand *why* an output looks wrong before changing it. A mathematically regular grid is not automatically musically correct.

## 2. Non-negotiable guarantees

1. Raw model output is immutable and always retained.
2. Final output is derived reproducibly from raw output, a versioned ruleset, and recorded configuration.
3. No beat timestamp may be moved in v1.
4. No beat may be inserted or deleted in v1.
5. Structural interpretation may only change the role of an existing beat.
6. Every detection, proposal, applied change, rejection, and abstention has an audit record.
7. Every audit record names the actor, stage, rule ID/version, target, evidence for and against, alternatives, thresholds, decision, and mutation status.
8. Low-confidence or conflicting evidence produces `abstain`, not a fabricated answer.
9. Interpretation failure falls back safely to raw output.
10. “More regular” must never be presented as “more correct” without human review or a reference annotation.

## 3. Scope of v1

### Included

- Preserve raw beats, downbeats, frame logits, and probabilities.
- Classify regions as `tracked`, `uncertain`, or `untracked`.
- Evaluate beat-group and phase hypotheses only in trackable regions.
- Detect unexpected downbeats, possible missing downbeats, downbeat dropouts, and possible meter changes.
- Produce `apply`, `suggest`, `abstain`, or `reject_issue` decisions.
- Build a final interpretation from audited `apply` decisions only.
- Report before/after structural effects separately from correctness.
- Provide a laboratory UI with raw/final overlays, region state, evidence, alternatives, and a rule log.

### Explicitly excluded

- Moving timestamps onto a mathematical grid.
- Inventing beats where no reliable audio/model anchor exists.
- Deleting raw evidence.
- Forcing a single meter over an entire track.
- Blindly extending a grid into a free/silent intro or fading outro.
- Hidden rules or hard-coded, unreported thresholds.
- Claiming that a structurally cleaner result is objectively correct.

## 4. Conceptual pipeline

```text
Audio → model evidence → immutable raw result
                           ↓
                  pulse reliability gate
                           ↓
          tracked / uncertain / untracked regions
                           ↓ (tracked only)
              meter/group + phase hypotheses
                           ↓
                    issue detection
                           ↓
       versioned rules: apply/suggest/abstain/reject
                           ↓
        final interpretation + append-only audit trail
```

## 5. Evidence and structure are separate

An audible/model event has a **time anchor** and a **structural role**. These are not the same fact.

- The anchor answers: “where did the evidence occur?”
- The role answers: “is this beat 1/downbeat, beat 2, etc.?”

A role may be reinterpreted without moving its anchor. A nearby sound is not automatically a rhythmic anchor: it must also be supported by a credible pulse sequence.

## 6. Region states

- `tracked`: sustained evidence supports a stable local pulse.
- `uncertain`: some evidence exists, but it is insufficient or contradictory.
- `untracked`: no reliable periodic pulse can be established.

`untracked` means “the system cannot reliably track this region,” not “music or beat definitely does not exist.” Meter/downbeat repair is forbidden outside `tracked` regions.

Tracking uses overlapping windows and hysteresis: starting tracking requires stronger evidence than continuing it; stopping requires sustained weak evidence. Exact thresholds are versioned configuration and are emitted in every result.

## 7. Hypotheses, not assumptions

V1 evaluates group sizes `[2, 3, 4, 6]` and all possible phases. Internally these remain `beats_per_group` candidates; labels such as `4/4` are display candidates, not unquestionable time-signature claims.

Each hypothesis records:

- score and score components;
- supporting events;
- contradicting events;
- local and neighboring continuity;
- alternative hypotheses and winner margin.

A small winner margin requires abstention. An unexpected model downbeat is contrary evidence that must be investigated, not automatically removed.

## 8. Initial issue taxonomy

- `unexpected_downbeat`
- `missing_downbeat_candidate`
- `downbeat_dropout`
- `possible_meter_change`

Detection and mutation are separate stages. Detecting an issue does not authorize changing output.

## 9. Rule decisions

Every rule returns exactly one:

- `apply`: evidence clears strict safety gates; change an existing beat role.
- `suggest`: plausible, visible to the operator, but no mutation.
- `abstain`: insufficient/conflicting evidence; no mutation.
- `reject_issue`: investigation suggests the initial issue is not an error.

`apply` is forbidden when a region is not tracked, confidence is low, alternatives are close, strong model evidence contradicts the change, a possible meter change exists, change budget is exceeded, or a timestamp/beat mutation would be required.

## 10. Audit contract

Audit history is append-only. A decision includes:

```json
{
  "decision_id": "decision-00431",
  "actor": {"type": "rule_engine", "name": "rhythm-interpreter", "version": "1.0.0"},
  "rule": {"id": "unexpected-downbeat", "version": "1.0.0"},
  "stage": "rhythm_interpretation",
  "region_id": "region-003",
  "target_event_ids": ["beat-000043"],
  "action": "abstain",
  "proposed_change": {"field": "is_downbeat", "from": true, "to": false},
  "decision_confidence": 0.58,
  "thresholds": {"apply": 0.90, "suggest": 0.70},
  "reason_codes": ["unexpected_phase_position", "strong_raw_downbeat_evidence"],
  "evidence_for": [{"type": "meter_consistency", "value": 0.91}],
  "evidence_against": [{"type": "raw_downbeat_probability", "value": 0.93}],
  "alternatives": [{"hypothesis": "local_2_group", "score": 0.73}],
  "mutation_applied": false
}
```

A later human review appends a new record referencing the original; it never rewrites history. Actors include `model`, `rule_engine`, `human`, `importer`, and `system`.

## 11. Output contract

Results retain three explicit layers:

1. `raw_model`: untouched model/postprocessor evidence.
2. `rhythm_interpretation`: regions, hypotheses, issues, decisions, ruleset, and metrics.
3. `final`: user-facing role interpretation derived from audited decisions.

Required invariants:

```text
final beat timestamps == raw beat timestamps
final beat count      == raw beat count
all raw event IDs exist in final
all raw/final role differences have an applied audit decision
```

Structural effect and correctness are separate:

```json
{
  "structural_effect": {"before": 0.71, "after": 0.93, "improved": true},
  "correctness_verdict": "unknown"
}
```

Correctness remains `unknown` until human review or reference comparison.

## 12. Operating modes

- `off`: existing behavior; no interpretation.
- `observe_only`: detect, explain, and propose; final remains raw.
- `conservative_apply`: apply only decisions passing all strict gates.

Development starts in `observe_only`. Default activation must not change until real-track review and regression gates approve it.

## 13. Dashboard UX charter

Complexity belongs behind progressive disclosure, not in the operator’s way.

### Default view

- Clean final timeline and essential summary.
- Small, visible indicators for interpreted/uncertain content.
- No wall of diagnostics.

### Laboratory view

Optional layers:

- raw model;
- final interpretation;
- tracking regions;
- issues and decisions;
- confidence/evidence.

Clicking a beat or region opens one focused inspector showing raw values, final role, rule/version, action, evidence for/against, alternatives, and thresholds. A searchable rule log provides the complete history.

### Help system

Every specialist concept gets a nearby `?` affordance. The global help panel explains terminology, states, rules, confidence, evidence, and guarantees. Help must explain both *what* a control does and *why* it exists.

## 14. Implementation stages

1. **Foundation:** immutable models, ruleset config, audit schema, probability extraction, invariants.
2. **Pulse reliability:** window metrics, hysteresis state machine, merged regions.
3. **Hypotheses:** group-size/phase scoring and alternatives.
4. **Issues and rules:** initial taxonomy, conservative decisions, change budgets.
5. **Pipeline and JSON:** orchestrator, artifacts, API, fail-safe behavior.
6. **Laboratory UI:** raw/final layers, regions, inspector, rule log, help.
7. **Hardening:** unit, property, scenario, snapshot, integration, frontend, and regression tests.

## 15. Test and acceptance gates

### Required test classes

- Unit tests for probability, windows, regions, hypotheses, and decisions.
- Property-based tests for immutability and invariants.
- Scenario tests: silent/free intro, random vocal/piano peaks, regular 3/4 and 4/4, beat-3 accent, missing downbeat, dropout, real meter change, chaotic output.
- Deterministic JSON snapshots.
- Full pipeline/API/artifact integration tests.
- Frontend tests for layers, inspectors, abstentions, and untracked regions.
- A permanent regression fixture for every real bug discovered.

### Safety acceptance

- Zero moved timestamps.
- Zero inserted/deleted beats.
- Zero raw mutations.
- Zero applied repairs in untracked regions.
- Zero low-confidence applies.
- 100% of raw/final differences linked to an audit decision.
- 100% of decisions include rule ID/version and recorded configuration.
- Interpretation failure returns raw output safely.

### Honesty acceptance

- `abstain` and uncertainty remain visible in laboratory mode.
- Model and inferred downbeats are distinguishable.
- Structural regularity is never labeled correctness.
- No threshold or rule executes without provenance.

## 16. Change discipline

Any behavioral change must:

1. add or update a failing test first;
2. update the affected rule version;
3. preserve old audit interpretability;
4. run the complete regression corpus;
5. document changed thresholds/logic;
6. show which previous scenarios improved or regressed.

This charter is the implementation authority for rhythm interpretation. If code and this document disagree, the code is considered defective until the charter is deliberately amended and reviewed.
