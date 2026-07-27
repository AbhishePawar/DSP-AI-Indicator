import { NextResponse } from "next/server";

import { getBuildInfo } from "@/lib/observability/buildInfo";

export const dynamic = "force-dynamic";

export async function GET() {
  const info = getBuildInfo();
  return NextResponse.json({
    status: "alive",
    ready: true,
    application_version: info.applicationVersion,
    frontend_version: info.frontendVersion,
    environment: info.environment,
    build_timestamp: info.buildTimestamp,
    api_base_url: info.apiBaseUrl,
  });
}
