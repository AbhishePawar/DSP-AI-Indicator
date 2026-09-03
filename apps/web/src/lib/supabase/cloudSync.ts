import { COOKIE_TOKEN_PLACEHOLDER } from "@/lib/auth/sessionStore";
import { cookieFetchInit } from "@/lib/auth/cookieSession";
import type { Session } from "@/lib/auth/types";
import type { UserDataBundle } from "@/lib/persistence/types";
import type { WatchlistEntry } from "@/lib/portfolio-intelligence/prefsStore";

import type { CloudPersistenceSnapshot } from "./appData";

type PersistenceEnvelope = {
  ok: boolean;
  configured?: boolean;
  snapshot?: CloudPersistenceSnapshot | null;
  error?: string;
  message?: string;
};

function authHeaders(session: Session): Headers {
  const headers = new Headers({ Accept: "application/json" });
  if (
    session.accessToken &&
    session.accessToken !== COOKIE_TOKEN_PLACEHOLDER
  ) {
    headers.set("Authorization", `Bearer ${session.accessToken}`);
  }
  return headers;
}

export async function fetchCloudPersistence(
  session: Session,
): Promise<PersistenceEnvelope> {
  const response = await fetch(
    "/api/app/persistence",
    cookieFetchInit({ method: "GET", headers: authHeaders(session) }),
  );
  const body = (await response.json()) as PersistenceEnvelope;
  return body;
}

export async function saveCloudPersistence(
  session: Session,
  bundle: UserDataBundle,
  watchlist: WatchlistEntry[],
): Promise<PersistenceEnvelope> {
  const headers = authHeaders(session);
  headers.set("Content-Type", "application/json");
  const response = await fetch(
    "/api/app/persistence",
    cookieFetchInit({
      method: "PUT",
      headers,
      body: JSON.stringify({ bundle, watchlist }),
    }),
  );
  const body = (await response.json()) as PersistenceEnvelope;
  return body;
}
