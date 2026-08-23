import React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { HelpCircle } from "lucide-react";
import { cn } from "../../lib/cn";

export const TooltipProvider = TooltipPrimitive.Provider;

export function Tooltip({ content, children, className }: { content: React.ReactNode; children: React.ReactNode; className?: string }) {
  return <TooltipPrimitive.Root><TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger><TooltipPrimitive.Portal><TooltipPrimitive.Content sideOffset={6} className={cn("z-50 max-w-xs rounded-lg bg-ink-900 px-3 py-2 text-xs leading-5 text-white shadow-xl data-[state=delayed-open]:animate-in", className)}>{content}<TooltipPrimitive.Arrow className="fill-ink-900" /></TooltipPrimitive.Content></TooltipPrimitive.Portal></TooltipPrimitive.Root>;
}

export function HelpTooltip({ content, label = "More information" }: { content: React.ReactNode; label?: string }) {
  return <Tooltip content={content}><button type="button" aria-label={label} className="inline-flex rounded-full text-ink-400 hover:text-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"><HelpCircle className="h-4 w-4" /></button></Tooltip>;
}
