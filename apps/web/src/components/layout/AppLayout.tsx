"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { FeedbackProvider } from "@/components/beta/FeedbackContext";
import { BetaShellWidgets } from "@/components/beta/BetaShellWidgets";
import { WorkspaceLoading } from "@/components/loading/WorkspaceLoading";
import { useRouteTransitionTiming } from "@/hooks/usePerformanceTiming";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  isAuthPublicPath,
  loginRedirectUrl,
  requiresAuth,
} from "@/lib/auth/routeGuards";
import { ContentArea } from "./ContentArea";
import { Sidebar } from "./Sidebar";
import { StatusBar } from "./StatusBar";
import { Topbar } from "./Topbar";

const COLLAPSE_KEY = "dsp.sidebar.collapsed.v1";

export function AppLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { session, status } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useRouteTransitionTiming();

  useEffect(() => {
    const stored = window.localStorage.getItem(COLLAPSE_KEY);
    if (stored === "1") setCollapsed(true);
  }, []);

  useEffect(() => {
    if (status === "loading" || status === "refreshing") return;

    if (isAuthPublicPath(pathname)) {
      if (session && pathname === "/login") {
        router.replace("/dashboard");
      }
      return;
    }

    if (requiresAuth(pathname) && !session) {
      const target =
        status === "expired"
          ? `${loginRedirectUrl(pathname)}&expired=1`
          : loginRedirectUrl(pathname);
      router.replace(target);
    }
  }, [status, session, pathname, router]);

  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  function toggleCollapse() {
    setCollapsed((v) => {
      const next = !v;
      window.localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
      return next;
    });
  }

  if (status === "loading" || status === "refreshing") {
    return (
      <div className="grid min-h-screen place-items-center px-4">
        <WorkspaceLoading
          label={
            status === "refreshing" ? "Refreshing session…" : "Loading session…"
          }
        />
      </div>
    );
  }

  if (isAuthPublicPath(pathname)) {
    return <>{children}</>;
  }

  if (requiresAuth(pathname) && !session) {
    return (
      <div className="grid min-h-screen place-items-center px-4">
        <WorkspaceLoading label="Redirecting to sign in…" />
      </div>
    );
  }

  return (
    <FeedbackProvider>
      <div className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
        <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--glow)_0%,_transparent_55%)]" />
        <div className="flex min-h-screen">
          <Sidebar collapsed={collapsed} />
          <div className="flex min-w-0 flex-1 flex-col">
            <Topbar
              onMenuClick={() => setDrawerOpen(true)}
              onToggleCollapse={toggleCollapse}
              sidebarCollapsed={collapsed}
            />
            <main id="main-content" className="flex-1 overflow-y-auto">
              <ContentArea>{children}</ContentArea>
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
              role="dialog"
              aria-modal="true"
              aria-label="Navigation"
              className="absolute inset-y-0 left-0 border-r border-[var(--border)] bg-[var(--surface)] shadow-xl"
            >
              <Sidebar
                collapsed={false}
                mobile
                onNavigate={() => setDrawerOpen(false)}
              />
            </div>
          </div>
        ) : null}

        <BetaShellWidgets />
      </div>
    </FeedbackProvider>
  );
}
