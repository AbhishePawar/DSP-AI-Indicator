"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  Badge,
  Button,
  Input,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ds";
import { rbacAuthApi } from "@/lib/api/rbacAuth";
import { useAuth } from "@/lib/auth/AuthProvider";
import { tokenStatus } from "@/lib/auth/sessionStore";
import {
  DASHBOARD_WIDGETS,
  useDashboardPrefsStore,
} from "@/lib/dashboard";
import { env } from "@/lib/env";
import {
  FRONTEND_FOUNDATION_EPIC,
  FRONTEND_FOUNDATION_STATUS,
  FRONTEND_FOUNDATION_VERSION,
  BACKEND_PLATFORM_TARGET,
  API_CONTRACT_TARGET,
} from "@/foundation";
import {
  LANDING_PAGE_OPTIONS,
  useSettingsPrefsStore,
  type ContrastPreference,
  type DensityPreference,
  type FontSizePreference,
  type MotionPreference,
} from "@/lib/settings";
import { useUiStore } from "@/lib/shell/uiStore";
import { usePersistence } from "@/providers/PersistenceProvider";
import { useTheme, type ThemeMode } from "@/providers/ThemeProvider";
import { useNotifications } from "@/providers/NotificationProvider";
import {
  ChoiceGroup,
  FieldRow,
  SectionCard,
  WorkspaceEmpty,
  WorkspaceSkeleton,
} from "./Primitives";

export function ProfileSection() {
  const { user, session, status, loadProfile } = useAuth();

  useEffect(() => {
    if (status === "authenticated") void loadProfile();
  }, [status, loadProfile]);

  if (status === "loading") return <WorkspaceSkeleton />;
  if (!user || !session) {
    return (
      <WorkspaceEmpty
        title="Account unavailable."
        description="Sign in to view profile information from existing auth APIs."
        action={
          <Link href="/login">
            <Button size="sm">Sign in</Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      <SectionCard
        title="Account Summary"
        description="Display-only identity from the active session /auth/rbac/me."
      >
        <dl>
          <FieldRow label="Display name" value={user.displayName} />
          <FieldRow label="Username" value={user.username} />
          <FieldRow label="Email" value={user.email} />
          <FieldRow label="Subject" value={user.subject} />
          <FieldRow label="Primary role" value={user.role} />
        </dl>
      </SectionCard>
      <SectionCard title="Roles">
        {(user.roles || []).length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <div className="flex flex-wrap gap-1">
            {user.roles.map((r) => (
              <Badge key={r} variant="outline">
                {r}
              </Badge>
            ))}
          </div>
        )}
      </SectionCard>
      <SectionCard title="Permissions">
        {(user.permissions || []).length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <div className="flex flex-wrap gap-1" aria-label="User permissions">
            {user.permissions.map((p) => (
              <Badge key={p} variant="outline">
                {p}
              </Badge>
            ))}
          </div>
        )}
      </SectionCard>
      <SectionCard title="Session Information">
        <dl>
          <FieldRow label="Session ID" value={session.sessionId} />
          <FieldRow label="Auth method" value={session.authMethod} />
          <FieldRow label="Issued at" value={session.issuedAt} />
          <FieldRow label="Expires at" value={session.expiresAt} />
          <FieldRow label="Last login" value={session.issuedAt} />
        </dl>
      </SectionCard>
      <div>
        <Link href="/profile" className="text-sm text-[var(--accent)] hover:underline">
          Open full profile page
        </Link>
      </div>
    </div>
  );
}

export function AppearanceSection() {
  const { mode, resolved, setMode } = useTheme();
  const { status } = useAuth();
  const { updatePreferences } = usePersistence();
  const { success } = useNotifications();
  const density = useSettingsPrefsStore((s) => s.density);
  const fontSize = useSettingsPrefsStore((s) => s.fontSize);
  const motionPreference = useSettingsPrefsStore((s) => s.motionPreference);
  const contrastPreference = useSettingsPrefsStore((s) => s.contrastPreference);
  const setDensity = useSettingsPrefsStore((s) => s.setDensity);
  const setFontSize = useSettingsPrefsStore((s) => s.setFontSize);
  const setMotionPreference = useSettingsPrefsStore((s) => s.setMotionPreference);
  const setContrastPreference = useSettingsPrefsStore(
    (s) => s.setContrastPreference,
  );
  const resetAppearance = useSettingsPrefsStore((s) => s.resetAppearance);

  const setTheme = (next: ThemeMode) => {
    setMode(next);
    if (status === "authenticated") {
      updatePreferences({ theme: next });
    }
    success("Theme updated", `Theme set to ${next}.`);
  };

  return (
    <div className="space-y-4">
      <SectionCard
        title="Theme"
        description={`Resolved: ${resolved}. Persists via ThemeProvider (dsp.theme.v2).`}
      >
        <ChoiceGroup legend="Theme mode">
          {(["light", "dark", "system"] as ThemeMode[]).map((value) => (
            <Button
              key={value}
              size="sm"
              variant={mode === value ? "primary" : "secondary"}
              aria-pressed={mode === value}
              onClick={() => setTheme(value)}
            >
              {value.charAt(0).toUpperCase() + value.slice(1)}
            </Button>
          ))}
        </ChoiceGroup>
      </SectionCard>

      <SectionCard title="Density" description="Local UI density preference.">
        <ChoiceGroup legend="Density">
          {(["comfortable", "compact"] as DensityPreference[]).map((value) => (
            <Button
              key={value}
              size="sm"
              variant={density === value ? "primary" : "secondary"}
              aria-pressed={density === value}
              onClick={() => setDensity(value)}
            >
              {value.charAt(0).toUpperCase() + value.slice(1)}
            </Button>
          ))}
        </ChoiceGroup>
      </SectionCard>

      <SectionCard title="Font Size">
        <ChoiceGroup legend="Font size">
          {(["sm", "md", "lg"] as FontSizePreference[]).map((value) => (
            <Button
              key={value}
              size="sm"
              variant={fontSize === value ? "primary" : "secondary"}
              aria-pressed={fontSize === value}
              onClick={() => setFontSize(value)}
            >
              {value.toUpperCase()}
            </Button>
          ))}
        </ChoiceGroup>
      </SectionCard>

      <SectionCard title="Motion Preference">
        <ChoiceGroup legend="Motion">
          {(["system", "full", "reduce"] as MotionPreference[]).map((value) => (
            <Button
              key={value}
              size="sm"
              variant={motionPreference === value ? "primary" : "secondary"}
              aria-pressed={motionPreference === value}
              onClick={() => setMotionPreference(value)}
            >
              {value.charAt(0).toUpperCase() + value.slice(1)}
            </Button>
          ))}
        </ChoiceGroup>
      </SectionCard>

      <SectionCard title="High Contrast">
        <ChoiceGroup legend="Contrast">
          {(["system", "more"] as ContrastPreference[]).map((value) => (
            <Button
              key={value}
              size="sm"
              variant={contrastPreference === value ? "primary" : "secondary"}
              aria-pressed={contrastPreference === value}
              onClick={() => setContrastPreference(value)}
            >
              {value === "more" ? "High contrast" : "System"}
            </Button>
          ))}
        </ChoiceGroup>
      </SectionCard>

      <Button
        size="sm"
        variant="outline"
        onClick={() => {
          resetAppearance();
          success("Appearance reset", "Local appearance defaults restored.");
        }}
      >
        Reset appearance defaults
      </Button>
    </div>
  );
}

export function DashboardSection() {
  const widgetOrder = useDashboardPrefsStore((s) => s.widgetOrder);
  const hiddenWidgets = useDashboardPrefsStore((s) => s.hiddenWidgets);
  const toggleWidgetVisible = useDashboardPrefsStore(
    (s) => s.toggleWidgetVisible,
  );
  const moveWidget = useDashboardPrefsStore((s) => s.moveWidget);
  const resetLayout = useDashboardPrefsStore((s) => s.resetLayout);
  const isWidgetVisible = useDashboardPrefsStore((s) => s.isWidgetVisible);
  const { preferences, updatePreferences } = usePersistence();
  const { status } = useAuth();
  const { success } = useNotifications();

  const metaById = Object.fromEntries(
    DASHBOARD_WIDGETS.map((w) => [w.id, w]),
  );

  return (
    <div className="space-y-4">
      <SectionCard
        title="Default Landing Page"
        description="Persisted with browser-scoped user preferences when signed in."
      >
        <label className="block text-sm text-[var(--muted)]" htmlFor="landing">
          Landing page
        </label>
        <select
          id="landing"
          className="mt-1 w-full rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm"
          value={preferences.defaultLandingPage}
          disabled={status !== "authenticated"}
          onChange={(e) => {
            updatePreferences({ defaultLandingPage: e.target.value });
            success("Landing page saved", e.target.value);
          }}
          aria-label="Default landing page"
        >
          {LANDING_PAGE_OPTIONS.map((page) => (
            <option key={page.href} value={page.href}>
              {page.label}
            </option>
          ))}
        </select>
        {status !== "authenticated" ? (
          <p className="mt-2 text-xs text-[var(--muted)]">
            Sign in to persist landing page preference.
          </p>
        ) : null}
      </SectionCard>

      <SectionCard
        title="Widget Preferences"
        description="Visibility and order from the F004 dashboard prefs store. No scores."
        action={
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              resetLayout();
              success("Dashboard layout reset", "Default widget order restored.");
            }}
          >
            Reset layout
          </Button>
        }
      >
        <Table aria-label="Dashboard widget preferences">
          <TableHeader>
            <TableRow>
              <TableHead>Widget</TableHead>
              <TableHead>Visible</TableHead>
              <TableHead>Order</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {widgetOrder.map((id) => (
              <TableRow key={id}>
                <TableCell>
                  {metaById[id]?.title || id}
                  <p className="text-xs text-[var(--muted)]">
                    {metaById[id]?.description || "Data unavailable."}
                  </p>
                </TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant={isWidgetVisible(id) ? "primary" : "secondary"}
                    aria-pressed={isWidgetVisible(id)}
                    onClick={() => toggleWidgetVisible(id)}
                  >
                    {isWidgetVisible(id) ? "Shown" : "Hidden"}
                  </Button>
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      aria-label={`Move ${id} up`}
                      onClick={() => moveWidget(id, "up")}
                    >
                      ↑
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      aria-label={`Move ${id} down`}
                      onClick={() => moveWidget(id, "down")}
                    >
                      ↓
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <p className="mt-2 text-xs text-[var(--muted)]">
          Hidden widgets: {hiddenWidgets.length || "none"}
        </p>
      </SectionCard>
    </div>
  );
}

export function WorkspaceSection() {
  const sidebarCollapsed = useUiStore((s) => s.sidebarCollapsed);
  const setSidebarCollapsed = useUiStore((s) => s.setSidebarCollapsed);
  const recentPages = useUiStore((s) => s.recentPages);
  const favouritePages = useUiStore((s) => s.favouritePages);
  const recentSearches = useDashboardPrefsStore((s) => s.recentSearches);
  const pinnedCompanies = useDashboardPrefsStore((s) => s.pinnedCompanies);
  const defaultWorkspace = useSettingsPrefsStore((s) => s.defaultWorkspace);
  const setDefaultWorkspace = useSettingsPrefsStore(
    (s) => s.setDefaultWorkspace,
  );
  const recentItemsLimit = useSettingsPrefsStore((s) => s.recentItemsLimit);
  const setRecentItemsLimit = useSettingsPrefsStore(
    (s) => s.setRecentItemsLimit,
  );
  const searchHistoryEnabled = useSettingsPrefsStore(
    (s) => s.searchHistoryEnabled,
  );
  const setSearchHistoryEnabled = useSettingsPrefsStore(
    (s) => s.setSearchHistoryEnabled,
  );
  const { success } = useNotifications();

  const limitedRecent = recentPages.slice(0, recentItemsLimit);

  return (
    <div className="space-y-4">
      <SectionCard title="Sidebar State">
        <ChoiceGroup legend="Sidebar">
          <Button
            size="sm"
            variant={!sidebarCollapsed ? "primary" : "secondary"}
            aria-pressed={!sidebarCollapsed}
            onClick={() => setSidebarCollapsed(false)}
          >
            Expanded
          </Button>
          <Button
            size="sm"
            variant={sidebarCollapsed ? "primary" : "secondary"}
            aria-pressed={sidebarCollapsed}
            onClick={() => setSidebarCollapsed(true)}
          >
            Collapsed
          </Button>
        </ChoiceGroup>
      </SectionCard>

      <SectionCard title="Default Workspace">
        <label
          className="block text-sm text-[var(--muted)]"
          htmlFor="default-workspace"
        >
          Preferred workspace path (local)
        </label>
        <select
          id="default-workspace"
          className="mt-1 w-full rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm"
          value={defaultWorkspace}
          onChange={(e) => {
            setDefaultWorkspace(e.target.value);
            success("Default workspace saved", e.target.value);
          }}
          aria-label="Default workspace"
        >
          {LANDING_PAGE_OPTIONS.map((page) => (
            <option key={page.href} value={page.href}>
              {page.label}
            </option>
          ))}
        </select>
      </SectionCard>

      <SectionCard title="Recent Items Limit">
        <label
          className="block text-sm text-[var(--muted)]"
          htmlFor="recent-limit"
        >
          Display limit for recent pages in Settings
        </label>
        <Input
          id="recent-limit"
          type="number"
          min={3}
          max={24}
          value={recentItemsLimit}
          onChange={(e) => setRecentItemsLimit(Number(e.target.value) || 8)}
          aria-label="Recent items limit"
          className="mt-1 max-w-[8rem]"
        />
      </SectionCard>

      <SectionCard title="Search History">
        <ChoiceGroup legend="Search history">
          <Button
            size="sm"
            variant={searchHistoryEnabled ? "primary" : "secondary"}
            aria-pressed={searchHistoryEnabled}
            onClick={() => setSearchHistoryEnabled(true)}
          >
            Enabled
          </Button>
          <Button
            size="sm"
            variant={!searchHistoryEnabled ? "primary" : "secondary"}
            aria-pressed={!searchHistoryEnabled}
            onClick={() => setSearchHistoryEnabled(false)}
          >
            Disabled
          </Button>
        </ChoiceGroup>
        {!searchHistoryEnabled || recentSearches.length === 0 ? (
          <p className="mt-2 text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="mt-2 space-y-1 text-sm">
            {recentSearches.slice(0, recentItemsLimit).map((s) => (
              <li key={`${s.query}-${s.at}`}>{s.query}</li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Pinned Items">
        {pinnedCompanies.length === 0 && favouritePages.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. Pin companies on the dashboard or favourite pages in the shell." />
        ) : (
          <div className="space-y-2 text-sm">
            {pinnedCompanies.map((p) => (
              <p key={p.symbol}>
                Company · {p.symbol}
                {p.label ? ` (${p.label})` : ""}
              </p>
            ))}
            {favouritePages.map((p) => (
              <p key={p.path}>
                Page · {p.title} ({p.path})
              </p>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard title="Recent Pages">
        {limitedRecent.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <ul className="space-y-1 text-sm">
            {limitedRecent.map((p) => (
              <li key={p.path}>
                <Link
                  href={p.path}
                  className="text-[var(--accent)] hover:underline"
                >
                  {p.title}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}

export function NotificationsSection() {
  const toastEnabled = useSettingsPrefsStore((s) => s.toastEnabled);
  const toastDurationMs = useSettingsPrefsStore((s) => s.toastDurationMs);
  const soundEnabled = useSettingsPrefsStore((s) => s.soundEnabled);
  const setToastEnabled = useSettingsPrefsStore((s) => s.setToastEnabled);
  const setToastDurationMs = useSettingsPrefsStore((s) => s.setToastDurationMs);
  const setSoundEnabled = useSettingsPrefsStore((s) => s.setSoundEnabled);
  const { success } = useNotifications();

  return (
    <div className="space-y-4">
      <SectionCard
        title="Notification Preferences (UI)"
        description="Local toast preferences only. No notification delivery API."
      >
        <ChoiceGroup legend="Toasts">
          <Button
            size="sm"
            variant={toastEnabled ? "primary" : "secondary"}
            aria-pressed={toastEnabled}
            onClick={() => {
              setToastEnabled(true);
              success("Toasts enabled", "UI toast notifications are on.");
            }}
          >
            Enabled
          </Button>
          <Button
            size="sm"
            variant={!toastEnabled ? "primary" : "secondary"}
            aria-pressed={!toastEnabled}
            onClick={() => setToastEnabled(false)}
          >
            Disabled
          </Button>
        </ChoiceGroup>
        <label
          className="mt-3 block text-sm text-[var(--muted)]"
          htmlFor="toast-duration"
        >
          Toast duration (ms)
        </label>
        <Input
          id="toast-duration"
          type="number"
          min={1500}
          max={15000}
          step={500}
          value={toastDurationMs}
          onChange={(e) => setToastDurationMs(Number(e.target.value) || 4000)}
          className="mt-1 max-w-[10rem]"
          aria-label="Toast duration in milliseconds"
        />
      </SectionCard>

      <SectionCard title="Sound Toggle">
        <ChoiceGroup legend="Sound">
          <Button
            size="sm"
            variant={soundEnabled ? "primary" : "secondary"}
            aria-pressed={soundEnabled}
            onClick={() => setSoundEnabled(true)}
          >
            On
          </Button>
          <Button
            size="sm"
            variant={!soundEnabled ? "primary" : "secondary"}
            aria-pressed={!soundEnabled}
            onClick={() => setSoundEnabled(false)}
          >
            Off
          </Button>
        </ChoiceGroup>
        <p className="mt-2 text-xs text-[var(--muted)]">
          Preference stored locally. No notification sound engine is wired in
          the thin client.
        </p>
      </SectionCard>

      <SectionCard title="Email Preferences">
        <WorkspaceEmpty description="Data unavailable. No email preference endpoint in frozen /api/v1." />
      </SectionCard>
    </div>
  );
}

export function SecuritySection() {
  const { session, user, logout } = useAuth();
  const token = tokenStatus(session);
  const sessionsQuery = useQuery({
    queryKey: ["settings", "sessions", session?.accessToken, session?.subject],
    queryFn: async () => {
      const envelope = await rbacAuthApi.listSessions(
        session!.accessToken,
        session!.subject,
      );
      if (envelope.ok && Array.isArray(envelope.result)) {
        return envelope.result;
      }
      throw new Error(
        envelope.message || "Data unavailable. Session list not available.",
      );
    },
    enabled: Boolean(session?.accessToken && session?.subject),
    retry: false,
  });

  if (!session) {
    return (
      <WorkspaceEmpty
        description="Sign in to view session and token information."
        action={
          <Link href="/login">
            <Button size="sm">Sign in</Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      <SectionCard title="Token Information">
        <dl>
          <FieldRow label="Token status" value={token.label} />
          <FieldRow label="Token valid" value={String(token.valid)} />
          <FieldRow label="Has refresh" value={String(token.hasRefresh)} />
          <FieldRow label="Token type" value={session.tokenType} />
          <FieldRow label="Remember me" value={String(session.rememberMe)} />
          <FieldRow label="Subject" value={session.subject} />
          <FieldRow
            label="Access token"
            value={session.accessToken ? "Present (hidden)" : undefined}
          />
        </dl>
      </SectionCard>

      <SectionCard
        title="Active Sessions"
        description="GET /admin/sessions scoped to current subject when permitted."
      >
        {sessionsQuery.isLoading ? (
          <WorkspaceSkeleton />
        ) : sessionsQuery.isError ? (
          <WorkspaceEmpty
            description={
              sessionsQuery.error instanceof Error
                ? sessionsQuery.error.message
                : "Data unavailable."
            }
          />
        ) : (sessionsQuery.data || []).length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. No sessions returned." />
        ) : (
          <Table aria-label="Active sessions">
            <TableHeader>
              <TableRow>
                <TableHead>Session</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead>Revoked</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sessionsQuery.data!.map((s) => (
                <TableRow key={s.session_id}>
                  <TableCell className="font-mono text-xs">
                    {s.session_id}
                  </TableCell>
                  <TableCell>{s.created_at || "Data unavailable."}</TableCell>
                  <TableCell>{s.expires_at || "Data unavailable."}</TableCell>
                  <TableCell>
                    {s.revoked === undefined
                      ? "Data unavailable."
                      : String(s.revoked)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>

      <SectionCard title="Password Management">
        <Link href="/forgot-password">
          <Button size="sm" variant="secondary">
            Password reset link
          </Button>
        </Link>
        <p className="mt-2 text-xs text-[var(--muted)]">
          Uses the existing auth screen. No in-app password change API.
        </p>
      </SectionCard>

      <SectionCard title="Logout Other Sessions">
        <Button size="sm" variant="outline" disabled title="Data unavailable.">
          Logout other sessions
        </Button>
        <p className="mt-2 text-xs text-[var(--muted)]">
          Data unavailable. No logout-other-sessions endpoint in frozen APIs.
        </p>
        <div className="mt-3">
          <Button size="sm" variant="danger" asChild>
            <Link href="/logout">
              Sign out this session
              {user?.username ? ` (${user.username})` : ""}
            </Link>
          </Button>
        </div>
      </SectionCard>
    </div>
  );
}

export function AccessibilitySection() {
  const motionPreference = useSettingsPrefsStore((s) => s.motionPreference);
  const contrastPreference = useSettingsPrefsStore((s) => s.contrastPreference);
  const focusVisible = useSettingsPrefsStore((s) => s.focusVisible);
  const setMotionPreference = useSettingsPrefsStore((s) => s.setMotionPreference);
  const setContrastPreference = useSettingsPrefsStore(
    (s) => s.setContrastPreference,
  );
  const setFocusVisible = useSettingsPrefsStore((s) => s.setFocusVisible);

  return (
    <div className="space-y-4">
      <SectionCard
        title="Keyboard Shortcuts"
        description="Available in the Settings workspace toolbar."
      >
        <ul className="space-y-1 text-sm">
          <li>1–8 — Jump to settings section</li>
          <li>[ / ] — Toggle left / right panels</li>
          <li>Ctrl/⌘ + K — Command palette (shell)</li>
        </ul>
      </SectionCard>

      <SectionCard title="Reduced Motion">
        <ChoiceGroup legend="Motion preference">
          {(["system", "full", "reduce"] as MotionPreference[]).map((value) => (
            <Button
              key={value}
              size="sm"
              variant={motionPreference === value ? "primary" : "secondary"}
              aria-pressed={motionPreference === value}
              onClick={() => setMotionPreference(value)}
            >
              {value.charAt(0).toUpperCase() + value.slice(1)}
            </Button>
          ))}
        </ChoiceGroup>
      </SectionCard>

      <SectionCard title="High Contrast">
        <ChoiceGroup legend="Contrast preference">
          {(["system", "more"] as ContrastPreference[]).map((value) => (
            <Button
              key={value}
              size="sm"
              variant={contrastPreference === value ? "primary" : "secondary"}
              aria-pressed={contrastPreference === value}
              onClick={() => setContrastPreference(value)}
            >
              {value === "more" ? "High contrast" : "System"}
            </Button>
          ))}
        </ChoiceGroup>
      </SectionCard>

      <SectionCard title="Focus Visibility">
        <ChoiceGroup legend="Focus rings">
          <Button
            size="sm"
            variant={focusVisible ? "primary" : "secondary"}
            aria-pressed={focusVisible}
            onClick={() => setFocusVisible(true)}
          >
            Enhanced
          </Button>
          <Button
            size="sm"
            variant={!focusVisible ? "primary" : "secondary"}
            aria-pressed={!focusVisible}
            onClick={() => setFocusVisible(false)}
          >
            Default
          </Button>
        </ChoiceGroup>
        <p className="mt-2 text-xs text-[var(--muted)]">
          Enhanced mode strengthens `:focus-visible` outlines via document
          dataset.
        </p>
      </SectionCard>
    </div>
  );
}

export function AboutSection() {
  return (
    <div className="space-y-4">
      <SectionCard title="Version Information">
        <dl>
          <FieldRow label="Platform / app channel" value={env.frontendVersion} />
          <FieldRow
            label="Frontend foundation"
            value={FRONTEND_FOUNDATION_VERSION}
          />
          <FieldRow label="Foundation epic" value={FRONTEND_FOUNDATION_EPIC} />
          <FieldRow
            label="Foundation status"
            value={FRONTEND_FOUNDATION_STATUS}
          />
          <FieldRow label="Backend target" value={BACKEND_PLATFORM_TARGET} />
          <FieldRow label="API contract" value={API_CONTRACT_TARGET} />
          <FieldRow label="Environment" value={env.environment} />
          <FieldRow label="API base URL" value={env.apiBaseUrl} />
        </dl>
      </SectionCard>

      <SectionCard title="Build Information">
        <dl>
          <FieldRow label="App name" value={env.appName} />
          <FieldRow label="Tagline" value={env.tagline} />
          <FieldRow
            label="Thin client"
            value="Presentation only — no browser engines"
          />
        </dl>
      </SectionCard>

      <SectionCard title="Documentation Links">
        <ul className="space-y-2 text-sm">
          <li>
            <Link href="/docs" className="text-[var(--accent)] hover:underline">
              Product documentation
            </Link>
          </li>
          <li>
            <Link
              href="/docs/administrator-guide"
              className="text-[var(--accent)] hover:underline"
            >
              Administrator guide
            </Link>
          </li>
          <li>
            <Link
              href="/diagnostics"
              className="text-[var(--accent)] hover:underline"
            >
              Diagnostics
            </Link>
          </li>
        </ul>
      </SectionCard>

      <SectionCard title="Licence Information">
        <WorkspaceEmpty description="Data unavailable. Licence text is not exposed by a frozen /api/v1 endpoint." />
      </SectionCard>
    </div>
  );
}
