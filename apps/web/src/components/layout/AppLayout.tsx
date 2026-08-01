"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { FeedbackProvider } from "@/components/beta/FeedbackContext";
import { BetaShellWidgets } from "@/components/beta/BetaShellWidgets";
import { ClosedBetaGate } from "@/components/beta/ClosedBetaGate";
import { LoadingLayout } from "@/components/layout/ContentArea";
import { useRouteTransitionTiming } from "@/hooks/usePerformanceTiming";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  isAuthPublicPath,
  isMarketingPath,
  loginRedirectUrl,
  requiresAuth,
} from "@/lib/auth/routeGuards";
import { useUiStore } from "@/lib/shell";
import { ContentArea } from "./ContentArea";
import { ShellCommandPalette } from "./ShellCommandPalette";
import { Sidebar } from "./Sidebar";
import { StatusBar } from "./StatusBar";
import { Topbar } from "./Topbar";

function focusableSelector() {
  return [
    "a[href]",
    "button:not([disabled])",
    "textarea:not([disabled])",
    "input:not([disabled])",
    "select:not([disabled])",
    "[tabindex]:not([tabindex='-1'])",
  ].join(",");
}

export function AppLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { session, status } = useAuth();

  const sidebarCollapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggleSidebarCollapsed = useUiStore((s) => s.toggleSidebarCollapsed);
  const drawerOpen = useUiStore((s) => s.mobileDrawerOpen);
  const setDrawerOpen = useUiStore((s) => s.setMobileDrawerOpen);
  const drawerRef = useRef<HTMLDivElement | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useRouteTransitionTiming();

  useEffect(() => {
    if (status === "loading" || status === "refreshing") return;

    if (isAuthPublicPath(pathname)) {
      if (session && pathname === "/login") {
        router.replace("/dashboard");
      }
      return;
    }

    if (requiresAuth(pathname) && !session) {
      router.replace(loginRedirectUrl(pathname, status === "expired"));
    }
  }, [status, session, pathname, router]);

  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname, setDrawerOpen]);

  useEffect(() => {
    if (!drawerOpen) return;

    previousFocusRef.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;

    const dialog = drawerRef.current;
    const nodes = dialog
      ? Array.from(dialog.querySelectorAll<HTMLElement>(focusableSelector()))
      : [];
    nodes[0]?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setDrawerOpen(false);
        return;
      }
      if (event.key !== "Tab" || nodes.length === 0) return;
      const first = nodes[0]!;
      const last = nodes[nodes.length - 1]!;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      previousFocusRef.current?.focus?.();
    };
  }, [drawerOpen, setDrawerOpen]);

  if (status === "loading" || status === "refreshing") {
    return (
      <div className="grid min-h-screen place-items-center bg-[var(--bg)]">
        <LoadingLayout
          label={
            status === "refreshing" ? "Refreshing session…" : "Loading session…"
          }
        />
      </div>
    );
  }

  if (isMarketingPath(pathname) || isAuthPublicPath(pathname)) {
    return (
      <main
        id="main-content"
        tabIndex={-1}
        className="min-h-screen bg-[var(--bg)] text-[var(--fg)]"
      >
        {children}
      </main>
    );
  }

  if (requiresAuth(pathname) && !session) {
    return (
      <div className="grid min-h-screen place-items-center bg-[var(--bg)]">
        <LoadingLayout label="Redirecting to sign in…" />
      </div>
    );
  }

  return (
    <FeedbackProvider>
      <div className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
        <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--glow)_0%,_transparent_55%)]" />
        <div className="flex min-h-screen">
          <Sidebar collapsed={sidebarCollapsed} />
          <div className="flex min-w-0 flex-1 flex-col">
            <Topbar
              onMenuClick={() => setDrawerOpen(true)}
              onToggleCollapse={toggleSidebarCollapsed}
              sidebarCollapsed={sidebarCollapsed}
            />
            <main
              id="main-content"
              className="flex-1 overflow-auto scroll-smooth motion-reduce:scroll-auto"
              tabIndex={-1}
            >
              <ContentArea>
                <ClosedBetaGate>{children}</ClosedBetaGate>
              </ContentArea>
            </main>
            <StatusBar />
          </div>
        </div>

        {drawerOpen ? (
          <div className="fixed inset-0 z-50 md:hidden" role="presentation">
            <button
              type="button"
              className="absolute inset-0 bg-black/40"
              aria-label="Close navigation menu"
              onClick={() => setDrawerOpen(false)}
            />
            <div
              ref={drawerRef}
              role="dialog"
              aria-modal="true"
              aria-label="Navigation"
              className="absolute inset-y-0 left-0 max-w-[min(100vw,20rem)] overflow-y-auto border-r border-[var(--border)] bg-[var(--surface)] shadow-xl"
            >
              <Sidebar
                collapsed={false}
                mobile
                onNavigate={() => setDrawerOpen(false)}
              />
            </div>
          </div>
        ) : null}

        <ShellCommandPalette />
        <BetaShellWidgets />
      </div>
    </FeedbackProvider>
  );
}
