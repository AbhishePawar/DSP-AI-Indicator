"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { Avatar, AvatarFallback, UserMenu } from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";

export function ResearchShell({ children }: { children: ReactNode }) {
  const { session, user } = useAuth();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const initials = (user?.displayName || "U").slice(0, 2).toUpperCase();
  const menuId = "research-navigation-mobile";

  useEffect(() => {
    if (!menuOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [menuOpen]);

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      <header className="border-b border-[var(--border)] bg-[var(--surface)]/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link
            href="/dashboard"
            className="flex items-center gap-3"
            aria-label="DSP AI Indicator home"
          >
            <span className="grid size-9 place-items-center rounded-[var(--radius-sm)] bg-[var(--accent)] text-sm font-semibold text-[var(--accent-fg)]">
              D
            </span>
            <span>
              <span className="block text-sm font-semibold tracking-[0.08em]">
                DSP AI INDICATOR
              </span>
              <span className="block text-xs text-[var(--muted)]">
                Evidence-first research
              </span>
            </span>
          </Link>
          <button
            type="button"
            className="min-h-11 rounded-[var(--radius-sm)] border border-[var(--border)] px-3 py-2 text-sm md:hidden"
            aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={menuOpen}
            aria-controls={menuId}
            onClick={() => setMenuOpen((open) => !open)}
          >
            Menu
          </button>
          <nav
            id="research-navigation-desktop"
            aria-label="Research navigation"
            className="hidden items-center gap-2 text-sm md:flex"
          >
            <Link
              href="/dashboard"
              className="rounded-[var(--radius-sm)] px-3 py-2 text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
            >
              Search
            </Link>
            {session && user ? (
              <UserMenu
                name={user.displayName}
                email={user.email || undefined}
                avatar={
                  <Avatar className="size-7">
                    <AvatarFallback className="text-[10px]">{initials}</AvatarFallback>
                  </Avatar>
                }
                items={[
                  { id: "profile", label: "Profile", onSelect: () => router.push("/profile") },
                  { id: "settings", label: "Settings", onSelect: () => router.push("/settings") },
                  { id: "logout", label: "Logout", destructive: true, onSelect: () => router.push("/logout") },
                ]}
              />
            ) : (
              <Link
                href="/login"
                className="rounded-[var(--radius-sm)] bg-[var(--accent)] px-3 py-2 font-medium text-[var(--accent-fg)]"
              >
                Sign in
              </Link>
            )}
          </nav>
        </div>
      </header>
      {menuOpen ? (
        <div
          id={menuId}
          role="dialog"
          aria-modal="true"
          aria-label="Navigation"
          className="border-b border-[var(--border)] bg-[var(--surface)] px-4 py-3 md:hidden"
        >
          <nav aria-label="Mobile research navigation" className="flex flex-col gap-2">
            <Link
              href="/dashboard"
              onClick={() => setMenuOpen(false)}
              className="rounded-[var(--radius-sm)] px-3 py-2 text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
            >
              Search
            </Link>
            {session ? (
              <Link
                href="/logout"
                onClick={() => setMenuOpen(false)}
                className="rounded-[var(--radius-sm)] px-3 py-2 text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
              >
                Sign out
              </Link>
            ) : (
              <Link
                href="/login"
                onClick={() => setMenuOpen(false)}
                className="rounded-[var(--radius-sm)] px-3 py-2 text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
              >
                Sign in
              </Link>
            )}
          </nav>
        </div>
      ) : null}
      <main
        id="main-content"
        className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 sm:py-10"
      >
        {children}
      </main>
      <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs text-[var(--muted)] sm:px-6">
        Research tools, not investment advice. Backend-authoritative analysis only.
      </footer>
    </div>
  );
}
