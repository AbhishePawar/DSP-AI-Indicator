import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";
import bundleAnalyzer from "@next/bundle-analyzer";

const appRoot = path.dirname(fileURLToPath(import.meta.url));

/**
 * Web 2.0.0-rc.1 — security headers (EPS-003 / EPIC-019A).
 * CSP is issued per-request from src/middleware.ts (nonce; no static
 * script-src 'unsafe-inline'/'unsafe-eval' in production). See CSP_REVIEW.md.
 *
 * EPIC-010 / GA-003 — set ANALYZE=true to emit webpack-bundle-analyzer reports
 * (npm run analyze). Quality tooling only; no product behaviour change.
 */
const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,
  productionBrowserSourceMaps: false,
  output: "standalone",
  // The v0 preview iframe serves the app from a separate origin during development.
  allowedDevOrigins: ["identify-gaps-list.v0.build"],
  // Keep preview and production resolution rooted at this app instead of
  // inferring a parent monorepo root from unrelated lockfiles.
  turbopack: {
    root: appRoot,
  },
  // Pin tracing to this app. A leftover empty repo-root package-lock.json
  // otherwise makes Next infer the workspace root as the repository root,
  // emitting .next/standalone/apps/web/server.js instead of
  // .next/standalone/server.js (the path Playwright and the frontend
  // Dockerfile both use).
  outputFileTracingRoot: appRoot,
  // P7.3 — tree-shake heavy UI kits without changing product behaviour
  async rewrites() {
    const publicUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || "").trim().replace(/\/$/, "");
    const backendEnv = (process.env.BACKEND || "").trim().replace(/\/$/, "");
    const absolute = [backendEnv, publicUrl].find((value) => /^https?:\/\//i.test(value));
    // Browser calls same-origin /api/v1. An absolute BACKEND (preferred) or an
    // absolute NEXT_PUBLIC_API_BASE_URL is the proxy target. Relative
    // NEXT_PUBLIC_API_BASE_URL=/api/v1 does not itself prove a proxy exists.
    // Local dev proxies to the API on port 8000. Production does not invent
    // a localhost target when no absolute backend is configured.
    if (absolute) {
      return [{ source: "/api/v1/:path*", destination: `${absolute}/:path*` }];
    }
    if (process.env.NODE_ENV === "production") return [];
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://127.0.0.1:8000/api/v1/:path*",
      },
    ];
  },
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  headers: async () => [
    {
      source: "/_next/static/:path*",
      headers: [
        {
          key: "Cache-Control",
          value: "public, max-age=31536000, immutable",
        },
      ],
    },
    {
      source: "/:path*",
      headers: [
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        {
          key: "Permissions-Policy",
          value: "camera=(), microphone=(), geolocation=()",
        },
        // Edge (Caddy) is primary HSTS; app-level header for direct access / defense in depth (P7.0).
        {
          key: "Strict-Transport-Security",
          value: "max-age=31536000; includeSubDomains",
        },
      ],
    },
  ],
};

export default withBundleAnalyzer(nextConfig);
