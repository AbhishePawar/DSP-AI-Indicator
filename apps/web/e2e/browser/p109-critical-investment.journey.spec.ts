import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

import {
  API_BASE,
  EXPECTED_API_ORIGIN,
  P109_EXCHANGE,
  P109_TICKER,
  acknowledgeDisclaimerIfPresent,
  analysisWorkspaceUrl,
  attachNetworkForensics,
  isAnalysePost,
  isEnterpriseLogin,
  isProvenanceGet,
  logP109,
  redactValue,
  seedNonBlockingBrowserState,
  summarizeCriticalPath,
  unexpected5xxOnCriticalPath,
} from "./p109-harness";

/**
 * P1-09 — critical investment browser journey (Chromium).
 *
 * evidence_class = test_fixture — never real_live_authenticated_provider.
 *
 * Architecture: one API + one Next production server + one Chromium process.
 * Synchronization: Playwright waitForResponse around the single POST /analyse.
 *
 * Auto-run: CompanyAnalysisWorkspace POSTs /analyse when the URL includes
 * ticker + exchange and an authenticated token exists. That is the one
 * intentional submission. The test must not click Analyze again.
 */

const ADMIN_ID = process.env.DSP_P109_LOGIN ?? "admin";
const ADMIN_PASSWORD =
  process.env.DSP_SEED_ADMIN_PASSWORD ??
  process.env.DSP_P109_PASSWORD ??
  "Admin@123";

const EVIDENCE_CLASS = "test_fixture";

const STAGE = {
  AUTHENTICATION: 30_000,
  ANALYSIS_WORKSPACE: 30_000,
  ANALYSE_REQUEST: 30_000,
  DSP_RESULT: 20_000,
  PROVENANCE: 15_000,
  EXPORT: 15_000,
} as const;

test.describe.configure({ mode: "serial", retries: 0 });

test.describe("P1-09 critical investment journey", () => {
  test("API health ready before browser journey", async ({ request }) => {
    const root = API_BASE.replace(/\/api\/v1$/, "");
    expect((await request.get(`${root}/health/live`)).ok()).toBeTruthy();
    expect((await request.get(`${root}/health/ready`)).ok()).toBeTruthy();
  });

  test("login → analyse → valuation → Buffett → provenance → export", async ({
    page,
  }) => {
    test.setTimeout(90_000);
    await seedNonBlockingBrowserState(page);
    await page.addLocatorHandler(
      page.getByRole("dialog", { name: "Welcome tour" }),
      async (dialog) => {
        await dialog.getByRole("button", { name: "Skip tutorial" }).click();
      },
    );

    const forensic = attachNetworkForensics(page);
    let lastStep = "BOOT";

    const failStep = (step: string, extra: Record<string, unknown>) => {
      logP109(`STEP ${step} FAIL`);
      logP109(`last URL=${page.url()}`);
      for (const [key, value] of Object.entries(extra)) {
        logP109(
          `${key}=${typeof value === "string" ? value : JSON.stringify(redactValue(value))}`,
        );
      }
      logP109(`network\n${summarizeCriticalPath(forensic.records)}`);
      logP109(
        `browser console errors=${forensic.consoleErrors.length} page errors=${forensic.pageErrors.length}`,
      );
      for (const row of forensic.consoleErrors) {
        logP109(`console error=${row.text}`);
      }
      for (const err of forensic.pageErrors) {
        logP109(`page error=${err}`);
      }
    };

    const runStage = async <T>(name: string, fn: () => Promise<T>): Promise<T> => {
      lastStep = name;
      logP109(`STEP ${name} START`);
      try {
        const result = await fn();
        logP109(`STEP ${name} PASS`);
        return result;
      } catch (err) {
        failStep(name, {
          status: "exception",
          response: err instanceof Error ? err.message : String(err),
        });
        throw err;
      }
    };

    try {
      await runStage("AUTHENTICATION", async () => {
        await page.goto("/login", { waitUntil: "domcontentloaded" });
        await expect(
          page.getByRole("button", { name: /username and password/i }),
        ).toBeVisible({ timeout: STAGE.AUTHENTICATION });
        await page.getByRole("button", { name: /username and password/i }).click();
        await expect(page.locator("#login-username")).toBeVisible({
          timeout: 10_000,
        });
        await page.locator("#login-username").fill(ADMIN_ID);
        await page.locator("#login-password").fill(ADMIN_PASSWORD);

        const loginResponsePromise = page.waitForResponse(isEnterpriseLogin, {
          timeout: STAGE.AUTHENTICATION,
        });
        await page.getByRole("button", { name: /^sign in$/i }).click();
        const loginResponse = await loginResponsePromise;
        logP109(`POST /auth/enterprise/login status=${loginResponse.status()}`);
        expect(
          loginResponse.ok(),
          `login HTTP ${loginResponse.status()}`,
        ).toBeTruthy();

        await page.waitForURL(/\/(analysis|dashboard)/, {
          timeout: STAGE.AUTHENTICATION,
        });
        await expect(page.getByRole("button", { name: /sign in/i })).toHaveCount(
          0,
        );
        await expect(
          page.getByRole("button", { name: /Administrator|admin/i }).first(),
        ).toBeVisible({ timeout: 15_000 });

        const sessionProbe = await page.evaluate(async (apiBase: string) => {
          const res = await fetch(`${apiBase}/auth/session`, {
            method: "GET",
            credentials: "include",
            headers: { Accept: "application/json" },
          });
          let authenticated: boolean | null = null;
          try {
            const body = (await res.json()) as {
              payload?: { authenticated?: boolean };
              authenticated?: boolean;
            };
            authenticated = Boolean(
              body.payload?.authenticated ?? body.authenticated,
            );
          } catch {
            authenticated = null;
          }
          return { status: res.status, authenticated };
        }, API_BASE);
        logP109(
          `auth session probe status=${sessionProbe.status} authenticated=${String(sessionProbe.authenticated)}`,
        );
      });

      logP109("STEP ANALYSE_REQUEST START");
      const analyseResponsePromise = page.waitForResponse(isAnalysePost, {
        timeout: STAGE.ANALYSE_REQUEST,
      });

      await runStage("ANALYSIS_WORKSPACE", async () => {
        await page.goto(analysisWorkspaceUrl(), {
          waitUntil: "domcontentloaded",
        });
        await acknowledgeDisclaimerIfPresent(page);
        const main = page.getByRole("region", { name: "Main analysis area" });
        await expect(main).toBeVisible({ timeout: STAGE.ANALYSIS_WORKSPACE });
        await expect(page.getByLabel(/Company search/i)).toBeVisible();
        await expect(
          page.getByRole("button", { name: /^(Analyze|Run analysis)$/i }).first(),
        ).toBeVisible();
        logP109(
          "auto-run expected: URL includes ticker+exchange; no Analyze click",
        );
      });

      const { analysisId, analyseBody } = await runStage(
        "ANALYSE_REQUEST",
        async () => {
          const analyseResponse = await analyseResponsePromise;
          logP109(`POST /analyse status=${analyseResponse.status()}`);
          if (!analyseResponse.ok()) {
            let responseText = "";
            try {
              responseText = JSON.stringify(
                redactValue(await analyseResponse.json()),
              );
            } catch {
              responseText = "(unreadable body)";
            }
            failStep("ANALYSE_REQUEST", {
              status: analyseResponse.status(),
              response: responseText,
            });
          }
          expect(analyseResponse.ok()).toBeTruthy();
          expect(new URL(analyseResponse.url()).origin).toBe(EXPECTED_API_ORIGIN);

          const posted = analyseResponse.request().postDataJSON() as Record<
            string,
            unknown
          > | null;
          expect(posted, "POST /analyse must have a JSON body").toBeTruthy();
          expect(String(posted!.ticker || "").toUpperCase()).toBe(P109_TICKER);
          expect(String(posted!.exchange || "").toUpperCase()).toBe(
            P109_EXCHANGE,
          );
          const signals = (posted!.valuation_signals ?? {}) as Record<
            string,
            unknown
          >;
          expect(signals.intrinsic_value_per_share).toBeUndefined();
          expect(signals.margin_of_safety).toBeUndefined();
          expect(posted!.current_market_price).toBeUndefined();

          const analyseBody = (await analyseResponse.json()) as Record<
            string,
            unknown
          >;
        expect(analyseBody.ok).toBe(true);
        expect(analyseBody.analysis_id).toBeTruthy();
        const analysisId = String(analyseBody.analysis_id);
        const payload = (analyseBody.payload ?? {}) as Record<string, unknown>;
        const source = (payload.source_evidence ?? {}) as Record<string, unknown>;
        const quoteProv = (source.quote_provenance ?? {}) as Record<string, unknown>;
        const quoteMeta = (quoteProv.metadata ?? {}) as Record<string, unknown>;
        const evidenceClass =
          source.evidence_class ?? quoteMeta.evidence_class ?? null;
        expect(evidenceClass).toBe(EVIDENCE_CLASS);
        expect(source.g2_claim).not.toBe(true);
        logP109(`analysis_id=${analysisId}`);
        logP109(`evidence_class=${String(source.evidence_class)} g2_claim=${String(source.g2_claim)}`);
        return { analysisId, analyseBody };
        },
      );

      await runStage("DSP_RESULT", async () => {
        const payload = (analyseBody.payload ?? {}) as Record<string, unknown>;
        const buffett = (payload.buffett_authority ?? {}) as Record<
          string,
          unknown
        >;
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
          page
            .getByRole("heading", { name: /Executive Summary|Summary/i })
            .first(),
        ).toBeVisible({ timeout: STAGE.DSP_RESULT });
      });

      const release = await runStage("PROVENANCE", async () => {
        const nav = page.getByRole("navigation", { name: "Analysis sections" });
        await expect(nav).toBeVisible();
        const provenancePromise = page.waitForResponse(
          (response) => isProvenanceGet(response, analysisId),
          { timeout: STAGE.PROVENANCE },
        );
        await nav.getByRole("button", { name: /Research Object/i }).click();
        const provenanceResponse = await provenancePromise;
        logP109(
          `GET provenance status=${provenanceResponse.status()} path=${new URL(provenanceResponse.url()).pathname}`,
        );
        expect(
          provenanceResponse.ok(),
          `provenance HTTP ${provenanceResponse.status()}`,
        ).toBeTruthy();
        const provEnvelope = (await provenanceResponse.json()) as {
          provenance?: Record<string, unknown>;
        };
        const prov = provEnvelope.provenance;
        expect(prov, "provenance payload missing").toBeTruthy();
        expect(prov!.analysis_id).toBe(analysisId);
        expect(prov!.ticker).toBe(P109_TICKER);
        const release = prov!.release as Record<string, string>;
        expect(release.epic).toBe("EPS-003");
        expect(release.product_version).toBe("2.0.0-rc.1");
        expect(release.channel).toBe("rc");
        expect(release.decision).toBe("RELEASE_CANDIDATE");
        expect(prov!.input_fingerprint).toBeTruthy();
        expect(prov!.result_fingerprint).toBeTruthy();
        const buffettBtn = nav.getByRole("button", { name: /Buffett/i });
        if (await buffettBtn.isVisible().catch(() => false)) {
          await buffettBtn.click();
        }
        return release;
      });

      await runStage("EXPORT", async () => {
        const nav = page.getByRole("navigation", { name: "Analysis sections" });
        await nav.getByRole("button", { name: /Downloads/i }).click();
        const exportJson = page.getByRole("button", { name: /Export JSON/i });
        await expect(exportJson).toBeVisible({ timeout: STAGE.EXPORT });
        const downloadPromise = page.waitForEvent("download", {
          timeout: STAGE.EXPORT,
        });
        await exportJson.click();
        const download = await downloadPromise;
        const downloadPath = await download.path();
        expect(downloadPath).toBeTruthy();
        const exported = JSON.parse(fs.readFileSync(downloadPath!, "utf-8")) as {
          ticker?: string;
          analysisId?: string | null;
          auditReference?: string | null;
        };
        expect(exported.ticker?.toUpperCase()).toBe(P109_TICKER);
        expect(exported.analysisId || exported.auditReference).toBe(analysisId);
      });

      const expectedAnalyse = 1;
      const actualAnalyse = forensic.analyseRequests.length;
      logP109(
        `/analyse requests: expected=${expectedAnalyse} actual=${actualAnalyse}`,
      );
      logP109("intentional_analysis_submissions=1");
      logP109(
        `unexpected_analysis_submissions=${Math.max(0, actualAnalyse - expectedAnalyse)}`,
      );
      expect(actualAnalyse, "exactly one POST /analyse").toBe(1);

      const unexpected5xx = unexpected5xxOnCriticalPath(forensic.records);
      logP109(`unexpected 5xx=${unexpected5xx.length}`);
      expect(unexpected5xx, JSON.stringify(unexpected5xx)).toEqual([]);
      logP109(`browser console errors=${forensic.consoleErrors.length}`);
      logP109(`page errors=${forensic.pageErrors.length}`);

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
            ticker: P109_TICKER,
            exchange: P109_EXCHANGE,
            analysis_id: analysisId,
            release_identity: release,
            intentional_analysis_submissions: 1,
            unexpected_analysis_submissions: 0,
            analyse_request_count: actualAnalyse,
            api_origin: EXPECTED_API_ORIGIN,
            browser: "chromium",
            retries: 0,
          },
          null,
          2,
        )}\n`,
        "utf-8",
      );
    } catch (err) {
      logP109(`failed after ${lastStep}`);
      throw err;
    }
  });

  test("unauthenticated analyse path does not invent values for missing symbol", async ({
    page,
  }) => {
    await seedNonBlockingBrowserState(page);
    await page.goto("/analysis?symbol=ZZZZNOPE", {
      waitUntil: "domcontentloaded",
    });
    await expect(
      page.getByRole("region", { name: "Main analysis area" }),
    ).toBeVisible({ timeout: 20_000 });
    const bodyText = await page.locator("body").innerText();
    expect(bodyText.toLowerCase()).not.toMatch(
      /intrinsic value:\s*\$?\s*[1-9]/i,
    );
    expect(bodyText.toLowerCase()).not.toMatch(/margin of safety:\s*[+-]?\d/i);
  });
});
