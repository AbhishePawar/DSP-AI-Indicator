import { NextResponse, type NextRequest } from "next/server";

import {
  CANONICAL_WWW_REDIRECT_STATUS,
  productionWwwRedirect,
} from "@/lib/canonicalWwwRedirect";

/**
 * EPIC-019A — CSP with per-request nonce.
 * Removes script-src 'unsafe-inline' / 'unsafe-eval' in production.
 * Dev retains 'unsafe-eval' for Next HMR (documented in CSP_REVIEW.md).
 *
 * Production www host is permanently redirected to the hardcoded apex origin
 * before auth pages run, so Google OAuth always uses
 * https://dspaiindicator.com/oauth/callback.
 */
export function middleware(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const isDev = process.env.NODE_ENV === "development";

  const scriptSrc = isDev
    ? `script-src 'self' 'nonce-${nonce}' 'strict-dynamic' 'unsafe-eval'`
    : `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`;

  // style-src 'unsafe-inline' retained — Next.js / CSS-in-JS / next-themes
  // require it without a full style-nonce migration (see CSP_REVIEW.md).
  const csp = [
    "default-src 'self'",
    scriptSrc,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    "connect-src 'self' http://127.0.0.1:8000 http://localhost:8000 https:",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");

  const wwwRedirect = productionWwwRedirect(
    request.headers,
    request.nextUrl.pathname,
    request.nextUrl.search,
    request.nextUrl.hostname,
  );
  if (wwwRedirect) {
    const response = NextResponse.redirect(
      wwwRedirect.location,
      CANONICAL_WWW_REDIRECT_STATUS,
    );
    response.headers.set("Content-Security-Policy", csp);
    response.headers.set("x-nonce", nonce);
    return response;
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });
  response.headers.set("Content-Security-Policy", csp);
  response.headers.set("x-nonce", nonce);
  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except static assets and images.
     */
    {
      source:
        "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
