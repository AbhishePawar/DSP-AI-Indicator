import type { NextConfig } from "next";
import bundleAnalyzer from "@next/bundle-analyzer";

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
  // P7.3 — tree-shake heavy UI kits without changing product behaviour
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
