/** Client-side auth form helpers — UX only; no API contract changes. */

export type PasswordStrength = {
  score: 0 | 1 | 2 | 3 | 4;
  label: "Too weak" | "Weak" | "Fair" | "Strong" | "Excellent";
  hints: string[];
};

/** Browser OAuth callback path used by Google begin/complete. */
export const OAUTH_CALLBACK_PATH = "/oauth/callback";

/** Canonical public website origin for production auth. */
export const CANONICAL_PRODUCTION_ORIGIN = "https://dspaiindicator.com";

export function oauthRedirectUri(origin: string): string {
  return `${String(origin || "").replace(/\/$/, "")}${OAUTH_CALLBACK_PATH}`;
}

export function isValidEmail(value: string): boolean {
  const v = value.trim();
  if (!v || v.length > 254) return false;
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
}

/** Match backend India mobile normalization (auth.otp.normalize_india_mobile). */
const INDIA_MOBILE_RE = /^(?:\+91|91|0)?([6-9]\d{9})$/;

export function normalizeIndiaMobileInput(value: string): string | null {
  const raw = (value || "").trim().replace(/[\s-]/g, "");
  const match = INDIA_MOBILE_RE.exec(raw);
  if (!match) return null;
  return `+91${match[1]}`;
}

/** 10-digit local number used as an editable username suggestion. */
export function suggestedUsernameFromMobile(value: string): string {
  const normalized = normalizeIndiaMobileInput(value);
  return normalized ? normalized.slice(-10) : "";
}

/**
 * Normalize a unified OTP/password identifier for API submission.
 * Emails lowercased; India mobiles normalized to +91XXXXXXXXXX; else trimmed.
 */
export function normalizeLoginIdentifier(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "";
  if (trimmed.includes("@")) return trimmed.toLowerCase();
  const mobile = normalizeIndiaMobileInput(trimmed);
  return mobile ?? trimmed;
}

export function isPlausibleLoginIdentifier(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) return false;
  if (trimmed.includes("@")) return isValidEmail(trimmed);
  if (normalizeIndiaMobileInput(trimmed)) return true;
  // Username: 3–64 of common username charset (server validates strictly).
  return /^[a-zA-Z0-9._-]{3,64}$/.test(trimmed);
}

export function evaluatePasswordStrength(password: string): PasswordStrength {
  const hints: string[] = [];
  let score = 0 as PasswordStrength["score"];

  if (password.length >= 8) score = 1;
  if (password.length >= 12) score = 2;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score = Math.max(score, 2) as PasswordStrength["score"];
  if (/\d/.test(password)) score = Math.min(4, score + 1) as PasswordStrength["score"];
  if (/[^A-Za-z0-9]/.test(password)) score = Math.min(4, score + 1) as PasswordStrength["score"];
  if (password.length >= 16 && score >= 3) score = 4;

  if (password.length < 8) hints.push("Use at least 8 characters");
  if (!/[A-Z]/.test(password) || !/[a-z]/.test(password)) {
    hints.push("Mix upper and lower case");
  }
  if (!/\d/.test(password)) hints.push("Add a number");
  if (!/[^A-Za-z0-9]/.test(password)) hints.push("Add a symbol");

  const labels: PasswordStrength["label"][] = [
    "Too weak",
    "Weak",
    "Fair",
    "Strong",
    "Excellent",
  ];

  return { score, label: labels[score]!, hints: hints.slice(0, 3) };
}

export function mapAuthError(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error ?? "");
  const lower = message.toLowerCase();

  if (
    lower.includes("429") ||
    lower.includes("rate") ||
    lower.includes("too many")
  ) {
    return "Too many attempts. Wait a moment, then try again.";
  }
  if (
    lower.includes("invalid credentials") ||
    lower.includes("401") ||
    lower.includes("unauthorized") ||
    lower.includes("wrong password") ||
    lower.includes("bad credentials")
  ) {
    return "Unable to sign in. Please verify your credentials.";
  }
  if (
    lower.includes("network") ||
    lower.includes("fetch") ||
    lower.includes("timeout") ||
    lower.includes("failed to fetch")
  ) {
    return "Authentication service temporarily unavailable. Check your connection and try again.";
  }
  if (
    lower.includes("503") ||
    lower.includes("502") ||
    lower.includes("500") ||
    lower.includes("unavailable")
  ) {
    return "Authentication service temporarily unavailable. Try again shortly.";
  }
  if (lower.includes("403") || lower.includes("forbidden")) {
    return "Unable to sign in. Access is not permitted for this account. Contact your administrator.";
  }
  // Never surface raw API paths or implementation details to end users.
  if (
    lower.includes("/api/") ||
    lower.includes("http") ||
    lower.includes("endpoint") ||
    lower.includes("rbac")
  ) {
    return "Unable to sign in. Please try again or contact your administrator.";
  }
  return "Unable to sign in. Please verify your credentials or try again later.";
}
