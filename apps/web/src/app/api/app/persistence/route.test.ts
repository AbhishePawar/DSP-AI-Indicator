import { beforeEach, describe, expect, it, vi } from "vitest";

const getSupabaseAdminClient = vi.fn();
const isSupabaseBrowserConfigured = vi.fn();
const verifyDspUser = vi.fn();

vi.mock("@/lib/supabase/adminClient", () => ({
  getSupabaseAdminClient: () => getSupabaseAdminClient(),
}));

vi.mock("@/lib/supabase/publicConfig", () => ({
  isSupabaseBrowserConfigured: () => isSupabaseBrowserConfigured(),
}));

vi.mock("@/lib/supabase/dspSession", () => ({
  verifyDspUser: (...args: unknown[]) => verifyDspUser(...args),
}));

vi.mock("@/lib/supabase/appData", () => ({
  ensureProfile: vi.fn(),
  readCloudSnapshot: vi.fn(),
  writeCloudSnapshot: vi.fn(),
}));

import { GET } from "./route";

describe("persistence BFF", () => {
  beforeEach(() => {
    getSupabaseAdminClient.mockReset();
    isSupabaseBrowserConfigured.mockReset();
    verifyDspUser.mockReset();
  });

  it("reports unconfigured when public supabase env is absent", async () => {
    isSupabaseBrowserConfigured.mockReturnValue(false);
    const response = await GET(new Request("http://localhost/api/app/persistence"));
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      ok: true,
      configured: false,
    });
  });

  it("rejects unauthenticated access when persistence is configured", async () => {
    isSupabaseBrowserConfigured.mockReturnValue(true);
    getSupabaseAdminClient.mockReturnValue({});
    verifyDspUser.mockResolvedValue(null);
    const response = await GET(new Request("http://localhost/api/app/persistence"));
    expect(response.status).toBe(401);
  });
});
