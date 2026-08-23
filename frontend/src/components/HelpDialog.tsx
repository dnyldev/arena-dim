import React from "react";
import { HelpCircle } from "lucide-react";
import { Button, Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui";

export function HelpButton({ onClick }: { onClick: () => void }) {
  return <Button type="button" variant="outline" size="icon" onClick={onClick} aria-label="Open analysis guide" title="Concepts, rules, and guarantees"><HelpCircle className="h-4 w-4" /></Button>;
}

export function HelpDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  return <Dialog open={open} onOpenChange={(next) => !next && onClose()}><DialogContent>
    <header className="border-b border-ink-100 px-6 py-4 pr-12"><DialogTitle>Analysis guide</DialogTitle><DialogDescription className="mt-1">What the data means, and what the system is allowed to change.</DialogDescription></header>
    <div className="space-y-5 px-6 py-5 text-sm leading-6 text-ink-700">
      <GuideSection title="Raw evidence is preserved">Model beats, downbeats, logits, and timestamps remain available. Interpretation never silently overwrites the original evidence.</GuideSection>
      <GuideSection title="Timing and musical role are different">A sound can be anchored at the correct time while its role—ordinary beat, downbeat, or beat number—remains uncertain. The first interpretation version may change a role, but cannot move, insert, or delete a beat.</GuideSection>
      <GuideSection title="Tracked, uncertain, and untracked">Meter and downbeat rules run only where a sustained pulse is reliable. “Untracked” means the system cannot confidently follow the pulse; it does not claim that the music has no rhythm.</GuideSection>
      <GuideSection title="Apply, suggest, or abstain">A rule applies only after strict safety checks. Conflicting evidence becomes a visible suggestion or abstention instead of a fabricated answer.</GuideSection>
      <GuideSection title="Complete audit trail">Every rule evaluation records its version, target, thresholds, evidence for and against, alternatives, confidence, and whether a mutation was actually applied.</GuideSection>
      <GuideSection title="Regular is not automatically correct">Structural consistency can be measured before and after interpretation, but correctness remains unknown until confirmed by a human or reference annotation.</GuideSection>
      <div className="rounded-lg border border-brand-200 bg-brand-50 p-4 text-xs text-brand-800">Advanced evidence lives in focused inspectors and optional laboratory layers, so the main workflow stays clean while every technical detail remains accessible.</div>
    </div>
  </DialogContent></Dialog>;
}

function GuideSection({ title, children }: { title: string; children: React.ReactNode }) {
  return <section><h3 className="font-semibold text-ink-900">{title}</h3><p className="mt-1">{children}</p></section>;
}
