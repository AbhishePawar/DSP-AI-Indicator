"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "./modal";

export type CommandDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
};

/**
 * Shell dialog for embedding command-palette (or cmdk) content.
 * Use with CommandPalette content area or custom cmdk trees.
 */
export function CommandDialog({
  open,
  onOpenChange,
  title = "Command palette",
  description = "Search and run a command.",
  children,
  className,
}: CommandDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn("overflow-hidden p-0 sm:max-w-lg", className)}
      >
        <DialogHeader className="sr-only">
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        {children}
      </DialogContent>
    </Dialog>
  );
}
