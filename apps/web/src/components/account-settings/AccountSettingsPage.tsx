"use client";

import { useState, useEffect, useCallback } from "react";
import {
  User,
  Bell,
  Mail,
  Webhook,
  Save,
  Loader2,
  CheckCircle,
  AlertCircle,
  ChevronDown,
} from "lucide-react";
import {
  getAccountSettings,
  upsertAccountSettings,
  getProfileData,
  updateDisplayName,
  type AccountSettings,
  type ProfileData,
} from "@/lib/account-settings/accountSettingsService";
import { PageHeader } from "@/components/layout/PageHeader";
import { trackAccountSettingsSaved } from "@/lib/analytics/events";

const DIGEST_OPTIONS: { value: AccountSettings["emailDigestFrequency"]; label: string; description: string }[] = [
  { value: "realtime", label: "Real-time", description: "Immediate email on each event" },
  { value: "daily", label: "Daily digest", description: "One summary email per day" },
  { value: "weekly", label: "Weekly digest", description: "One summary email per week" },
  { value: "never", label: "Never", description: "No email digests" },
];

const TIMEZONES = [
  "UTC", "America/New_York", "America/Chicago", "America/Denver",
  "America/Los_Angeles", "Europe/London", "Europe/Paris", "Europe/Berlin",
  "Asia/Tokyo", "Asia/Shanghai", "Asia/Kolkata", "Australia/Sydney",
];

interface SectionCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
}

function SectionCard({ icon, title, description, children }: SectionCardProps) {
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
      <div className="flex items-start gap-3 px-5 py-4 border-b border-[var(--border)] bg-[var(--surface-2)]">
        <span className="mt-0.5 text-[var(--accent)]">{icon}</span>
        <div>
          {/* Wave 3: Upgraded section title to text-base font-semibold for clearer hierarchy */}
          <h2 className="text-base font-semibold text-[var(--fg)]">{title}</h2>
          <p className="text-xs text-[var(--muted)] mt-0.5">{description}</p>
        </div>
      </div>
      <div className="px-5 py-4 space-y-4">{children}</div>
    </div>
  );
}

interface ToggleRowProps {
  label: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}

function ToggleRow({ label, description, checked, onChange, disabled }: ToggleRowProps) {
  return (
    <div className="flex items-center justify-between gap-4 py-1">
      <div className="min-w-0">
        <p className="text-sm font-medium text-[var(--fg)]">{label}</p>
        <p className="text-xs text-[var(--muted)]">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={[
          "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50",
          checked ? "bg-[var(--accent)]" : "bg-[var(--border)]",
        ].join(" ")}
      >
        <span
          className={[
            "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform",
            checked ? "translate-x-4" : "translate-x-0",
          ].join(" ")}
        />
      </button>
    </div>
  );
}

interface SaveBarProps {
  saving: boolean;
  saved: boolean;
  error: string | null;
  onSave: () => void;
}

function SaveBar({ saving, saved, error, onSave }: SaveBarProps) {
  return (
    <div className="sticky bottom-0 z-10 flex items-center justify-between gap-3 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)]/95 px-5 py-3 backdrop-blur shadow-sm">
      <div className="flex items-center gap-2 text-sm">
        {error ? (
          <>
            <AlertCircle className="size-4 text-red-500" />
            <span className="text-red-500">{error}</span>
          </>
        ) : saved ? (
          <>
            <CheckCircle className="size-4 text-emerald-500" />
            <span className="text-emerald-600">Settings saved</span>
          </>
        ) : (
          <span className="text-[var(--muted)]">Unsaved changes</span>
        )}
      </div>
      <button
        type="button"
        onClick={onSave}
        disabled={saving}
        className="inline-flex items-center gap-2 rounded-[var(--radius-md)] bg-[var(--accent)] px-4 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60 transition-opacity"
      >
        {saving ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <Save className="size-4" />
        )}
        {saving ? "Saving…" : "Save changes"}
      </button>
    </div>
  );
}

export function AccountSettingsPage() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [settings, setSettings] = useState<AccountSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [timezone, setTimezone] = useState("UTC");

  const [notifyAlertTriggers, setNotifyAlertTriggers] = useState(true);
  const [notifyWatchlistUpdates, setNotifyWatchlistUpdates] = useState(true);
  const [notifyResearchPublished, setNotifyResearchPublished] = useState(false);
  const [notifyPortfolioChanges, setNotifyPortfolioChanges] = useState(true);
  const [notifySystemAnnouncements, setNotifySystemAnnouncements] = useState(true);

  const [emailDigestFrequency, setEmailDigestFrequency] = useState<AccountSettings["emailDigestFrequency"]>("daily");

  const [resendWebhookEnabled, setResendWebhookEnabled] = useState(false);
  const [resendWebhookAlerts, setResendWebhookAlerts] = useState(false);
  const [resendWebhookDigest, setResendWebhookDigest] = useState(false);
  const [resendWebhookResearch, setResendWebhookResearch] = useState(false);
  const [resendWebhookUrl, setResendWebhookUrl] = useState("");

  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const markDirty = useCallback(() => {
    setDirty(true);
    setSaved(false);
    setSaveError(null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [p, s] = await Promise.all([getProfileData(), getAccountSettings()]);
        if (cancelled) return;
        setProfile(p);
        setDisplayName(p?.displayName ?? "");
        if (s) {
          setSettings(s);
          setBio(s.bio ?? "");
          setTimezone(s.timezone ?? "UTC");
          setNotifyAlertTriggers(s.notifyAlertTriggers);
          setNotifyWatchlistUpdates(s.notifyWatchlistUpdates);
          setNotifyResearchPublished(s.notifyResearchPublished);
          setNotifyPortfolioChanges(s.notifyPortfolioChanges);
          setNotifySystemAnnouncements(s.notifySystemAnnouncements);
          setEmailDigestFrequency(s.emailDigestFrequency);
          setResendWebhookEnabled(s.resendWebhookEnabled);
          setResendWebhookAlerts(s.resendWebhookAlerts);
          setResendWebhookDigest(s.resendWebhookDigest);
          setResendWebhookResearch(s.resendWebhookResearch);
          setResendWebhookUrl(s.resendWebhookUrl ?? "");
        }
      } catch (err) {
        if (!cancelled) setLoadError((err as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  async function handleSave() {
    setSaving(true);
    setSaveError(null);

    // Detect which fields changed relative to loaded state
    const changedFields: string[] = [];
    if (settings) {
      if (displayName !== (profile?.displayName ?? "")) changedFields.push("display_name");
      if (bio !== (settings.bio ?? "")) changedFields.push("bio");
      if (timezone !== (settings.timezone ?? "UTC")) changedFields.push("timezone");
      if (notifyAlertTriggers !== settings.notifyAlertTriggers) changedFields.push("notify_alert_triggers");
      if (notifyWatchlistUpdates !== settings.notifyWatchlistUpdates) changedFields.push("notify_watchlist_updates");
      if (notifyResearchPublished !== settings.notifyResearchPublished) changedFields.push("notify_research_published");
      if (notifyPortfolioChanges !== settings.notifyPortfolioChanges) changedFields.push("notify_portfolio_changes");
      if (notifySystemAnnouncements !== settings.notifySystemAnnouncements) changedFields.push("notify_system_announcements");
      if (emailDigestFrequency !== settings.emailDigestFrequency) changedFields.push("email_digest_frequency");
      if (resendWebhookEnabled !== settings.resendWebhookEnabled) changedFields.push("resend_webhook_enabled");
      if (resendWebhookAlerts !== settings.resendWebhookAlerts) changedFields.push("resend_webhook_alerts");
      if (resendWebhookDigest !== settings.resendWebhookDigest) changedFields.push("resend_webhook_digest");
      if (resendWebhookResearch !== settings.resendWebhookResearch) changedFields.push("resend_webhook_research");
      if (resendWebhookUrl !== (settings.resendWebhookUrl ?? "")) changedFields.push("resend_webhook_url");
    }

    try {
      await Promise.all([
        updateDisplayName(displayName),
        upsertAccountSettings({
          bio: bio || null,
          timezone,
          notifyAlertTriggers,
          notifyWatchlistUpdates,
          notifyResearchPublished,
          notifyPortfolioChanges,
          notifySystemAnnouncements,
          emailDigestFrequency,
          resendWebhookEnabled,
          resendWebhookAlerts,
          resendWebhookDigest,
          resendWebhookResearch,
          resendWebhookUrl: resendWebhookUrl || null,
        }),
      ]);
      trackAccountSettingsSaved({ changed_fields: changedFields });
      setSaved(true);
      setDirty(false);
    } catch (err) {
      setSaveError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="size-6 animate-spin text-[var(--muted)]" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex items-center gap-2 rounded-[var(--radius-md)] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
        <AlertCircle className="size-4 shrink-0" />
        {loadError}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Account Settings"
        description="Manage your profile, notification preferences, email digest frequency, and integration webhooks."
      />

      <div className="grid gap-5 lg:grid-cols-2">
        {/* Profile Editor */}
        <SectionCard
          icon={<User className="size-4" />}
          title="Profile"
          description="Update your display name, bio, and timezone"
        >
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-[var(--muted)] mb-1">
                Email address
              </label>
              <input
                type="email"
                value={profile?.email ?? ""}
                readOnly
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--muted)] cursor-not-allowed"
              />
              <p className="mt-1 text-xs text-[var(--muted)]">Email cannot be changed here</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--fg)] mb-1">
                Display name
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => { setDisplayName(e.target.value); markDirty(); }}
                placeholder="Your display name"
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--fg)] mb-1">
                Bio
              </label>
              <textarea
                value={bio}
                onChange={(e) => { setBio(e.target.value); markDirty(); }}
                rows={3}
                placeholder="A short bio about yourself"
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] resize-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--fg)] mb-1">
                Timezone
              </label>
              <div className="relative">
                <select
                  value={timezone}
                  onChange={(e) => { setTimezone(e.target.value); markDirty(); }}
                  className="w-full appearance-none rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-3 py-2 pr-8 text-sm text-[var(--fg)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                >
                  {TIMEZONES.map((tz) => (
                    <option key={tz} value={tz}>{tz}</option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 size-4 text-[var(--muted)]" />
              </div>
            </div>
          </div>
        </SectionCard>

        {/* Notification Preferences */}
        <SectionCard
          icon={<Bell className="size-4" />}
          title="Notification preferences"
          description="Choose which events trigger in-app and email notifications"
        >
          <div className="divide-y divide-[var(--border)]">
            <ToggleRow
              label="Alert triggers"
              description="Notify when a metric threshold is crossed"
              checked={notifyAlertTriggers}
              onChange={(v) => { setNotifyAlertTriggers(v); markDirty(); }}
            />
            <ToggleRow
              label="Watchlist updates"
              description="Notify on price or news changes for watchlisted tickers"
              checked={notifyWatchlistUpdates}
              onChange={(v) => { setNotifyWatchlistUpdates(v); markDirty(); }}
            />
            <ToggleRow
              label="Research published"
              description="Notify when new research reports are available"
              checked={notifyResearchPublished}
              onChange={(v) => { setNotifyResearchPublished(v); markDirty(); }}
            />
            <ToggleRow
              label="Portfolio changes"
              description="Notify on significant portfolio value movements"
              checked={notifyPortfolioChanges}
              onChange={(v) => { setNotifyPortfolioChanges(v); markDirty(); }}
            />
            <ToggleRow
              label="System announcements"
              description="Platform updates, maintenance windows, and releases"
              checked={notifySystemAnnouncements}
              onChange={(v) => { setNotifySystemAnnouncements(v); markDirty(); }}
            />
          </div>
        </SectionCard>

        {/* Email Digest Frequency */}
        <SectionCard
          icon={<Mail className="size-4" />}
          title="Email digest frequency"
          description="How often you receive summary emails from the platform"
        >
          <div className="space-y-2">
            {DIGEST_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className={[
                  "flex items-start gap-3 rounded-[var(--radius-sm)] border px-4 py-3 cursor-pointer transition-colors",
                  emailDigestFrequency === opt.value
                    ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                    : "border-[var(--border)] hover:bg-[var(--surface-2)]",
                ].join(" ")}
              >
                <input
                  type="radio"
                  name="emailDigest"
                  value={opt.value}
                  checked={emailDigestFrequency === opt.value}
                  onChange={() => { setEmailDigestFrequency(opt.value); markDirty(); }}
                  className="mt-0.5 accent-[var(--accent)]"
                />
                <div>
                  <p className="text-sm font-medium text-[var(--fg)]">{opt.label}</p>
                  <p className="text-xs text-[var(--muted)]">{opt.description}</p>
                </div>
              </label>
            ))}
          </div>
        </SectionCard>

        {/* Resend Webhook Integrations */}
        <SectionCard
          icon={<Webhook className="size-4" />}
          title="Resend webhook integrations"
          description="Route platform events to your Resend webhook endpoint"
        >
          <div className="space-y-4">
            <ToggleRow
              label="Enable Resend webhooks"
              description="Master toggle — enables all webhook delivery below"
              checked={resendWebhookEnabled}
              onChange={(v) => { setResendWebhookEnabled(v); markDirty(); }}
            />
            <div className={resendWebhookEnabled ? "space-y-3" : "space-y-3 opacity-40 pointer-events-none"}>
              <div>
                <label className="block text-xs font-medium text-[var(--fg)] mb-1">
                  Webhook URL
                </label>
                <input
                  type="url"
                  value={resendWebhookUrl}
                  onChange={(e) => { setResendWebhookUrl(e.target.value); markDirty(); }}
                  placeholder="https://your-endpoint.com/webhooks/resend"
                  disabled={!resendWebhookEnabled}
                  className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] disabled:cursor-not-allowed"
                />
              </div>
              <div className="divide-y divide-[var(--border)]">
                <ToggleRow
                  label="Alert events"
                  description="Send webhook on alert trigger events"
                  checked={resendWebhookAlerts}
                  onChange={(v) => { setResendWebhookAlerts(v); markDirty(); }}
                  disabled={!resendWebhookEnabled}
                />
                <ToggleRow
                  label="Digest emails"
                  description="Send webhook when digest emails are dispatched"
                  checked={resendWebhookDigest}
                  onChange={(v) => { setResendWebhookDigest(v); markDirty(); }}
                  disabled={!resendWebhookEnabled}
                />
                <ToggleRow
                  label="Research events"
                  description="Send webhook when research reports are published"
                  checked={resendWebhookResearch}
                  onChange={(v) => { setResendWebhookResearch(v); markDirty(); }}
                  disabled={!resendWebhookEnabled}
                />
              </div>
            </div>
          </div>
        </SectionCard>
      </div>

      {dirty || saving || saved || saveError ? (
        <SaveBar
          saving={saving}
          saved={saved}
          error={saveError}
          onSave={handleSave}
        />
      ) : null}
    </div>
  );
}
