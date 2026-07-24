export default function Loading() {
  return (
    <div className="flex items-center gap-3 text-sm text-[var(--muted)]">
      <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-[var(--accent)] border-r-transparent" />
      Loading…
    </div>
  );
}
