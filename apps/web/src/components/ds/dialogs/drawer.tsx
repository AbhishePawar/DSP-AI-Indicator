"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Dialog, DialogOverlay, DialogPortal } from "./modal";

export type DrawerSide = "left" | "right";

export type DrawerProps = ComponentPropsWithoutRef<typeof DialogPrimitive.Root>;

export function Drawer(props: DrawerProps) {
  return <Dialog {...props} />;
}

export type DrawerContentProps = ComponentPropsWithoutRef<
  typeof DialogPrimitive.Content
> & {
  side?: DrawerSide;
  title?: string;
  description?: string;
  showClose?: boolean;
  children?: ReactNode;
};

export function DrawerContent({
  side = "right",
  title,
  description,
  showClose = true,
  className,
  children,
  ...props
}: DrawerContentProps) {
  return (
    <DialogPortal>
      <DialogOverlay />
      <DialogPrimitive.Content
        className={cn(
          "fixed top-0 z-50 flex h-full w-full max-w-sm flex-col border-[var(--border)] bg-[var(--surface)] text-[var(--fg)] shadow-[var(--shadow-md)] outline-none",
          side === "left"
            ? "left-0 border-r"
            : "right-0 border-l",
          className,
        )}
        {...props}
      >
        {(title || description || showClose) && (
          <div className="flex items-start justify-between gap-3 border-b border-[var(--border)] px-4 py-3">
            <div className="min-w-0">
              {title ? (
                <DialogPrimitive.Title className="font-[family-name:var(--font-display)] text-lg tracking-tight">
                  {title}
                </DialogPrimitive.Title>
              ) : (
                <DialogPrimitive.Title className="sr-only">
                  Drawer
                </DialogPrimitive.Title>
              )}
              {description ? (
                <DialogPrimitive.Description className="mt-1 text-sm text-[var(--muted)]">
                  {description}
                </DialogPrimitive.Description>
              ) : (
                <DialogPrimitive.Description className="sr-only">
                  Side panel
                </DialogPrimitive.Description>
              )}
            </div>
            {showClose ? (
              <DialogPrimitive.Close
                className="inline-flex size-8 shrink-0 items-center justify-center rounded-[var(--radius-md)] text-[var(--muted)] transition hover:bg-[var(--surface-2)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                aria-label="Close"
              >
                <X className="size-4" aria-hidden />
              </DialogPrimitive.Close>
            ) : null}
          </div>
        )}
        <div className="flex-1 overflow-y-auto px-4 py-4">{children}</div>
      </DialogPrimitive.Content>
    </DialogPortal>
  );
}

export const DrawerTrigger = DialogPrimitive.Trigger;
export const DrawerClose = DialogPrimitive.Close;
