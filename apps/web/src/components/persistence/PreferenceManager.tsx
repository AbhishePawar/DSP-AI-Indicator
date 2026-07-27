"use client";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { useAuth } from "@/lib/auth/AuthProvider";
import { usePersistence } from "@/providers/PersistenceProvider";
import { useTheme, type ThemeMode } from "@/providers/ThemeProvider";

const LANDING_PAGES = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/analysis", label: "Analysis" },
  { href: "/research", label: "Research" },
  { href: "/companies", label: "Companies" },
  { href: "/portfolio", label: "Portfolio" },
] as const;

const WATCHLIST_VIEWS = [
  { id: null, label: "Default (placeholder)" },
  { id: "compact", label: "Compact" },
  { id: "detailed", label: "Detailed" },
] as const;

export function PreferenceManager() {
  const { status } = useAuth();
  const { preferences, updatePreferences } = usePersistence();
  const { mode, setMode } = useTheme();

  function handleTheme(next: ThemeMode) {
    setMode(next);
    if (status === "authenticated") {
      updatePreferences({ theme: next });
    }
  }

  return (
    <Card>
      <CardHeader
        title="User Preferences"
        description={
          status === "authenticated"
            ? "Synced to your account in this browser"
            : "Sign in to persist preferences"
        }
      />
      <CardBody className="space-y-4">
        <div>
          <p className="mb-2 text-sm text-[var(--muted)]">Theme</p>
          <div className="flex flex-wrap gap-2">
            {(["light", "dark", "system"] as ThemeMode[]).map((value) => (
              <Button
                key={value}
                size="sm"
                variant={mode === value ? "primary" : "secondary"}
                onClick={() => handleTheme(value)}
                aria-pressed={mode === value}
              >
                {value.charAt(0).toUpperCase() + value.slice(1)}
              </Button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm text-[var(--muted)]" htmlFor="landing-page">
            Default landing page
          </label>
          <select
            id="landing-page"
            className="mt-1 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm"
            value={preferences.defaultLandingPage}
            disabled={status !== "authenticated"}
            onChange={(event) =>
              updatePreferences({ defaultLandingPage: event.target.value })
            }
          >
            {LANDING_PAGES.map((page) => (
              <option key={page.href} value={page.href}>
                {page.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            className="block text-sm text-[var(--muted)]"
            htmlFor="watchlist-view"
          >
            Preferred watchlist view (placeholder)
          </label>
          <select
            id="watchlist-view"
            className="mt-1 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm"
            value={preferences.preferredWatchlistView ?? ""}
            disabled={status !== "authenticated"}
            onChange={(event) =>
              updatePreferences({
                preferredWatchlistView: event.target.value || null,
              })
            }
          >
            {WATCHLIST_VIEWS.map((view) => (
              <option key={String(view.id)} value={view.id ?? ""}>
                {view.label}
              </option>
            ))}
          </select>
        </div>
      </CardBody>
    </Card>
  );
}
