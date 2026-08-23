import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RhythmInterpretation } from "../types";
import { RhythmLaboratory } from "./RhythmLaboratory";

const interpretation: RhythmInterpretation = {
  schema_version: "1.0",
  mode: "observe_only",
  ruleset: { id: "conservative-rhythm-v1", version: "1.0.0", configuration: {} },
  guarantees: { raw_immutable: true, timestamps_changed: false, beats_inserted: 0, beats_deleted: 0 },
  tracking: { regions: [{ region_id: "r1", start_sec: 0, end_sec: 8, status: "untracked", status_confidence: 0.9, reason_codes: ["insufficient_periodic_pulse"] }] },
  issues: [{ issue_id: "i1", type: "unexpected_downbeat", detection_confidence: 0.81 }],
  decisions: [{
    decision_id: "d1",
    actor: { type: "rule_engine", name: "interpreter", version: "1.0.0" },
    rule: { id: "unexpected-downbeat", version: "1.0.0" },
    action: "abstain",
    target_event_ids: ["beat-2"],
    decision_confidence: 0.81,
    thresholds: { apply: 0.9, suggest: 0.7 },
    reason_codes: ["strong_raw_evidence"],
    evidence_for: [{ type: "structure", value: 0.9, description: "Structure disagrees" }],
    evidence_against: [{ type: "model", value: 0.93, description: "Model strongly supports it" }],
    alternatives: [{ hypothesis: "local_2_group", score: 0.78 }],
    mutation_applied: false,
  }],
  summary: { tracking_ratio: { tracked: 0, uncertain: 0, untracked: 1 }, issues: 1, actions: { abstain: 1 }, changed_roles: 0, structural_effect: { before: 0.5, after: 0.5, improved: false } },
  correctness_verdict: "unknown",
};

describe("RhythmLaboratory", () => {
  it("keeps details collapsed while showing an honest summary", () => {
    render(<RhythmLaboratory interpretation={interpretation} />);
    expect(screen.getByText("correctness:")).toBeInTheDocument();
    expect(screen.queryByText("Rule log")).not.toBeInTheDocument();
  });

  it("reveals complete evidence through progressive disclosure", () => {
    render(<RhythmLaboratory interpretation={interpretation} />);
    fireEvent.click(screen.getByRole("button", { name: "Open laboratory" }));
    expect(screen.getByText("Safety guarantees")).toBeInTheDocument();
    fireEvent.click(screen.getByText("unexpected-downbeat@1.0.0"));
    expect(screen.getByText("Evidence for")).toBeInTheDocument();
    expect(screen.getByText("Evidence against")).toBeInTheDocument();
    expect(screen.getByText(/Model strongly supports it/)).toBeInTheDocument();
    expect(screen.getByText(/Mutation applied:/)).toBeInTheDocument();
  });
});
