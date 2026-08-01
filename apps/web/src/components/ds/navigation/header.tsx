import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

export type HeaderProps = HTMLAttributes<HTMLElement> & {
  left?: ReactNode;
  center?: ReactNode;
  right?: ReactNode;
};

export function Header({
  left,
  center,
  right,
  className,
  children,
  ...props
}: HeaderProps) {
  return (
    <header
      className={cn(
        "sticky top-0 z-40 flex h-14 items-center gap-3 border-b border-[var(--border)] bg-[var(--surface)] px-4 text-[var(--fg)]",
        className,
      )}
      {...props}
    >
      <div className="flex min-w-0 flex-1 items-center gap-2">{left}</div>
      {center ? (
        <div className="hidden min-w-0 flex-1 items-center justify-center md:flex">
          {center}
        </div>
      ) : null}
      <div className="flex min-w-0 flex-1 items-center justify-end gap-2">
        {right}
      </div>
      {children}
    </header>
  );
}
