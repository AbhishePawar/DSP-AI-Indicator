import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

/**
 * P1-09 — critical investment browser journey (Chromium).
 *
 * Requires a running API with:
 *   DSP_ENVIRONMENT=development
 *   DSP_MARKET_QUOTE_MEMORY=1
 *   DSP_FINANCIAL_STATEMENT_MEMORY=1
 *   DSP_P109_E2E_FIXTURE=1
 *   DSP_SEED_ADMIN_PASSWORD=Admin@123 (default)
 *
 * evidence_class = test_fixture — never real_live_authenticated_provider.
 */

const API_BASE =
  process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const TICKER = process.env.DSP_P109_TICKER ?? "DSPFIX";
const ADMIN_ID = process.env.DSP_P109_LOGIN ?? "admin";
const ADMIN_PASSWORD =
  process.env.DSP_SEED_ADMIN_PASSWORD ??
  process.env.DSP_P109_PASSWORD ??
  "Admin@123";

const EVIDENCE_CLASS = "test_fixture";

async function dismissOverlays(page: Page) {
  await page.addLocatorHandler(
    page.getByRole("dialog", { name: "Welcome tour" }),
    async (dialog) => {
      await dialog.getByRole("button", { name: "Skip tutorial" }).click();
    },
  );
}

async function acknowledgeResearchDisclaimer(page: Page) {
  const dialog = page.getByRole("dialog", {
    name: /Investment research disclaimer/i,
  });
  if (await dialog.isVisible().catch(() => false)) {
    await dialog
      .getByRole("checkbox", {
        name: /I understand the investment research disclaimer/i,
      })
      .check();
    await dialog
      .getByRole("button", { name: /Acknowledge and continue/i })
      .click();
    await expect(dialog).toBeHidden({ timeout: 15_000 });
  }
}

test.describe("P1-09 critical investment journey", () => {
  test.describe.configure({ mode: "serial" });

  test("API health ready before browser journey", async ({ request }) => {
    const live = await request.get(`${API_BASE.replace(/\/api\/v1$/, "")}/health/live`);
    const ready = await request.get(
      `${API_BASE.replace(/\/api\/v1$/, "")}/health/ready`,
    );
    expect(live.ok(), `live ${live.status()}`).toBeTruthy();
    expect(ready.ok(), `ready ${ready.status()}`).toBeTruthy();
  });

  test("login → analyse → valuation → Buffett → provenance → export", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    await dismissOverlays(page);

    // Capture analyse + provenance network
    let analyseBody: Record<string, unknown> | null = null;
    page.on("response", async (response) => {
      try {
        const url = response.url();
        if (
          response.request().method() === "POST" &&
          url.includes("/analyse") &&
          !url.includes("provenance")
        ) {
          if (response.ok()) {
            analyseBody = (await response.json()) as Record<string, unknown>;
          }
        }
      } catch {
        /* ignore parse errors */
      }
    });

    // --- Login ---
    await page.goto(`/login?next=${encodeURIComponent(`/analysis?symbol=${TICKER}`)}`, {
      waitUntil: "domcontentloaded",
    });
    await page.locator("#login-identifier").fill(ADMIN_ID);
    await page.locator("#login-password").fill(ADMIN_PASSWORD);
    await page.getByRole("button", { name: /sign in/i }).click();

    // Land on analysis (or dashboard then navigate)
    await page.waitForURL(/\/(analysis|dashboard)/, { timeout: 60_000 });
    if (!page.url().includes("/analysis")) {
      await page.goto(`/analysis?symbol=${TICKER}`, {
        waitUntil: "domcontentloaded",
      });
    }

    await acknowledgeResearchDisclaimer(page);

    const main = page.getByRole("region", { name: "Main analysis area" });
    await expect(main).toBeVisible({ timeout: 30_000 });

    // Ensure symbol and run analyse if needed
    const search = page.getByLabel(/Company search/i);
    if (await search.isVisible().catch(() => false)) {
      await search.fill(TICKER);
    }
    const analyzeBtn = page.getByRole("button", { name: /^Analyze/i }).first();
    if (await analyzeBtn.isVisible().catch(() => false)) {
      await analyzeBtn.click();
      await acknowledgeResearchDisclaimer(page);
    }

    // Wait for analyse network success
    await expect
      .poll(() => analyseBody?.ok === true && Boolean(analyseBody?.analysis_id), {
        timeout: 90_000,
        message: "POST /analyse must succeed with analysis_id",
      })
      .toBeTruthy();

    const analysisId = String(analyseBody!.analysis_id);
    const payload = (analyseBody!.payload ?? {}) as Record<string, unknown>;
    const buffett = (payload.buffett_authority ?? {}) as Record<string, unknown>;
    expect(buffett, "buffett_authority from server").toBeTruthy();
    expect(Object.keys(buffett).length).toBeGreaterThan(0);

    const stages = (payload.stage_summaries ?? []) as Array<Record<string, unknown>>;
    const valuation = stages.find((s) => s.stage === "valuation");
    expect(valuation, "valuation stage present").toBeTruthy();
    expect(["succeeded", "degraded", "unavailable"]).toContain(
      String(valuation!.status),
    );

    // UI: Executive summary / analysis loaded
    await expect(
      page.getByRole("heading", { name: /Executive Summary|Summary/i }).first(),
    ).toBeVisible({ timeout: 30_000 });

    // Navigate Buffett section via left nav
    const nav = page.getByRole("navigation", { name: "Analysis sections" });
    if (await nav.isVisible().catch(() => false)) {
      const buffettBtn = nav.getByRole("button", { name: /Buffett/i });
      if (await buffettBtn.isVisible().catch(() => false)) {
        await buffettBtn.click();
      }
    }

    // Provenance via API using browser storage cookies / token is hard;
    // use request context against API with enterprise login for same analysis_id.
    const loginResp = await page.request.post(`${API_BASE}/auth/enterprise/login`, {
      data: { identifier: ADMIN_ID, password: ADMIN_PASSWORD },
    });
    expect(loginResp.ok(), await loginResp.text()).toBeTruthy();
    const loginJson = (await loginResp.json()) as {
      result?: { tokens?: { access_token?: string }; access_token?: string };
    };
    const token =
      loginJson.result?.tokens?.access_token ??
      loginJson.result?.access_token ??
      null;
    expect(token, "enterprise login token").toBeTruthy();

    const provResp = await page.request.get(
      `${API_BASE}/analyse/provenance/${analysisId}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    expect(provResp.ok(), await provResp.text()).toBeTruthy();
    const provJson = await provResp.json();
    const prov = provJson.provenance as Record<string, unknown>;
    expect(prov.analysis_id).toBe(analysisId);
    expect(prov.ticker).toBe(TICKER);
    const release = prov.release as Record<string, string>;
    expect(release.epic).toBe("EPS-003");
    expect(release.product_version).toBe("2.0.0-rc.1");
    expect(release.channel).toBe("rc");
    expect(release.decision).toBe("RELEASE_CANDIDATE");
    expect(prov.input_fingerprint).toBeTruthy();
    expect(prov.result_fingerprint).toBeTruthy();

    // Export section — JSON download must carry same analysisId / ticker
    const downloadsNav = nav.getByRole("button", { name: /^Downloads$/i });
    await expect(downloadsNav).toBeVisible({ timeout: 15_000 });
    await downloadsNav.click();

    const downloadPromise = page.waitForEvent("download", { timeout: 30_000 }).catch(
      () => null,
    );
    const exportJsonBtn = page.getByRole("button", { name: /Export JSON/i });
    await expect(exportJsonBtn).toBeVisible({ timeout: 20_000 });
    await exportJsonBtn.click();
    const download = await downloadPromise;
    expect(download, "Export JSON download").toBeTruthy();
    const downloadPath = await download!.path();
    expect(downloadPath).toBeTruthy();
    const exported = JSON.parse(fs.readFileSync(downloadPath!, "utf-8")) as {
      ticker?: string;
      analysisId?: string | null;
      auditReference?: string | null;
    };
    expect(exported.ticker?.toUpperCase()).toBe(TICKER);
    expect(exported.analysisId || exported.auditReference).toBe(analysisId);

    // Persist local evidence (test_fixture only)
    const outDir = path.join(process.cwd(), "..", "..", "artifacts");
    fs.mkdirSync(outDir, { recursive: true });
    fs.writeFileSync(
      path.join(outDir, "p109_playwright_evidence.json"),
      JSON.stringify(
        {
          ok: true,
          gate: "P1-09",
          evidence_class: EVIDENCE_CLASS,
          g2_claim: false,
          ticker: TICKER,
          analysis_id: analysisId,
          release_identity: release,
          browser: "chromium",
        },
        null,
        2,
      ) + "\n",
      "utf-8",
    );
  });

  test("unauthenticated analyse path does not invent values for missing symbol", async ({
    page,
  }) => {
    await page.goto("/analysis?symbol=ZZZZNOPE", {
      waitUntil: "domcontentloaded",
    });
    // Without login, market status should be honest / sign-in prompt — never fake IV
    const bodyText = await page.locator("body").innerText();
    expect(bodyText.toLowerCase()).not.toMatch(/intrinsic value:\s*\$?\s*[1-9]/i);
    expect(bodyText).toMatch(/Sign in|Data unavailable|Analyze|Company/i);
  });
});
