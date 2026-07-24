"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { FeedbackProvider } from "@/components/beta/FeedbackContext";
import { BetaShellWidgets } from "@/components/beta/BetaShellWidgets";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ContentArea } from "./ContentArea";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

const COLLAPSE_KEY = "dsp.sidebar.collapsed.v1";

export function AppLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { session, ready } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem(COLLAPSE_KEY);
    if (stored === "1") setCollapsed(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    if (!session && pathname !== "/login") {
      router.replace("/login");
    }
    if (session && pathname === "/login") {
      router.replace("/dashboard");
    }
  }, [ready, session, pathname, router]);

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

  if (!ready) {
    return (
      <div className="grid min-h-screen place-items-center text-sm text-[var(--muted)]">
        Loading session…
      </div>
    );
  }

  if (pathname === "/login") {
    return <>{children}</>;
  }

  if (!session) {
    return (
      <div className="grid min-h-screen place-items-center text-sm text-[var(--muted)]">
        Redirecting to login…
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
            <main id="main-content" className="flex-1">
              <ContentArea>{children}</ContentArea>
            </main>
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
