"use client";

type Props = {
  title: string;
  data: unknown;
  loading?: boolean;
  error?: string | null;
};

export function ControlCenterJsonPanel({
  title,
  data,
  loading,
  error,
}: Props) {
  if (loading) {
    return (
      <p className="text-sm text-[var(--dsp-text-muted)]">Loading {title}…</p>
    );
  }
  if (error) {
    return (
      <p className="text-sm text-[var(--dsp-danger)]" role="alert">
        {error}
      </p>
    );
  }
  if (data == null) {
    return (
      <p className="text-sm text-[var(--dsp-text-muted)]">Data unavailable.</p>
    );
  }
  return (
    <section className="rounded-lg border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-4">
      <h2 className="mb-2 text-base font-semibold">{title}</h2>
      <pre
        className="max-h-[28rem] overflow-auto whitespace-pre-wrap break-words font-mono text-xs text-[var(--dsp-text)]"
        data-testid="control-center-json"
      >
        {JSON.stringify(data, null, 2)}
      </pre>
    </section>
  );
}
