import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { HelpButton, HelpDialog } from "./HelpDialog";

describe("analysis guide", () => {
  it("opens through an accessible help control", () => {
    const open = vi.fn();
    render(<HelpButton onClick={open} />);
    fireEvent.click(screen.getByRole("button", { name: /open analysis guide/i }));
    expect(open).toHaveBeenCalledOnce();
  });

  it("explains safety guarantees and closes with Escape", () => {
    const close = vi.fn();
    render(<HelpDialog open onClose={close} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Raw evidence is preserved")).toBeInTheDocument();
    expect(screen.getByText("Regular is not automatically correct")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(close).toHaveBeenCalledOnce();
  });
});
