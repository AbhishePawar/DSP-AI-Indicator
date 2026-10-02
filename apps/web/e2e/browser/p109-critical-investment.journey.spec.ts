import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

import { loginWithUsernamePassword } from "./p109/login";
import { p109Stage, type P109StageRecord } from "./p109/stages";
import { assertP109Config } from "./p109/env";
import {
  assertBuffettVisible,
  assertEvidenceVisible,
  assertValuationVisible,
  attachAnalyseCapture,
  exportJsonSnapshot,
  fetchProvenanceFromSession,
  openAnalysisWorkspace,
  waitForAnalyseSuccess,
} from "./p109/workspace";

/**
 * P1-09 V2 — critical investment browser journey (Chromium).
 *
 * evidence_class = test_fixture — never real_live_authenticated_provider.
 * Stages: LOGIN → ANALYSIS → VALUATION → BUFFETT → PROVENANCE → EXPORT
 */

const P109 = assertP109Config();
const API_BASE = P109.apiBaseUrl;
const TICKER = P109.ticker;
const ADMIN_ID = P109.adminLogin;
const ADMIN_PASSWORD = P109.adminPassword;

const EVIDENCE_CLASS = "test_fixture";

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
    const live = await request.get(`${root}/health/live`);
    if (!live.ok()) {
      throw new Error(`P1-09 backend unavailable: ${root}/health/live returned ${live.status()}`);
    }
    const ready = await request.get(`${root}/health/ready`);
    if (!ready.ok()) {
      throw new Error(`P1-09 backend unavailable: ${root}/health/ready returned ${ready.status()}`);
    }
  });

  test("frontend is reachable before browser journey", async ({ request }) => {
    const response = await request.get(P109.baseUrl);
    if (!response.ok()) {
      throw new Error(`P1-09 frontend unavailable: ${P109.baseUrl} returned ${response.status()}`);
    }
  });

  test("login → analyse → valuation → Buffett → provenance → export", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    await seedNonBlockingBrowserState(page);

    await page.addLocatorHandler(
      page.getByRole("dialog", { name: "Welcome tour" }),
      async (dialog) => {
        await dialog.getByRole("button", { name: "Skip tutorial" }).click();
      },
    );

    const stages: P109StageRecord[] = [];
    const capture = attachAnalyseCapture(page);

    await p109Stage("LOGIN", async () => {
      try {
        await loginWithUsernamePassword(page, ADMIN_ID, ADMIN_PASSWORD);
      } catch (error) {
        throw new Error(
          `P1-09 authentication failed for fixture user ${ADMIN_ID}: ${
            error instanceof Error ? error.message : String(error)
          }`,
        );
      }
      stages.push({ stage: "LOGIN", status: "passed" });
    });

    const { analysisId, payload } = await p109Stage("ANALYSIS", async () => {
      await openAnalysisWorkspace(page, TICKER);
      await acknowledgeDisclaimerIfPresent(page);
      const result = await waitForAnalyseSuccess(page, capture, TICKER);
      stages.push({ stage: "ANALYSIS", status: "passed" });
      return result;
    });

    await p109Stage("VALUATION", async () => {
      await assertValuationVisible(page, payload);
      stages.push({ stage: "VALUATION", status: "passed" });
    });

    await p109Stage("BUFFETT", async () => {
      await assertBuffettVisible(page, payload, TICKER);
      stages.push({ stage: "BUFFETT", status: "passed" });
    });

    const provenance = await p109Stage("PROVENANCE", async () => {
      await assertEvidenceVisible(page, analysisId);
      const record = await fetchProvenanceFromSession(
        page,
        API_BASE,
        analysisId,
        TICKER,
      );
      stages.push({ stage: "PROVENANCE", status: "passed" });
      return record;
    });

    await p109Stage("EXPORT", async () => {
      await exportJsonSnapshot(page, TICKER, analysisId);
      stages.push({ stage: "EXPORT", status: "passed" });
    });

    const release = provenance.release as Record<string, string>;
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
          stages,
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
