import React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "../../lib/cn";

export const Tabs = TabsPrimitive.Root;
export const TabsContent = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>>(function TabsContent({ className, ...props }, ref) { return <TabsPrimitive.Content ref={ref} className={cn("mt-5 focus-visible:outline-none", className)} {...props} />; });
export function TabsList({ className, ...props }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>) { return <TabsPrimitive.List className={cn("inline-flex rounded-lg border border-ink-200 bg-ink-50 p-1", className)} {...props} />; }
export function TabsTrigger({ className, ...props }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>) { return <TabsPrimitive.Trigger className={cn("rounded-md px-3 py-1.5 text-xs font-medium text-ink-500 transition hover:text-ink-900 data-[state=active]:bg-white data-[state=active]:text-ink-900 data-[state=active]:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500", className)} {...props} />; }
