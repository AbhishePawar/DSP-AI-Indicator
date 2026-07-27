"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth/AuthProvider";
import { isAuthPublicPath, normalizePath } from "@/lib/auth/routeGuards";
import { env } from "@/lib/env";

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, status, session } = useAuth();
  const [username, setUsername] = useState("admin");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const nextPath = normalizePath(searchParams.get("next") || "/dashboard");
  const expired = searchParams.get("expired") === "1";

  useEffect(() => {
    if (status === "authenticated" && session) {
      router.replace(isAuthPublicPath(nextPath) ? "/dashboard" : nextPath);
    }
  }, [status, session, nextPath, router]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await login({ username, rememberMe });
      router.replace(isAuthPublicPath(nextPath) ? "/dashboard" : nextPath);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="relative grid min-h-screen place-items-center px-4">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--glow)_0%,_transparent_50%)]" />
      <div className="relative w-full max-w-md border-y border-[var(--border)] bg-[var(--surface)]/90 p-8 shadow-[0_24px_80px_rgba(16,22,20,0.12)] backdrop-blur">
        <p className="font-[family-name:var(--font-display)] text-3xl text-[var(--accent)]">
          {env.appName}
        </p>
        <p className="mt-1 font-[family-name:var(--font-display)] text-lg tracking-tight text-[var(--fg)]">
          Complex Analysis. Simple Decisions.
        </p>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Sign in to access portfolio, copilot, diagnostics, and profile.
          Public research routes remain available without authentication.
        </p>

        {expired ? (
          <div className="mt-4">
            <Alert tone="warning" title="Session expired">
              Your session has expired. Please sign in again.
            </Alert>
          </div>
        ) : null}

        <form className="mt-8 space-y-4" onSubmit={onSubmit}>
          <label className="block text-sm">
            <span className="text-[var(--muted)]">Username</span>
            <input
              className="mt-1 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 outline-none ring-[var(--accent)] focus:ring-2"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="rounded border-[var(--border)]"
            />
            Remember me on this device
          </label>
          {error ? (
            <p className="rounded-md border border-[var(--danger-border)] bg-[var(--danger-bg)] px-3 py-2 text-sm text-[var(--danger-fg)]">
              {error}
            </p>
          ) : null}
          <Button type="submit" disabled={pending} className="w-full">
            {pending ? "Signing in…" : "Sign in"}
          </Button>
        </form>
        <p className="mt-6 text-xs text-[var(--muted)]">
          RC note: seeded user <code>admin</code> ·{" "}
          <code>POST /api/v1/auth/login</code>
        </p>
      </div>
    </div>
  );
}
