import { env } from "@/lib/env";
import { COOKIE_TOKEN_PLACEHOLDER } from "@/lib/auth/sessionStore";

export type VerifiedDspUser = {
  subject: string;
  email: string | null;
  displayName: string | null;
};

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

export async function verifyDspUser(request: Request): Promise<VerifiedDspUser | null> {
  const authorization = request.headers.get("authorization");
  const cookie = request.headers.get("cookie");
  const hasBearer =
    Boolean(authorization) &&
    authorization!.toLowerCase().startsWith("bearer ") &&
    !authorization!.includes(COOKIE_TOKEN_PLACEHOLDER);

  if (!hasBearer && !cookie) return null;

  const headers = new Headers({ Accept: "application/json" });
  if (hasBearer && authorization) headers.set("Authorization", authorization);
  if (cookie) headers.set("Cookie", cookie);

  try {
    const response = await fetch(`${env.apiBaseUrl}/auth/rbac/me`, {
      method: "GET",
      headers,
      cache: "no-store",
    });
    if (!response.ok) return null;
    const body = (await response.json()) as {
      ok?: boolean;
      result?: {
        user_id?: string;
        email?: string;
        display_name?: string;
        username?: string;
      };
    };
    if (!body?.ok || !body.result) return null;
    const subject = firstString(body.result.user_id, body.result.username);
    if (!subject) return null;
    return {
      subject,
      email: firstString(body.result.email),
      displayName: firstString(body.result.display_name, body.result.username),
    };
  } catch {
    return null;
  }
}
