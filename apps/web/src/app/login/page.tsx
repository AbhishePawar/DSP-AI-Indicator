"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { env } from "@/lib/env";

export default function LoginPage() {
  const router = useRouter();
  const { setSession } = useAuth();
  const [username, setUsername] = useState("admin");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const result = await api.login({ username: username.trim() });
      if (!result.ok || !result.payload?.access_token) {
        throw new Error(result.errors?.[0] || "Login failed");
      }
      setSession({
        accessToken: result.payload.access_token,
        role: result.payload.role,
        subject: result.payload.subject,
        username: result.payload.username,
      });
      router.replace("/dashboard");
    } catch (err) {
      const message =
        err instanceof ApiClientError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Login failed";
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
          Professional Investment Research for Everyone. Sign in to the research
          workspace — analysis runs only on the backend API.
        </p>
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
          {error ? (
            <p className="rounded-md border border-[var(--danger-border)] bg-[var(--danger-bg)] px-3 py-2 text-sm text-[var(--danger-fg)]">
              {error}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={pending}
            className="w-full rounded-md bg-[var(--accent)] px-3 py-2.5 text-[var(--accent-fg)] disabled:opacity-60"
          >
            {pending ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="mt-6 text-xs text-[var(--muted)]">
          RC note: seeded user <code>admin</code> ·{" "}
          <code>POST /api/v1/auth/login</code>
        </p>
      </div>
    </div>
  );
}
