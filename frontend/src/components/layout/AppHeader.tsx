import React from "react";
import { Activity, Cpu, Music2 } from "lucide-react";
import type { Health } from "../../types";
import { Badge } from "../ui";
import { HelpButton } from "../HelpDialog";

export function AppHeader({ health, onOpenHelp }: { health: Health | null; onOpenHelp: () => void }) {
  return <header className="sticky top-0 z-40 border-b border-ink-200/80 bg-white/90 backdrop-blur-xl"><div className="mx-auto flex max-w-[1440px] items-center justify-between px-4 py-3 sm:px-6">
    <div className="flex min-w-0 items-center gap-3"><div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm"><Music2 className="h-5 w-5" /></div><div className="min-w-0"><h1 className="truncate text-sm font-semibold tracking-tight text-ink-900 sm:text-base">Beat Analysis Laboratory</h1><p className="hidden text-xs text-ink-500 sm:block">Auditable, CPU-only rhythm intelligence</p></div></div>
    <div className="flex items-center gap-2"><div className="hidden items-center gap-2 lg:flex">{health && <><Badge tone="good"><Cpu className="mr-1 h-3 w-3" />CPU</Badge><Badge tone={health.beat_this_installed ? "good" : "warn"}>model {health.beat_this_installed ? "available" : "missing"}</Badge><Badge tone={health.status === "ok" ? "good" : "bad"}><Activity className="mr-1 h-3 w-3" />API {health.status}</Badge><span className="text-xs text-ink-400">v{health.version}</span></>}</div><HelpButton onClick={onOpenHelp} /></div>
  </div></header>;
}

export function SystemFooter({ health }: { health: Health | null }) {
  return <footer className="mt-10 border-t border-ink-200 py-5 text-xs text-ink-400"><div className="flex flex-wrap gap-x-6 gap-y-1"><span>audio: {health?.audio_backends.join(", ") || "—"}</span><span>device: {health?.device || "—"}</span><span>uptime: {health ? `${health.uptime_sec.toFixed(0)}s` : "—"}</span></div></footer>;
}
