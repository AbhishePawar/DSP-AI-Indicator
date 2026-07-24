import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-lg px-4 py-16 text-center">
      <p className="text-sm text-[var(--muted)]">404</p>
      <h1 className="mt-2 font-[family-name:var(--font-display)] text-3xl">Page not found</h1>
      <p className="mt-3 text-sm text-[var(--muted)]">
        That route is not part of the DSP Private Beta surface. No research data was changed.
      </p>
      <Link
        href="/dashboard"
        className="mt-6 inline-flex min-h-11 items-center justify-center rounded-md bg-[var(--accent)] px-4 text-sm font-medium text-[var(--accent-fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
      >
        Go to dashboard
      </Link>
    </div>
  );
}
