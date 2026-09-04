import { expect, type Page } from "@playwright/test";
import fs from "node:fs";

/**
 * Company Analysis Workspace contracts (WorkspaceLeftNav + ANALYSIS_SECTIONS):
 *   nav "Analysis sections"
 *   region "Main analysis area"
 *   search aria-label "Company search"
 *   Analyze button
 *   section buttons include shortcut kbd, so names are "Valuation 2", "Buffett Indicator B", …
 *
 * Match the intended label; allow a trailing shortcut character.
 */

export function analysisNav(page: Page) {
  return page.getByRole("navigation", { name: "Analysis sections" });
}

export function analysisMain(page: Page) {
  return page.getByRole("region", { name: "Main analysis area" });
}

export async function openAnalysisWorkspace(
  page: Page,
  ticker: string,
): Promise<void> {
  await page.goto(`/analysis?symbol=${encodeURIComponent(ticker)}`, {
    waitUntil: "domcontentloaded",
  });
  await expect(analysisNav(page)).toBeVisible({ timeout: 30_000 });
  await expect(analysisMain(page)).toBeVisible();
  await expect(page.getByLabel(/Company search/i)).toBeVisible();
}

/** Section buttons concatenate label + shortcut; match label, not incidental order. */
export async function openAnalysisSection(
  page: Page,
  label: RegExp,
  heading: string | RegExp,
): Promise<void> {
  const button = analysisNav(page).getByRole("button", { name: label });
  await expect(
    button,
    `[P1-09] section control ${label} must exist`,
  ).toBeVisible();
  await button.click();
  await expect(analysisMain(page)).toBeVisible();
  await expect(
    page.getByRole("heading", { name: heading }).first(),
    `[P1-09] section heading ${String(heading)} must render`,
  ).toBeVisible({ timeout: 20_000 });
}

export type AnalyseCapture = {
  status: number | null;
  body: Record<string, unknown> | null;
};

export function attachAnalyseCapture(page: Page): AnalyseCapture {
  const capture: AnalyseCapture = { status: null, body: null };
  page.on("response", async (response) => {
    try {
      const url = response.url();
      if (
        response.request().method() === "POST" &&
        /\/analyse(\?|$)/.test(url) &&
        !url.includes("provenance")
      ) {
        capture.status = response.status();
        if (response.ok()) {
          capture.body = (await response.json()) as Record<string, unknown>;
        }
      }
    } catch {
      /* ignore parse races */
    }
  });
  return capture;
}

export async function waitForAnalyseSuccess(
  page: Page,
  capture: AnalyseCapture,
  ticker: string,
): Promise<{ analysisId: string; payload: Record<string, unknown> }> {
  const ready = () =>
    Boolean(capture.body?.ok === true && capture.body?.analysis_id);

  if (!ready()) {
    await page.getByRole("button", { name: /^Analyze/i }).first().click();
  }

  await expect
    .poll(
      async () => ready(),
      {
        timeout: 90_000,
        message: `[P1-09 ANALYSIS] POST /analyse must succeed with analysis_id (last status=${capture.status})`,
      },
    )
    .toBeTruthy();

  let stableId = "";
  let stableHits = 0;
  await expect
    .poll(
      async () => {
        const id = String(capture.body?.analysis_id || "");
        if (id && id === stableId) stableHits += 1;
        else {
          stableId = id;
          stableHits = 0;
        }
        return Boolean(id) && stableHits >= 4;
      },
      {
        timeout: 30_000,
        intervals: [250, 250, 250, 250],
        message: "[P1-09 ANALYSIS] analysis_id must stabilize",
      },
    )
    .toBeTruthy();

  const analysisId = String(capture.body!.analysis_id);
  const payload = (capture.body!.payload ?? {}) as Record<string, unknown>;
  const bodyTicker = String(
    (capture.body as { ticker?: string })?.ticker || payload.ticker || "",
  ).toUpperCase();
  if (bodyTicker) {
    expect(
      bodyTicker,
      "[P1-09 ANALYSIS] analyse payload ticker must match fixture",
    ).toBe(ticker.toUpperCase());
  }

  await expect(
    page.getByRole("heading", { name: /Executive Summary|Summary/i }).first(),
    "[P1-09 ANALYSIS] executive summary must be visible",
  ).toBeVisible({ timeout: 30_000 });

  const mainText = await analysisMain(page).innerText();
  expect(
    mainText.toUpperCase(),
    "[P1-09 ANALYSIS] workspace must show the fixture ticker",
  ).toContain(ticker.toUpperCase());

  return { analysisId, payload };
}

export async function assertValuationVisible(
  page: Page,
  payload: Record<string, unknown>,
): Promise<void> {
  await openAnalysisSection(page, /^Valuation(\s+\d|\d)?$/i, /^Valuation$/i);
  await expect(page.getByText("Intrinsic Value", { exact: true })).toBeVisible();
  await expect(page.getByText("Current Price", { exact: true })).toBeVisible();
  await expect(page.getByText("Margin of Safety", { exact: true })).toBeVisible();

  const stages = (payload.stage_summaries ?? []) as Array<
    Record<string, unknown>
  >;
  const valuation = stages.find((s) => s.stage === "valuation");
  expect(valuation, "[P1-09 VALUATION] valuation stage must exist").toBeTruthy();
  expect(["succeeded", "degraded", "unavailable"]).toContain(
    String(valuation!.status),
  );
  await expect(page.getByText("Stage status", { exact: true })).toBeVisible();
}

export async function assertBuffettVisible(
  page: Page,
  payload: Record<string, unknown>,
  ticker: string,
): Promise<void> {
  await openAnalysisSection(
    page,
    /Buffett Indicator/i,
    /Buffett Indicator Analysis/i,
  );
  const buffettMain = analysisMain(page);
  await expect(
    buffettMain.getByText(/Presentation synthesis of existing/i),
  ).toBeVisible();
  // Scorecard repeats the same dt labels; the section contract is the
  // heading + at least one rating/action row, not uniqueness of the dt.
  await expect(
    buffettMain.getByText("Overall Buffett Rating", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    buffettMain.getByText("Buffett Action", { exact: true }).first(),
  ).toBeVisible();

  const buffett = (payload.buffett_authority ?? {}) as Record<string, unknown>;
  expect(
    Object.keys(buffett).length,
    "[P1-09 BUFFETT] analyse payload must include Buffett outputs",
  ).toBeGreaterThan(0);

  const mainText = await analysisMain(page).innerText();
  expect(mainText.toUpperCase()).toContain(ticker.toUpperCase());
}

export async function assertEvidenceVisible(
  page: Page,
  analysisId: string,
): Promise<void> {
  await openAnalysisSection(
    page,
    /Supporting Evidence/i,
    /Research objects/i,
  );
  await expect(page.getByText("Analysis ID", { exact: true })).toBeVisible();
  await expect(analysisMain(page)).toContainText(analysisId);
}

export async function fetchProvenanceFromSession(
  page: Page,
  apiBase: string,
  analysisId: string,
  ticker: string,
): Promise<Record<string, unknown>> {
  const provFetch = await page.evaluate(
    async ({ apiBase: base, id }) => {
      const csrf =
        window.sessionStorage.getItem("dsp.auth.csrf.v1") ||
        window.localStorage.getItem("dsp.auth.csrf.v1");
      let bearer: string | null = null;
      for (const store of [window.sessionStorage, window.localStorage]) {
        try {
          const raw = store.getItem("dsp.auth.session.v3");
          if (!raw) continue;
          const parsed = JSON.parse(raw) as { accessToken?: string };
          if (parsed.accessToken && !parsed.accessToken.startsWith("cookie:")) {
            bearer = parsed.accessToken;
            break;
          }
        } catch {
          /* ignore */
        }
      }
      const headers: Record<string, string> = { Accept: "application/json" };
      if (csrf) headers["X-CSRF-Token"] = csrf;
      if (bearer) headers.Authorization = `Bearer ${bearer}`;
      const res = await fetch(`${base}/analyse/provenance/${id}`, {
        credentials: "include",
        headers,
      });
      const body = await res.json();
      return { ok: res.ok, status: res.status, body };
    },
    { apiBase, id: analysisId },
  );
  expect(
    provFetch.ok,
    `[P1-09 PROVENANCE] HTTP ${provFetch.status}`,
  ).toBeTruthy();
  const provenance = (provFetch.body as { provenance: Record<string, unknown> })
    .provenance;
  expect(provenance.analysis_id).toBe(analysisId);
  expect(String(provenance.ticker).toUpperCase()).toBe(ticker.toUpperCase());
  const release = provenance.release as Record<string, string>;
  expect(release.epic).toBe("EPS-003");
  expect(release.product_version).toBe("2.0.0-rc.1");
  expect(release.channel).toBe("rc");
  expect(release.decision).toBe("RELEASE_CANDIDATE");
  expect(provenance.input_fingerprint).toBeTruthy();
  expect(provenance.result_fingerprint).toBeTruthy();
  return provenance;
}

export async function exportJsonSnapshot(
  page: Page,
  ticker: string,
  analysisId: string,
): Promise<Record<string, unknown>> {
  await openAnalysisSection(page, /Downloads/i, /^Downloads$/i);
  const exportJson = page.getByRole("button", { name: /Export JSON/i });
  await expect(exportJson).toBeVisible({ timeout: 15_000 });
  const downloadPromise = page.waitForEvent("download", { timeout: 30_000 });
  await exportJson.click();
  const download = await downloadPromise;
  const downloadPath = await download.path();
  expect(downloadPath, "[P1-09 EXPORT] download path must exist").toBeTruthy();
  const exported = JSON.parse(fs.readFileSync(downloadPath!, "utf-8")) as {
    ticker?: string;
    analysisId?: string | null;
    auditReference?: string | null;
  };
  expect(exported.ticker?.toUpperCase()).toBe(ticker.toUpperCase());
  expect(exported.analysisId || exported.auditReference).toBe(analysisId);
  return exported as Record<string, unknown>;
}
