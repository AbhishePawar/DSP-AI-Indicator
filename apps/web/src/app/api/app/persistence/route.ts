import { NextResponse } from "next/server";

import { getSupabaseAdminClient } from "@/lib/supabase/adminClient";
import {
  ensureProfile,
  readCloudSnapshot,
  writeCloudSnapshot,
} from "@/lib/supabase/appData";
import { verifyDspUser } from "@/lib/supabase/dspSession";
import { isSupabaseBrowserConfigured } from "@/lib/supabase/publicConfig";
import type { UserDataBundle } from "@/lib/persistence/types";
import type { WatchlistEntry } from "@/lib/portfolio-intelligence/prefsStore";

export const dynamic = "force-dynamic";

function jsonError(message: string, status: number) {
  return NextResponse.json({ ok: false, error: message, message }, { status });
}

export async function GET(request: Request) {
  if (!isSupabaseBrowserConfigured()) {
    return NextResponse.json({ ok: true, configured: false, snapshot: null });
  }
  const admin = getSupabaseAdminClient();
  if (!admin) {
    return jsonError("Application persistence is not configured.", 503);
  }
  const user = await verifyDspUser(request);
  if (!user) return jsonError("Authentication required.", 401);
  try {
    const profileId = await ensureProfile(admin, user);
    const snapshot = await readCloudSnapshot(admin, profileId);
    return NextResponse.json({ ok: true, configured: true, snapshot });
  } catch {
    return jsonError("Unable to load application data.", 503);
  }
}

export async function PUT(request: Request) {
  if (!isSupabaseBrowserConfigured()) {
    return NextResponse.json({ ok: true, configured: false, snapshot: null });
  }
  const admin = getSupabaseAdminClient();
  if (!admin) {
    return jsonError("Application persistence is not configured.", 503);
  }
  const user = await verifyDspUser(request);
  if (!user) return jsonError("Authentication required.", 401);

  let body: { bundle?: UserDataBundle; watchlist?: WatchlistEntry[] };
  try {
    body = (await request.json()) as {
      bundle?: UserDataBundle;
      watchlist?: WatchlistEntry[];
    };
  } catch {
    return jsonError("Invalid persistence payload.", 400);
  }
  if (!body.bundle || body.bundle.subject !== user.subject) {
    return jsonError("Identity mismatch.", 403);
  }

  try {
    const profileId = await ensureProfile(admin, user);
    await writeCloudSnapshot(admin, profileId, body.bundle, body.watchlist ?? []);
    const snapshot = await readCloudSnapshot(admin, profileId);
    return NextResponse.json({ ok: true, configured: true, snapshot });
  } catch {
    return jsonError("Unable to save application data.", 503);
  }
}
