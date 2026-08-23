import React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/cn";

const badgeVariants = cva("inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium", {
  variants: { tone: {
    neutral: "bg-ink-100 text-ink-700",
    good: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200",
    warn: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200",
    bad: "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200",
    info: "bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-200",
  }}, defaultVariants: { tone: "neutral" }
});

export function Badge({ className, tone, ...props }: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
