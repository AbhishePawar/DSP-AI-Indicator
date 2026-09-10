/**
 * P1-09 Chromium harness helpers — diagnostics only, no secrets.
 */

import type { Page, Request, Response } from "@playwright/test";

export const P109_TICKER = process.env.DSP_P109_TICKER ?? "DSPFIX";
export const P109_EXCHANGE = process.env.DSP_P109_EXCHANGE ?? "NYSE";
export const API_BASE =
  process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
export const EXPECTED_API_ORIGIN = new URL(API_BASE).origin;

const SECRET_HEADER = /^(cookie|authorization|x-csrf-token|set-cookie)$/i;
const SECRET_BODY_KEY =
  /password|passwd|secret|token|csrf|cookie|authorization|bearer|api[_-]?key/i;

export type NetworkRecord = {
  method: string;
  pathname: string;
  status: number | null;
  durationMs: number | null;
  failed: boolean;
  aborted: boolean;
};

export type ConsoleRecord = {
  type: string;
  text: string;
};

function safePathname(url: string): string {
  try {
    return new URL(url).pathname;
  } catch {
    return url.split("?")[0] ?? url;
  }
}

export function isAnalysePost(response: Response): boolean {
  if (response.request().method() !== "POST") return false;
  const pathname = safePathname(response.url());
  return pathname === "/analyse" || pathname === "/api/v1/analyse";
}

export function isAnalysePostRequest(request: Request): boolean {
  if (request.method() !== "POST") return false;
  const pathname = safePathname(request.url());
  return pathname === "/analyse" || pathname === "/api/v1/analyse";
}

export function isEnterpriseLogin(response: Response): boolean {
  if (response.request().method() !== "POST") return false;
  const pathname = safePathname(response.url());
  return pathname.endsWith("/auth/enterprise/login");
}

export function isProvenanceGet(response: Response, analysisId: string): boolean {
  if (response.request().method() !== "GET") return false;
  const pathname = safePathname(response.url());
  return (
    pathname === `/api/v1/analyse/provenance/${analysisId}` ||
    pathname === `/analyse/provenance/${analysisId}`
  );
}

export function redactValue(value: unknown): unknown {
  if (value == null) return value;
  if (typeof value === "string") {
    if (value.length > 240) return `${value.slice(0, 120)}…`;
    return value;
  }
  if (Array.isArray(value)) {
    return value.slice(0, 20).map(redactValue);
  }
  if (typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [key, nested] of Object.entries(value as Record<string, unknown>)) {
      out[key] = SECRET_BODY_KEY.test(key) ? "[redacted]" : redactValue(nested);
    }
    return out;
  }
  return value;
}

export function logP109(message: string): void {
  // eslint-disable-next-line no-console -- CI forensic breadcrumb
  console.log(`[P109] ${message}`);
}

export function attachNetworkForensics(page: Page): {
  records: NetworkRecord[];
  consoleErrors: ConsoleRecord[];
  pageErrors: string[];
  analyseRequests: Request[];
  provenanceResponses: Response[];
} {
  const records: NetworkRecord[] = [];
  const consoleErrors: ConsoleRecord[] = [];
  const pageErrors: string[] = [];
  const analyseRequests: Request[] = [];
  const provenanceResponses: Response[] = [];
  const startedAt = new WeakMap<Request, number>();

  page.on("request", (request) => {
    startedAt.set(request, Date.now());
    if (isAnalysePostRequest(request)) {
      analyseRequests.push(request);
    }
  });

  page.on("response", (response) => {
    const request = response.request();
    const started = startedAt.get(request);
    records.push({
      method: request.method(),
      pathname: safePathname(response.url()),
      status: response.status(),
      durationMs: started ? Date.now() - started : null,
      failed: response.status() >= 500,
      aborted: false,
    });
    if (
      request.method() === "GET" &&
      safePathname(response.url()).includes("/analyse/provenance/")
    ) {
      provenanceResponses.push(response);
    }
  });

  page.on("requestfailed", (request) => {
    const started = startedAt.get(request);
    const failure = request.failure()?.errorText ?? "failed";
    records.push({
      method: request.method(),
      pathname: safePathname(request.url()),
      status: null,
      durationMs: started ? Date.now() - started : null,
      failed: true,
      aborted: /abort|cancel/i.test(failure),
    });
  });

  page.on("console", (msg) => {
    if (msg.type() === "error") {
      consoleErrors.push({ type: msg.type(), text: sanitizeLogText(msg.text()) });
    }
  });

  page.on("pageerror", (error) => {
    pageErrors.push(sanitizeLogText(error.message));
  });

  return { records, consoleErrors, pageErrors, analyseRequests, provenanceResponses };
}

export function sanitizeLogText(text: string): string {
  return text
    .replace(/Bearer\s+\S+/gi, "Bearer [redacted]")
    .replace(/csrf[^,\s]*/gi, "[redacted-csrf]")
    .slice(0, 400);
}

export function summarizeCriticalPath(records: NetworkRecord[]): string {
  const interesting = records.filter((row) => {
    const p = row.pathname;
    return (
      p.includes("/auth/") ||
      p.endsWith("/analyse") ||
      p.includes("/analyse/provenance") ||
      p.includes("/auth/session") ||
      p.includes("/market/quote") ||
      p.includes("/fundamentals/statements")
    );
  });
  return interesting
    .map((row) => {
      const status = row.status ?? (row.aborted ? "aborted" : "failed");
      const dur = row.durationMs == null ? "?" : `${row.durationMs}ms`;
      return `${row.method} ${row.pathname} status=${status} duration=${dur}`;
    })
    .join("\n");
}

export function unexpected5xxOnCriticalPath(records: NetworkRecord[]): NetworkRecord[] {
  return records.filter((row) => {
    if (row.status == null || row.status < 500) return false;
    const p = row.pathname;
    return (
      p.includes("/auth/") ||
      p.endsWith("/analyse") ||
      p.includes("/analyse/provenance") ||
      p.includes("/market/quote") ||
      p.includes("/fundamentals/statements")
    );
  });
}

export function dumpHeadersSafe(headers: Record<string, string>): string {
  const keys = Object.keys(headers).filter((key) => !SECRET_HEADER.test(key));
  return keys.sort().join(",");
}

export async function seedNonBlockingBrowserState(page: Page): Promise<void> {
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

export async function acknowledgeDisclaimerIfPresent(page: Page): Promise<void> {
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
}

export function analysisWorkspaceUrl(ticker = P109_TICKER, exchange = P109_EXCHANGE): string {
  return `/analysis?symbol=${encodeURIComponent(ticker)}&exchange=${encodeURIComponent(exchange)}`;
}
