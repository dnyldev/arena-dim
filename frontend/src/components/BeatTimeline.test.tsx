import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { BeatTimeline } from "./BeatTimeline";
import type { AnalysisResult } from "../types";

function makeResult(
  beats: number[],
  downbeats: number[],
  numbers: number[],
  duration: number
): AnalysisResult {
  return {
    schema_version: "1.0",
    audio: {
      duration_sec: duration,
      original_sr: 44100,
      channels: 2,
      processed_sr: 22050,
      format: "wav",
      codec: null,
    },
    engine: { name: "mock" },
    config: { device: "cpu" },
    fps: 50,
    beats,
    downbeats,
    beat_numbers: numbers,
    tempo: {
      bpm: 120,
      origin: "derived",
      method: "median_ibi",
      median_ibi_sec: 0.5,
      min_bpm: 120,
      max_bpm: 120,
      curve_window_beats: 8,
      curve: [],
    },
    meter: {
      beats_per_bar: 4,
      origin: "estimated",
      method: "downbeat_interval_mode",
      confidence: 1,
      per_bar: [4],
      is_stable: true,
    },
    rhythm: {
      beat_density_beats_per_second: 2,
      mean_ibi_sec: 0.5,
      std_ibi_sec: 0,
      irregularity: 0,
    },
    counts: { beats: beats.length, downbeats: downbeats.length },
    timing_ms: { total: 100 },
    validation: { ok: true, issues: [] },
    artifacts: {},
  };
}

describe("BeatTimeline", () => {
  it("renders one marker per beat", () => {
    const r = makeResult(
      [0.5, 1.0, 1.5, 2.0],
      [0.5, 2.0],
      [1, 2, 3, 1],
      2.5
    );
    const { container } = render(<BeatTimeline result={r} />);
    const markers = container.querySelectorAll("[data-testid='beat-marker']");
    expect(markers.length).toBe(4);
  });

  it("shows empty state when no beats", () => {
    const r = makeResult([], [], [], 2.0);
    const { getByText } = render(<BeatTimeline result={r} />);
    expect(getByText(/No beats to display/i)).toBeInTheDocument();
  });
});
