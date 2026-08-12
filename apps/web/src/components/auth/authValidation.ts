/** Client-side auth form helpers — UX only; no API contract changes. */

export type PasswordStrength = {
  score: 0 | 1 | 2 | 3 | 4;
  label: "Too weak" | "Weak" | "Fair" | "Strong" | "Excellent";
  hints: string[];
};

export function isValidEmail(value: string): boolean {
  const v = value.trim();
  if (!v || v.length > 254) return false;
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
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
