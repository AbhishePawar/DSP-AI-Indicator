/**
 * P2.1 — Deterministic report identity (stable for identical inputs).
 * Not a cryptographic security hash — presentation identifier only.
 */

/** FNV-1a 32-bit → hex (deterministic, no crypto deps). */
export function fnv1aHex(input: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export type ReportIdInput = {
  ticker: string;
  exchange: string;
  analysedAt: string | null;
  correlationId: string | null;
  pipelineVersion: string | null;
  platformVersion: string | null;
  frontendVersion: string;
};

/** Stable Report ID for identical generation inputs. */
export function buildReportId(input: ReportIdInput): string {
  const parts = [
    input.ticker.trim().toUpperCase(),
    input.exchange.trim().toUpperCase(),
    input.analysedAt ?? "null",
    input.correlationId ?? "null",
    input.pipelineVersion ?? "null",
    input.platformVersion ?? "null",
    input.frontendVersion,
  ];
  const digest = fnv1aHex(parts.join("|"));
  const digest2 = fnv1aHex(`${digest}|${parts.join("|")}`);
  return `DSP-RPT-${digest}${digest2}`.toUpperCase();
}
