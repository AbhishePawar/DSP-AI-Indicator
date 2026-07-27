/** Safe text helpers — Sprint 9 security hardening (no business logic). */

/** Escape HTML entities for safe insertion into HTML strings. */
export function escapeHtml(input: string): string {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Strip control characters that can confuse logs or downloads. */
export function sanitizePlainText(input: string, maxLen = 50_000): string {
  return input.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "").slice(0, maxLen);
}

/** Validate a download filename (no path traversal). */
export function safeDownloadFilename(name: string, fallback = "dsp-export.txt"): string {
  const cleaned = name.replace(/[\\/:*?"<>|]+/g, "_").replace(/\.\./g, "_").trim();
  if (!cleaned || cleaned === "." || cleaned === "..") return fallback;
  return cleaned.slice(0, 180);
}

/** Reject javascript: / data: URLs in user-provided links. */
export function isSafeHref(href: string): boolean {
  const t = href.trim().toLowerCase();
  if (t.startsWith("javascript:") || t.startsWith("data:") || t.startsWith("vbscript:")) {
    return false;
  }
  return t.startsWith("#") || t.startsWith("/") || t.startsWith("https:") || t.startsWith("http:");
}
