"use client";

import {
  useCallback,
  useEffect,
  useId,
  type ReactNode,
} from "react";
import { Command } from "cmdk";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../dialogs/modal";

export type CommandPaletteItem = {
  id: string;
  label: string;
  onSelect: () => void;
  keywords?: string;
  group?: string;
  icon?: ReactNode;
};

export type CommandPaletteProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  items: CommandPaletteItem[];
  placeholder?: string;
  emptyMessage?: string;
  enableShortcut?: boolean;
  className?: string;
  title?: string;
};

export function CommandPalette({
  open,
  onOpenChange,
  items,
  placeholder = "Search commands…",
  emptyMessage = "No results found.",
  enableShortcut = false,
  className,
  title = "Command palette",
}: CommandPaletteProps) {
  const titleId = useId();

  const onKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enableShortcut) return;
      const isMod = event.metaKey || event.ctrlKey;
      if (isMod && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onOpenChange(!open);
      }
    },
    [enableShortcut, onOpenChange, open],
  );

  useEffect(() => {
    if (!enableShortcut) return;
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [enableShortcut, onKeyDown]);

  const groups = items.reduce<Record<string, CommandPaletteItem[]>>(
    (acc, item) => {
      const key = item.group ?? "Commands";
      (acc[key] ??= []).push(item);
      return acc;
    },
    {},
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn("overflow-hidden p-0 sm:max-w-lg", className)}
        aria-labelledby={titleId}
      >
        <DialogHeader className="sr-only">
          <DialogTitle id={titleId}>{title}</DialogTitle>
          <DialogDescription>Search and run a command.</DialogDescription>
        </DialogHeader>
        <Command
          className="flex max-h-[min(70vh,28rem)] flex-col bg-[var(--surface)] text-[var(--fg)]"
          label={title}
        >
          <div className="flex items-center gap-2 border-b border-[var(--border)] px-3">
            <Search className="size-4 shrink-0 text-[var(--muted)]" aria-hidden />
            <Command.Input
              placeholder={placeholder}
              className="h-11 w-full bg-transparent text-sm outline-none placeholder:text-[var(--muted)]"
            />
          </div>
          <Command.List className="flex-1 overflow-y-auto p-2">
            <Command.Empty className="px-2 py-6 text-center text-sm text-[var(--muted)]">
              {emptyMessage}
            </Command.Empty>
            {Object.entries(groups).map(([group, groupItems]) => (
              <Command.Group
                key={group}
                heading={group}
                className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-[var(--muted)]"
              >
                {groupItems.map((item) => (
                  <Command.Item
                    key={item.id}
                    value={`${item.label} ${item.keywords ?? ""}`}
                    onSelect={() => {
                      item.onSelect();
                      onOpenChange(false);
                    }}
                    className="flex cursor-pointer items-center gap-2 rounded-[var(--radius-md)] px-2 py-2 text-sm aria-selected:bg-[var(--surface-2)]"
                  >
                    {item.icon ? (
                      <span className="inline-flex size-4 shrink-0" aria-hidden>
                        {item.icon}
                      </span>
                    ) : null}
                    {item.label}
                  </Command.Item>
                ))}
              </Command.Group>
            ))}
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
