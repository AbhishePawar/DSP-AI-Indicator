"use client";

import type {
  AnchorHTMLAttributes,
  ButtonHTMLAttributes,
  HTMLAttributes,
  ReactNode,
} from "react";
import { cn } from "@/lib/utils";

export type SidebarProps = HTMLAttributes<HTMLElement> & {
  collapsed?: boolean;
};

export function Sidebar({
  collapsed = false,
  className,
  children,
  ...props
}: SidebarProps) {
  return (
    <aside
      data-collapsed={collapsed || undefined}
      aria-label="Sidebar"
      className={cn(
        "flex h-full flex-col border-r border-[var(--border)] bg-[var(--surface)] text-[var(--fg)] transition-[width] duration-200",
        collapsed ? "w-14" : "w-60",
        className,
      )}
      {...props}
    >
      <nav className="flex flex-1 flex-col gap-1 p-2">{children}</nav>
    </aside>
  );
}

export type SidebarGroupProps = HTMLAttributes<HTMLDivElement> & {
  label?: string;
  collapsed?: boolean;
};

export function SidebarGroup({
  label,
  collapsed = false,
  className,
  children,
  ...props
}: SidebarGroupProps) {
  return (
    <div className={cn("flex flex-col gap-1", className)} {...props}>
      {label && !collapsed ? (
        <p className="px-2 pt-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          {label}
        </p>
      ) : null}
      {children}
    </div>
  );
}

type SidebarItemShared = {
  label: string;
  icon?: ReactNode;
  active?: boolean;
  collapsed?: boolean;
  className?: string;
};

export type SidebarItemLinkProps = SidebarItemShared &
  Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "children"> & {
    href: string;
  };

export type SidebarItemButtonProps = SidebarItemShared &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
    href?: undefined;
  };

export type SidebarItemProps = SidebarItemLinkProps | SidebarItemButtonProps;

export function SidebarItem(props: SidebarItemProps) {
  const {
    label,
    icon,
    active = false,
    collapsed = false,
    className,
    ...rest
  } = props;

  const classes = cn(
    "inline-flex min-h-10 items-center gap-2 rounded-[var(--radius-md)] px-2.5 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
    collapsed ? "justify-center" : "justify-start",
    active
      ? "bg-[var(--accent-soft)] text-[var(--accent)]"
      : "text-[var(--fg)] hover:bg-[var(--surface-2)]",
    className,
  );

  const content = (
    <>
      {icon ? (
        <span className="inline-flex size-5 shrink-0 items-center justify-center" aria-hidden>
          {icon}
        </span>
      ) : null}
      {!collapsed ? <span className="truncate">{label}</span> : null}
      {collapsed ? <span className="sr-only">{label}</span> : null}
    </>
  );

  if ("href" in props && props.href !== undefined) {
    const { href, ...anchorRest } = rest as Omit<
      SidebarItemLinkProps,
      "label" | "icon" | "active" | "collapsed" | "className"
    >;
    return (
      <a
        href={href}
        aria-current={active ? "page" : undefined}
        title={collapsed ? label : undefined}
        className={classes}
        {...anchorRest}
      >
        {content}
      </a>
    );
  }

  const buttonRest = rest as Omit<
    SidebarItemButtonProps,
    "label" | "icon" | "active" | "collapsed" | "className"
  >;

  return (
    <button
      type="button"
      aria-current={active ? "page" : undefined}
      title={collapsed ? label : undefined}
      className={classes}
      {...buttonRest}
    >
      {content}
    </button>
  );
}
