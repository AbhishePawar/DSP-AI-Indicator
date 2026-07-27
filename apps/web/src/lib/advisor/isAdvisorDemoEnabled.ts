/**
 * Advisor demo gate — separate from Feature Flags / Research Mode.
 * Single-user experience unchanged when disabled (default).
 */

export function isAdvisorDemoEnabled(): boolean {
  const raw = process.env.NEXT_PUBLIC_ADVISOR_DEMO;
  if (raw == null || raw === "") return false;
  return raw === "1" || raw.toLowerCase() === "true" || raw.toLowerCase() === "yes";
}
