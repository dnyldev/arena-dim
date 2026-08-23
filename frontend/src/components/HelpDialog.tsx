import React, { useEffect } from "react";

export function HelpButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Open analysis guide"
      title="Concepts, rules, and guarantees"
      className="flex h-8 w-8 items-center justify-center rounded-full border border-ink-200 bg-white text-sm font-bold text-ink-600 transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
    >
      ?
    </button>
  );
}

export function HelpDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="guide-title"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <section className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-ink-200 bg-white shadow-xl">
        <header className="sticky top-0 flex items-start justify-between border-b border-ink-100 bg-white px-6 py-4">
          <div>
            <h2 id="guide-title" className="font-semibold text-ink-900">Analysis guide</h2>
            <p className="mt-1 text-xs text-ink-500">What the data means, and what the system is allowed to change.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded px-2 py-1 text-ink-500 hover:bg-ink-50" aria-label="Close guide">×</button>
        </header>
        <div className="space-y-5 px-6 py-5 text-sm leading-6 text-ink-700">
          <GuideSection title="Raw evidence is preserved">
            Model beats, downbeats, logits, and timestamps remain available. Interpretation never silently overwrites the original evidence.
          </GuideSection>
          <GuideSection title="Timing and musical role are different">
            A sound can be anchored at the correct time while its role—ordinary beat, downbeat, or beat number—remains uncertain. The first interpretation version may change a role, but cannot move, insert, or delete a beat.
          </GuideSection>
          <GuideSection title="Tracked, uncertain, and untracked">
            Meter and downbeat rules run only where a sustained pulse is reliable. “Untracked” means the system cannot confidently follow the pulse; it does not claim that the music has no rhythm.
          </GuideSection>
          <GuideSection title="Apply, suggest, or abstain">
            A rule applies only after strict safety checks. Conflicting evidence becomes a visible suggestion or abstention instead of a fabricated answer.
          </GuideSection>
          <GuideSection title="Complete audit trail">
            Every rule evaluation records its version, target, thresholds, evidence for and against, alternatives, confidence, and whether a mutation was actually applied.
          </GuideSection>
          <GuideSection title="Regular is not automatically correct">
            Structural consistency can be measured before and after interpretation, but correctness remains unknown until confirmed by a human or reference annotation.
          </GuideSection>
          <div className="rounded-lg border border-brand-200 bg-brand-50 p-4 text-xs text-brand-800">
            The dashboard will keep advanced evidence in focused inspectors and optional laboratory layers, so the main workflow stays clean while every technical detail remains accessible.
          </div>
        </div>
      </section>
    </div>
  );
}

function GuideSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="font-semibold text-ink-900">{title}</h3>
      <p className="mt-1">{children}</p>
    </section>
  );
}
