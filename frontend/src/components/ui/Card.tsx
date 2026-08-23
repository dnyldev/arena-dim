import React from "react";
import { cn } from "../../lib/cn";

export function Card({ title, subtitle, children, actions, className, contentClassName }: { title?: React.ReactNode; subtitle?: React.ReactNode; children?: React.ReactNode; actions?: React.ReactNode; className?: string; contentClassName?: string }) {
  return <section className={cn("rounded-xl border border-ink-200 bg-white shadow-sm", className)}>
    {(title || subtitle || actions) && <header className="flex items-start justify-between gap-4 border-b border-ink-100 px-5 py-4"><div className="min-w-0">{title && <h2 className="text-sm font-semibold text-ink-900">{title}</h2>}{subtitle && <p className="mt-0.5 text-xs text-ink-500">{subtitle}</p>}</div>{actions && <div className="shrink-0">{actions}</div>}</header>}
    <div className={cn("px-5 py-4", contentClassName)}>{children}</div>
  </section>;
}

export function Stat({ label, value, hint, tone = "default" }: { label: string; value: React.ReactNode; hint?: React.ReactNode; tone?: "default" | "good" | "warn" | "bad" }) {
  const colors = { default: "text-ink-900", good: "text-emerald-600", warn: "text-amber-600", bad: "text-rose-600" };
  return <div className="rounded-lg border border-ink-100 bg-ink-50/60 px-4 py-3"><div className="text-[11px] font-medium uppercase tracking-wider text-ink-500">{label}</div><div className={cn("mt-1 text-xl font-semibold", colors[tone])}>{value}</div>{hint && <div className="mt-0.5 text-[11px] text-ink-400">{hint}</div>}</div>;
}
