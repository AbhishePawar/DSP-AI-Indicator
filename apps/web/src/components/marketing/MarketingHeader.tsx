"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";

import { MoonStar } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthProvider";
import { env } from "@/lib/env";
import { useTheme } from "@/providers/ThemeProvider";

import { MARKETING_NAV } from "./content";

export function MarketingHeader() {
  const { user, logout } = useAuth();
  const { cycleMode, resolved, mode } = useTheme();
  const [open, setOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const menuId = useId();
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!userMenuOpen) return;
    function handleClickOutside(event: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [userMenuOpen]);

  useEffect(() => {
    if (!open) return;

    const panel = panelRef.current;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const focusables = () =>
      panel
        ? Array.from(
            panel.querySelectorAll<HTMLElement>(
              'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
            ),
          )
        : [];

    const first = focusables()[0];
    first?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        menuButtonRef.current?.focus();
        return;
      }
      if (event.key !== "Tab" || !panel) return;
      const items = focusables();
      if (!items.length) return;
      const firstEl = items[0]!;
      const lastEl = items[items.length - 1]!;
      if (event.shiftKey && document.activeElement === firstEl) {
        event.preventDefault();
        lastEl.focus();
      } else if (!event.shiftKey && document.activeElement === lastEl) {
        event.preventDefault();
        firstEl.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      if (previouslyFocused && document.contains(previouslyFocused)) {
        previouslyFocused.focus();
      }
    };
  }, [open]);

  const themeLabel =
    mode === "system"
      ? `Theme: System (${resolved}). Activate to cycle theme.`
      : `Theme: ${mode}. Activate to cycle theme. Currently showing ${resolved}.`;

  return (
    <header data-testid="marketing-header" className="sticky top-0 z-40 border-b border-[var(--border)] bg-[var(--surface)]">
      <div className="relative flex min-h-[70px] items-center justify-between gap-4 px-5 py-4 sm:px-12">
        <Link
          href="/"
          data-testid="marketing-home"
          aria-label={`${env.appName} home`}
          className="flex items-center gap-2.5 font-[family-name:var(--font-display)] text-lg text-[var(--fg)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
        >
          <span className="size-[26px] rounded-full bg-[linear-gradient(135deg,#7c6af7,#2dd4bf)]" />DSP
        </Link>

        <nav
          aria-label="Marketing"
          className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-1 lg:flex"
        >
          {MARKETING_NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              data-testid={`marketing-nav-${item.label.toLowerCase()}`}
              className="inline-flex items-center rounded-md px-3 py-1.5 text-[13px] text-[var(--muted)] transition-colors hover:text-[var(--fg)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <button data-testid="marketing-theme"
            type="button"
            onClick={cycleMode}
            className="inline-flex size-8 items-center justify-center rounded-full text-[var(--muted)] transition-colors hover:bg-[var(--surface-2)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
            aria-label={themeLabel}
          >
            <MoonStar className="size-3.5" />
          </button>
          {user ? (
            <div className="relative" ref={userMenuRef}>
              <button
                type="button"
                data-testid="marketing-account"
                aria-expanded={userMenuOpen}
                aria-haspopup="true"
                onClick={() => setUserMenuOpen((v) => !v)}
                className="flex min-h-9 max-w-44 items-center gap-2 rounded-lg px-2 text-xs transition-colors hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              >
                <span className="grid size-[26px] shrink-0 place-items-center rounded-full bg-[linear-gradient(135deg,#7c6af7,#2dd4bf)] font-mono text-[10px] font-semibold text-white">
                  {user.displayName.slice(0, 2).toUpperCase()}
                </span>
                <span className="truncate">{user.displayName}</span>
              </button>

              {userMenuOpen ? (
                <div
                  data-testid="marketing-account-menu"
                  role="menu"
                  className="absolute right-0 mt-1.5 w-40 rounded-lg border border-[var(--border)] bg-[var(--surface)] py-1 shadow-lg z-50 text-xs"
                >
                  <Link
                    href="/profile"
                    role="menuitem"
                    data-testid="marketing-account-profile"
                    className="flex w-full items-center px-3 py-2 text-[var(--fg)] hover:bg-[var(--surface-2)]"
                    onClick={() => setUserMenuOpen(false)}
                  >
                    Profile
                  </Link>
                  <button
                    type="button"
                    role="menuitem"
                    data-testid="marketing-account-logout"
                    className="flex w-full items-center px-3 py-2 text-[var(--fg)] hover:bg-[var(--surface-2)] text-left"
                    onClick={async () => {
                      setUserMenuOpen(false);
                      await logout();
                      window.location.assign("/");
                    }}
                  >
                    Logout
                  </button>
                </div>
              ) : null}
            </div>
          ) : (
            <Link
              data-testid="marketing-account"
              href="/login"
              className="flex min-h-9 max-w-44 items-center gap-2 rounded-lg px-2 text-xs transition-colors hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              <span className="truncate">Log in</span>
            </Link>
          )}
          <button
            data-testid="marketing-menu-toggle"
            ref={menuButtonRef}
            type="button"
            className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--border)] px-2.5 text-sm lg:hidden focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
            aria-expanded={open}
            aria-controls={menuId}
            aria-label={open ? "Close navigation menu" : "Open navigation menu"}
            onClick={() => setOpen((v) => !v)}
          >
            Menu
          </button>
        </div>
      </div>

      {open ? (
        <nav
          data-testid="marketing-mobile-menu"
          ref={panelRef}
          id={menuId}
          aria-label="Marketing mobile"
          className="border-t border-[var(--border)] bg-[var(--surface)] px-4 py-3 lg:hidden"
        >
          <ul className="flex flex-col gap-1">
            {MARKETING_NAV.map((item) => (
              <li key={item.href}>
                <Link
                  data-testid={`marketing-mobile-${item.label.toLowerCase()}`}
                  href={item.href}
                  className="flex min-h-11 items-center text-sm text-[var(--fg)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                  onClick={() => setOpen(false)}
                >
                  {item.label}
                </Link>
              </li>
            ))}
            {user ? (
              <>
                <li>
                  <Link
                    href="/profile"
                    data-testid="marketing-mobile-profile"
                    className="flex min-h-11 items-center text-sm text-[var(--fg)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                    onClick={() => setOpen(false)}
                  >
                    Profile ({user.displayName})
                  </Link>
                </li>
                <li>
                  <button
                    type="button"
                    data-testid="marketing-mobile-logout"
                    className="flex min-h-11 w-full items-center text-sm text-[var(--fg)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] text-left"
                    onClick={async () => {
                      setOpen(false);
                      await logout();
                      window.location.assign("/");
                    }}
                  >
                    Logout
                  </button>
                </li>
              </>
            ) : (
              <>
                <li>
                  <Link
                    href="/register"
                    className="flex min-h-11 items-center text-sm text-[var(--fg)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                    onClick={() => setOpen(false)}
                  >
                    Create account
                  </Link>
                </li>
                <li>
                  <Link
                    href="/login"
                    className="flex min-h-11 items-center text-sm text-[var(--accent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                    onClick={() => setOpen(false)}
                  >
                    Sign in
                  </Link>
                </li>
              </>
            )}
          </ul>
        </nav>
      ) : null}
    </header>
  );
}
