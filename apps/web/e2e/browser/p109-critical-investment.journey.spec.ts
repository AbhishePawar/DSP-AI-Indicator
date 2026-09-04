import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

/**
 * P1-09 — critical investment browser journey (Chromium).
 *
 * evidence_class = test_fixture — never real_live_authenticated_provider.
 */

const API_BASE =
  process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const TICKER = process.env.DSP_P109_TICKER ?? "DSPFIX";
const ADMIN_ID = process.env.DSP_P109_LOGIN ?? "admin";
const ADMIN_PASSWORD =
  process.env.DSP_SEED_ADMIN_PASSWORD ?? process.env.DSP_P109_PASSWORD;

if (!ADMIN_PASSWORD) {
  throw new Error(
    "P1-09 requires DSP_SEED_ADMIN_PASSWORD or DSP_P109_PASSWORD for fixture login",
  );
}

const EVIDENCE_CLASS = "test_fixture";

/** Seed browser state so tour/disclaimer do not block the hard-gate journey. */
async function seedNonBlockingBrowserState(page: Page) {
  await page.addInitScript(() => {
    try {
      window.localStorage.setItem(
        "dsp.researchDisclaimer.acknowledged.v1",
        "1",
      );
      window.localStorage.setItem(
        "dsp.researchDisclaimer.acknowledged.v1.at",
        new Date().toISOString(),
      );
      window.localStorage.setItem(
        "dsp.beta.onboarding.v1",
        JSON.stringify({ completed: true, step: 0 }),
      );
    } catch {
      /* private mode */
    }
  });
}

async function acknowledgeDisclaimerIfPresent(page: Page) {
  const disclaimer = page.getByRole("dialog", {
    name: /Investment research disclaimer/i,
  });
  if (!(await disclaimer.isVisible().catch(() => false))) return;
  await disclaimer
    .getByRole("checkbox", {
      name: /I understand the investment research disclaimer/i,
    })
    .check({ force: true });
  await disclaimer
    .getByRole("button", { name: /Acknowledge and continue/i })
    .click({ force: true });
  await expect(disclaimer).toBeHidden({ timeout: 15_000 });
}

test.describe("P1-09 critical investment journey", () => {
  test.describe.configure({ mode: "serial" });

  test("API health ready before browser journey", async ({ request }) => {
    const root = API_BASE.replace(/\/api\/v1$/, "");
    expect((await request.get(`${root}/health/live`)).ok()).toBeTruthy();
    expect((await request.get(`${root}/health/ready`)).ok()).toBeTruthy();
  });

  test("login → analyse → valuation → Buffett → provenance → export", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    await seedNonBlockingBrowserState(page);

    // Safety net if onboarding still opens (do not also click Skip manually).
    await page.addLocatorHandler(
      page.getByRole("dialog", { name: "Welcome tour" }),
      async (dialog) => {
        await dialog.getByRole("button", { name: "Skip tutorial" }).click();
      },
    );

    let analyseBody: Record<string, unknown> | null = null;
    let analyseStatus: number | null = null;
    page.on("response", async (response) => {
      try {
        const url = response.url();
        if (
          response.request().method() === "POST" &&
          /\/analyse(\?|$)/.test(url) &&
          !url.includes("provenance")
        ) {
          analyseStatus = response.status();
          if (response.ok()) {
            analyseBody = (await response.json()) as Record<string, unknown>;
          }
        }
      } catch {
        /* ignore */
      }
    });

    await page.goto("/login", { waitUntil: "domcontentloaded" });

    // Follow the current accessible login contract: choose the password
    // method first, then use the labelled username/password fields.
    await page
      .getByRole("button", { name: /username and password/i })
      .click();
    await page.getByLabel("Username", { exact: true }).fill(ADMIN_ID);
    await page.getByLabel("Password", { exact: true }).fill(ADMIN_PASSWORD);
    await page.getByRole("button", { name: /^sign in$/i }).click();
    await page.waitForURL(/\/(analysis|dashboard)/, { timeout: 60_000 });

    await page.goto(`/analysis?symbol=${TICKER}`, {
      waitUntil: "domcontentloaded",
    });
    await acknowledgeDisclaimerIfPresent(page);

    const main = page.getByRole("region", { name: "Main analysis area" });
    await expect(main).toBeVisible({ timeout: 30_000 });
    await expect(page.getByLabel(/Company search/i)).toBeVisible();

    const analyseReady = async () =>
      Boolean(analyseBody?.ok === true && analyseBody?.analysis_id);

    if (!(await analyseReady())) {
      await acknowledgeDisclaimerIfPresent(page);
      await page.getByRole("button", { name: /^Analyze/i }).first().click();
      await acknowledgeDisclaimerIfPresent(page);
    }

    await expect
      .poll(
        async () => {
          if (await analyseReady()) return true;
          return analyseStatus === 200 && (await analyseReady());
        },
        {
          timeout: 90_000,
          message: `POST /analyse must succeed with analysis_id (last status=${analyseStatus})`,
        },
      )
      .toBeTruthy();

    // Token/symbol effects can re-trigger analyse; wait until analysis_id is stable.
    let stableId = "";
    let stableHits = 0;
    await expect
      .poll(
        async () => {
          const id = String(analyseBody?.analysis_id || "");
          if (id && id === stableId) {
            stableHits += 1;
          } else {
            stableId = id;
            stableHits = 0;
          }
          return Boolean(id) && stableHits >= 4;
        },
        {
          timeout: 30_000,
          intervals: [250, 250, 250, 250],
          message: "analysis_id must stabilize before provenance/export",
        },
      )
      .toBeTruthy();

    const analysisId = String(analyseBody!.analysis_id);
    const payload = (analyseBody!.payload ?? {}) as Record<string, unknown>;
    const buffett = (payload.buffett_authority ?? {}) as Record<string, unknown>;
    expect(Object.keys(buffett).length).toBeGreaterThan(0);

    const stages = (payload.stage_summaries ?? []) as Array<
      Record<string, unknown>
    >;
    const valuation = stages.find((s) => s.stage === "valuation");
    expect(valuation).toBeTruthy();
    expect(["succeeded", "degraded", "unavailable"]).toContain(
      String(valuation!.status),
    );

    await expect(
      page.getByRole("heading", { name: /Executive Summary|Summary/i }).first(),
    ).toBeVisible({ timeout: 30_000 });

    const nav = page.getByRole("navigation", { name: "Analysis sections" });
    await expect(nav).toBeVisible();
    const buffettBtn = nav.getByRole("button", { name: /Buffett/i });
    if (await buffettBtn.isVisible().catch(() => false)) {
      await buffettBtn.click();
    }

    // Reuse the authenticated browser session (cookie + CSRF or bearer).
    // Do not POST /login again via APIRequestContext — that hits CSRF without cookies.
    const provFetch = await page.evaluate(
      async ({ apiBase, id }) => {
        const csrf =
          window.sessionStorage.getItem("dsp.auth.csrf.v1") ||
          window.localStorage.getItem("dsp.auth.csrf.v1");
        let bearer: string | null = null;
        for (const store of [window.sessionStorage, window.localStorage]) {
          try {
            const raw = store.getItem("dsp.auth.session.v3");
            if (!raw) continue;
            const parsed = JSON.parse(raw) as { accessToken?: string };
            if (
              parsed.accessToken &&
              !parsed.accessToken.startsWith("cookie:")
            ) {
              bearer = parsed.accessToken;
              break;
            }
          } catch {
            /* ignore */
          }
        }
        const headers: Record<string, string> = {
          Accept: "application/json",
        };
        if (csrf) headers["X-CSRF-Token"] = csrf;
        if (bearer) headers.Authorization = `Bearer ${bearer}`;
        const res = await fetch(`${apiBase}/analyse/provenance/${id}`, {
          credentials: "include",
          headers,
        });
        const body = await res.json();
        return { ok: res.ok, status: res.status, body };
      },
      { apiBase: API_BASE, id: analysisId },
    );
    expect(
      provFetch.ok,
      `provenance HTTP ${provFetch.status}: ${JSON.stringify(provFetch.body)}`,
    ).toBeTruthy();
    const prov = (provFetch.body as { provenance: Record<string, unknown> })
      .provenance;
    expect(prov.analysis_id).toBe(analysisId);
    expect(prov.ticker).toBe(TICKER);
    const release = prov.release as Record<string, string>;
    expect(release.epic).toBe("EPS-003");
    expect(release.product_version).toBe("2.0.0-rc.1");
    expect(release.channel).toBe("rc");
    expect(release.decision).toBe("RELEASE_CANDIDATE");
    expect(prov.input_fingerprint).toBeTruthy();
    expect(prov.result_fingerprint).toBeTruthy();

    // Accessible name includes shortcut badge ("Downloads 0").
    await nav.getByRole("button", { name: /Downloads/i }).click();
    const exportJson = page.getByRole("button", { name: /Export JSON/i });
    await expect(exportJson).toBeVisible({ timeout: 15_000 });
    const downloadPromise = page.waitForEvent("download", { timeout: 30_000 });
    await exportJson.click();
    const download = await downloadPromise;
    const downloadPath = await download.path();
    expect(downloadPath).toBeTruthy();
    const exported = JSON.parse(fs.readFileSync(downloadPath!, "utf-8")) as {
      ticker?: string;
      analysisId?: string | null;
      auditReference?: string | null;
    };
    expect(exported.ticker?.toUpperCase()).toBe(TICKER);
    expect(exported.analysisId || exported.auditReference).toBe(analysisId);

    const outDir = path.join(process.cwd(), "..", "..", "artifacts");
    fs.mkdirSync(outDir, { recursive: true });
    fs.writeFileSync(
      path.join(outDir, "p109_playwright_evidence.json"),
      `${JSON.stringify(
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
      )}\n`,
      "utf-8",
    );
  });

  test("unauthenticated analyse path does not invent values for missing symbol", async ({
    page,
  }) => {
    await seedNonBlockingBrowserState(page);
    await page.goto("/analysis?symbol=ZZZZNOPE", {
      waitUntil: "domcontentloaded",
    });
    // Wait past session bootstrap — must not invent investment values.
    await expect
      .poll(
        async () => {
          const text = await page.locator("body").innerText();
          return /Sign in|Data unavailable|Analyze|Company|Workspace|Main analysis/i.test(
            text,
          );
        },
        { timeout: 30_000, message: "page must leave session loading state" },
      )
      .toBeTruthy();
    const bodyText = await page.locator("body").innerText();
    expect(bodyText.toLowerCase()).not.toMatch(/intrinsic value:\s*\$?\s*[1-9]/i);
    expect(bodyText.toLowerCase()).not.toMatch(
      /margin of safety:\s*[+-]?\d/i,
    );
  });
});
