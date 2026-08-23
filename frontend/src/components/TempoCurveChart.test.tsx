import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { TempoCurveChart } from "./TempoCurveChart";

describe("TempoCurveChart", () => {
  it("renders the empty state when there is no curve data", () => {
    const { getByText } = render(
      <TempoCurveChart
        curve={[]}
        overallBpm={null}
        windowBeats={null}
        durationSec={10}
      />
    );
    expect(getByText(/Not enough beats/i)).toBeInTheDocument();
  });

  it("renders a point per curve sample and the window hint", () => {
    const curve = [
      { time_sec: 1.0, bpm: 120 },
      { time_sec: 2.0, bpm: 121 },
      { time_sec: 3.0, bpm: 119 },
    ];
    const { container, getByText } = render(
      <TempoCurveChart
        curve={curve}
        overallBpm={120}
        windowBeats={8}
        durationSec={4}
      />
    );
    const dots = container.querySelectorAll("circle");
    expect(dots.length).toBe(3);
    expect(getByText(/window: 8 beats/i)).toBeInTheDocument();
  });
});
