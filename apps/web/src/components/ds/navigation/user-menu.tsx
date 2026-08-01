"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { ChevronDown, User } from "lucide-react";
import { cn } from "@/lib/utils";

export type UserMenuItem = {
  id: string;
  label: string;
  onSelect: () => void;
  destructive?: boolean;
};

export type UserMenuProps = {
  name: string;
  email?: string;
  items: UserMenuItem[];
  avatar?: ReactNode;
  className?: string;
};

export function UserMenu({
  name,
  email,
  items,
  avatar,
  className,
}: UserMenuProps) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const menuId = `${id}-menu`;
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className={cn("relative", className)} ref={ref}>
      <button
        type="button"
        id={id}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((v) => !v)}
        className="inline-flex min-h-10 items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-sm text-[var(--fg)] transition hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
      >
        <span className="inline-flex size-7 items-center justify-center overflow-hidden rounded-full bg-[var(--surface-2)] text-[var(--muted)]">
          {avatar ?? <User className="size-4" aria-hidden />}
        </span>
        <span className="hidden min-w-0 text-left sm:block">
          <span className="block truncate font-medium leading-tight">{name}</span>
          {email ? (
            <span className="block truncate text-xs text-[var(--muted)]">
              {email}
            </span>
          ) : null}
        </span>
        <ChevronDown className="size-4 text-[var(--muted)]" aria-hidden />
      </button>
      {open ? (
        <div
          id={menuId}
          role="menu"
          aria-labelledby={id}
          className="absolute right-0 z-50 mt-1 min-w-[12rem] rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] py-1 shadow-[var(--shadow-md)]"
        >
          <div className="border-b border-[var(--border)] px-3 py-2 sm:hidden">
            <p className="truncate text-sm font-medium text-[var(--fg)]">{name}</p>
            {email ? (
              <p className="truncate text-xs text-[var(--muted)]">{email}</p>
            ) : null}
          </div>
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                item.onSelect();
              }}
              className={cn(
                "block w-full px-3 py-2 text-left text-sm focus-visible:outline-none focus-visible:bg-[var(--surface-2)] hover:bg-[var(--surface-2)]",
                item.destructive
                  ? "text-[var(--danger-fg)]"
                  : "text-[var(--fg)]",
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
