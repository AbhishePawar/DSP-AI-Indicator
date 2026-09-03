import { NextResponse } from "next/server";

import { getSupabaseAdminClient } from "@/lib/supabase/adminClient";
import { ensureProfile } from "@/lib/supabase/appData";
import { verifyDspUser } from "@/lib/supabase/dspSession";
import { isSupabaseBrowserConfigured } from "@/lib/supabase/publicConfig";

export const dynamic = "force-dynamic";

const ALLOWED_TYPES = new Set([
  "application/pdf",
  "text/plain",
  "image/png",
  "image/jpeg",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);

function jsonError(message: string, status: number) {
  return NextResponse.json({ ok: false, error: message, message }, { status });
}

export async function POST(request: Request) {
  if (!isSupabaseBrowserConfigured()) {
    return jsonError("Document storage is not configured.", 503);
  }
  const admin = getSupabaseAdminClient();
  if (!admin) return jsonError("Document storage is not configured.", 503);
  const user = await verifyDspUser(request);
  if (!user) return jsonError("Authentication required.", 401);

  let body: { filename?: string; contentType?: string; byteSize?: number };
  try {
    body = (await request.json()) as {
      filename?: string;
      contentType?: string;
      byteSize?: number;
    };
  } catch {
    return jsonError("Invalid document request.", 400);
  }

  const filename = (body.filename ?? "").replace(/[^a-zA-Z0-9._-]/g, "_");
  const contentType = body.contentType ?? "application/octet-stream";
  const byteSize = Number(body.byteSize ?? 0);
  if (!filename || filename.length > 180) {
    return jsonError("Filename is required.", 400);
  }
  if (!ALLOWED_TYPES.has(contentType)) {
    return jsonError("Unsupported document type.", 400);
  }
  if (!Number.isFinite(byteSize) || byteSize <= 0 || byteSize > 20 * 1024 * 1024) {
    return jsonError("Document exceeds size limit.", 400);
  }

  try {
    const profileId = await ensureProfile(admin, user);
    const objectPath = `${profileId}/${crypto.randomUUID()}-${filename}`;
    const { data, error } = await admin.storage
      .from("user-documents")
      .createSignedUploadUrl(objectPath);
    if (error || !data?.signedUrl) {
      return jsonError("Unable to create upload URL.", 503);
    }
    const { error: metaError } = await admin.from("stored_documents").insert({
      user_id: profileId,
      storage_path: `user-documents/${objectPath}`,
      filename,
      content_type: contentType,
      byte_size: byteSize,
      document_kind: "user_upload",
    });
    if (metaError) return jsonError("Unable to store document metadata.", 503);
    return NextResponse.json({
      ok: true,
      path: objectPath,
      signedUrl: data.signedUrl,
      token: data.token,
    });
  } catch {
    return jsonError("Unable to prepare document upload.", 503);
  }
}

export async function GET(request: Request) {
  if (!isSupabaseBrowserConfigured()) {
    return NextResponse.json({ ok: true, configured: false, documents: [] });
  }
  const admin = getSupabaseAdminClient();
  if (!admin) return jsonError("Document storage is not configured.", 503);
  const user = await verifyDspUser(request);
  if (!user) return jsonError("Authentication required.", 401);
  try {
    const profileId = await ensureProfile(admin, user);
    const { data, error } = await admin
      .from("stored_documents")
      .select("id, filename, content_type, byte_size, created_at")
      .eq("user_id", profileId)
      .order("created_at", { ascending: false });
    if (error) return jsonError("Unable to list documents.", 503);
    return NextResponse.json({ ok: true, configured: true, documents: data ?? [] });
  } catch {
    return jsonError("Unable to list documents.", 503);
  }
}
