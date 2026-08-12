"use client";

import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

const Tabs = TabsPrimitive.Root;

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      "inline-flex h-11 items-center justify-center gap-1 rounded-[var(--radius-md,0.5rem)]",
      "border border-[var(--border)] bg-[var(--surface-2)] p-1 text-[var(--muted)]",
      className,
    )}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "inline-flex items-center justify-center whitespace-nowrap rounded-[calc(var(--radius-md,0.5rem)-2px)]",
      "px-3 py-1.5 text-sm font-medium transition-colors",
      "disabled:pointer-events-none disabled:opacity-50",
      "data-[state=active]:bg-[var(--surface)] data-[state=active]:text-[var(--accent)]",
      "data-[state=active]:shadow-[var(--shadow-sm,0_1px_2px_rgba(0,0,0,0.06))]",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
      "focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]",
      className,
    )}
    {...props}
  />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      "mt-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
      "focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]",
      className,
    )}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;

export { Tabs, TabsList, TabsTrigger, TabsContent };
