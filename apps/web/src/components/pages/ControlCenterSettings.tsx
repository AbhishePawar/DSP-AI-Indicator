"use client";

/**
 * Figma `ControlCenter.tsx` — user settings: Account card · Notifications ·
 * Research Preferences · Interface · Danger Zone.
 *
 * Data: account from the authenticated session; toggles via
 * `GET/PUT /api/v1/workspace/preferences`; "Clear Research History" via
 * `DELETE /api/v1/workspace/research/saved`; "Delete Account" via
 * `DELETE /auth/me`. No plan tier is displayed unless the server provides it.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Switch } from "@/components/ds";
import { FigmaPage } from "@/components/pages/PagePrimitives";
import { api } from "@/lib/api/client";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import type { PreferenceKey, PreferencesResponse } from "@/lib/api/workspaceTypes";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useTheme } from "@/providers/ThemeProvider";

const QUERY_KEY = ["workspace", "preferences"] as const;
const CARD = "rounded-xl border border-[var(--border)] bg-[var(--card)]";
const BTN =
  "min-h-9 rounded-lg border px-4 text-[13px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50";
const RISK_BORDER = "border-[color-mix(in_srgb,var(--c-risk)_30%,transparent)]";

type SettingItem = { key: PreferenceKey; label: string; desc: string };

export const SETTING_SECTIONS: ReadonlyArray<{ title: string; items: SettingItem[] }> = [
  {
    title: "Notifications",
    items: [
      { key: "notifications", label: "Push Notifications", desc: "Browser notifications for DSP signal changes" },
      { key: "dsp_alerts", label: "DSP Rating Alerts", desc: "Notify when a watchlist company rating changes" },
      { key: "email_digest", label: "Weekly Email Digest", desc: "Summary of top DSP signals every Monday" },
    ],
  },
  {
    title: "Research Preferences",
    items: [
      { key: "peer_comparisons", label: "Auto-show Peer Comparison", desc: "Automatically surface peer data in research responses" },
      { key: "auto_research", label: "Auto-research on Search", desc: "Start research immediately when you select a company" },
    ],
  },
  {
    title: "Interface",
    items: [
      { key: "dark_mode", label: "Dark Mode", desc: "Use dark color scheme across all pages" },
      { key: "compact_view", label: "Compact View", desc: "Reduce spacing in tables and lists" },
      { key: "beta_features", label: "Beta Features", desc: "Enable experimental features (may be unstable)" },
    ],
  },
];

function initialOf(name: string | null | undefined, email: string | null | undefined): string {
  const source = (name || email || "").trim();
  return source ? source[0]!.toUpperCase() : "U";
}

export function ControlCenterSettings() {
  const router = useRouter();
  const { session, user, logout } = useAuth();
  const { setMode } = useTheme();
  const token = session?.accessToken;
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState<"clear" | "delete" | "logout" | null>(null);

  const prefsQuery = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => api.workspacePreferences({ token }),
    enabled: Boolean(token),
    retry: false,
    staleTime: 30_000,
  });

  const prefs = prefsQuery.data?.preferences;

  useEffect(() => {
    if (!prefs) return;
    setMode(prefs.dark_mode ? "dark" : "light");
    document.documentElement.dataset.density = prefs.compact_view ? "compact" : "comfortable";
  }, [prefs, setMode]);

  const saveMutation = useMutation({
    mutationFn: (patch: Partial<Record<PreferenceKey, boolean>>) =>
      api.workspacePreferencesSave(patch, { token }),
    onMutate: async (patch) => {
      await queryClient.cancelQueries({ queryKey: QUERY_KEY });
      const previous = queryClient.getQueryData<PreferencesResponse>(QUERY_KEY);
      if (previous) {
        queryClient.setQueryData<PreferencesResponse>(QUERY_KEY, {
          ...previous,
          preferences: { ...previous.preferences, ...patch },
        });
      }
      return { previous };
    },
    onError: (err, _patch, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(QUERY_KEY, ctx.previous);
      setNotice({ tone: "error", text: err instanceof Error ? err.message : "Unable to save." });
    },
    onSuccess: (next) => {
      queryClient.setQueryData(QUERY_KEY, next);
      setNotice(null);
    },
  });

  async function clearHistory() {
    if (!token) return;
    if (!window.confirm("Clear all saved research from your Research Hub? This cannot be undone.")) return;
    setBusy("clear");
    try {
      const res = await api.workspaceSavedResearchClear({ token });
      await queryClient.invalidateQueries({ queryKey: ["workspace", "saved-research"] });
      setNotice({
        tone: "ok",
        text: res.removed === 0 ? "No saved research to clear." : `Cleared ${res.removed} saved research item${res.removed === 1 ? "" : "s"}.`,
      });
    } catch (e) {
      setNotice({ tone: "error", text: e instanceof Error ? e.message : "Unable to clear research history." });
    } finally {
      setBusy(null);
    }
  }

  async function deleteAccount() {
    if (!token) return;
    if (!window.confirm("Disable your account and revoke all sessions? This cannot be undone from the UI.")) return;
    setBusy("delete");
    try {
      await enterpriseAuthApi.deleteAccount(token);
      await logout();
      router.push("/login");
    } catch (e) {
      setNotice({ tone: "error", text: e instanceof Error ? e.message : "Unable to delete account." });
      setBusy(null);
    }
  }

  async function signOut() {
    setBusy("logout");
    try {
      await logout();
      router.push("/login");
    } finally {
      setBusy(null);
    }
  }

  const accountLine = [user?.email, user?.role ? user.role.replace(/_/g, " ") : null]
    .filter(Boolean)
    .join(" · ");

  return (
    <FigmaPage title="Control Center" subtitle="System settings · Preferences" gap={24}>
      {/* Account */}
      <section className={`${CARD} flex flex-wrap items-center gap-4 px-6 py-5`} aria-label="Account">
        <div
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-lg font-semibold text-white"
          style={{ background: "linear-gradient(135deg, var(--c-dsp), var(--c-cashflow))" }}
          aria-hidden="true"
        >
          {initialOf(user?.displayName, user?.email)}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[15px] font-medium text-[var(--fg)]">
            {user?.displayName || "User Account"}
          </p>
          <p className="truncate font-[family-name:var(--font-mono)] text-xs text-[var(--muted)]">
            {accountLine || "Account details unavailable."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/profile/account"
            className={`${BTN} inline-flex items-center border-[var(--border)] bg-[var(--surface-2)] text-[var(--fg)] hover:bg-[var(--surface)]`}
          >
            Edit Profile
          </Link>
          <button
            type="button"
            onClick={signOut}
            disabled={busy !== null}
            className={`${BTN} ${RISK_BORDER} bg-transparent text-[var(--c-risk)] hover:bg-[color-mix(in_srgb,var(--c-risk)_8%,transparent)]`}
          >
            {busy === "logout" ? "Logging out…" : "Log out"}
          </button>
        </div>
      </section>

      {notice ? (
        <p
          role="status"
          className={`rounded-lg border px-4 py-2.5 text-[13px] ${
            notice.tone === "ok"
              ? "border-[color-mix(in_srgb,var(--c-profit)_30%,transparent)] text-[var(--c-profit)]"
              : "border-[var(--danger-border)] bg-[var(--danger-bg)] text-[var(--danger-fg)]"
          }`}
        >
          {notice.text}
        </p>
      ) : null}

      {/* Settings sections */}
      {prefsQuery.isError ? (
        <section className={`${CARD} px-6 py-5`} role="alert">
          <p className="text-sm font-medium text-[var(--fg)]">Preferences unavailable.</p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {prefsQuery.error instanceof Error ? prefsQuery.error.message : "The preferences service did not respond."}
          </p>
          <button
            type="button"
            onClick={() => prefsQuery.refetch()}
            className={`${BTN} mt-3 border-[var(--border)] text-[var(--fg)]`}
          >
            Retry
          </button>
        </section>
      ) : (
        SETTING_SECTIONS.map((section) => (
          <section key={section.title} className={`${CARD} overflow-hidden`} aria-labelledby={`settings-${section.title}`}>
            <header className="border-b border-[var(--border)] px-5 py-3.5">
              <h2 id={`settings-${section.title}`} className="text-[13px] font-medium text-[var(--fg)]">
                {section.title}
              </h2>
            </header>
            <ul>
              {section.items.map((item, i) => {
                const id = `pref-${item.key}`;
                const checked = prefs ? prefs[item.key] : false;
                return (
                  <li
                    key={item.key}
                    className={`flex items-center justify-between gap-4 px-5 py-4 ${
                      i < section.items.length - 1 ? "border-b border-[var(--border)]" : ""
                    }`}
                  >
                    <div>
                      <label htmlFor={id} className="block text-[13px] text-[var(--fg)]">
                        {item.label}
                      </label>
                      <p id={`${id}-desc`} className="mt-0.5 text-xs text-[var(--muted)]">
                        {item.desc}
                      </p>
                    </div>
                    <Switch
                      id={id}
                      checked={checked}
                      disabled={!prefs || saveMutation.isPending}
                      onCheckedChange={(value) => saveMutation.mutate({ [item.key]: value })}
                      aria-describedby={`${id}-desc`}
                    />
                  </li>
                );
              })}
            </ul>
          </section>
        ))
      )}
      {prefsQuery.isPending && token ? (
        <p className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)]" role="status">
          Loading preferences…
        </p>
      ) : null}

      {/* Danger zone */}
      <section
        className={`rounded-xl border bg-[var(--card)] px-6 py-5 ${RISK_BORDER}`}
        aria-labelledby="danger-zone"
      >
        <h2 id="danger-zone" className="mb-3 text-[13px] font-medium text-[var(--c-risk)]">
          Danger Zone
        </h2>
        <div className="flex flex-wrap gap-2.5">
          <button
            type="button"
            onClick={clearHistory}
            disabled={!token || busy !== null}
            className={`${BTN} ${RISK_BORDER} bg-[color-mix(in_srgb,var(--c-risk)_8%,transparent)] text-[var(--c-risk)]`}
          >
            {busy === "clear" ? "Clearing…" : "Clear Research History"}
          </button>
          <button
            type="button"
            onClick={deleteAccount}
            disabled={!token || busy !== null}
            className={`${BTN} ${RISK_BORDER} bg-transparent text-[var(--c-risk)]`}
          >
            {busy === "delete" ? "Deleting…" : "Delete Account"}
          </button>
        </div>
      </section>
    </FigmaPage>
  );
}
