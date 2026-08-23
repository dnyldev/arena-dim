import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProcessingPanel } from "./ProcessingPanel";

const props = { events: [], progress: { stage: "", pct: null }, phase: "idle" };

describe("ProcessingPanel", () => {
  it("keeps technical complexity collapsed by default", () => {
    render(<ProcessingPanel {...props} />);
    expect(screen.getByText("0%")).toBeInTheDocument();
    expect(screen.queryByText("Event log")).not.toBeInTheDocument();
  });

  it("makes the complete event pipeline available on demand", () => {
    render(<ProcessingPanel {...props} />);
    fireEvent.click(screen.getByRole("button", { name: "Technical details" }));
    expect(screen.getByText("Event log")).toBeInTheDocument();
    expect(screen.getByText("Stages")).toBeInTheDocument();
    expect(screen.getByText("Waiting for events…")).toBeInTheDocument();
  });
});
