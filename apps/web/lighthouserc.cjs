/**
 * EPIC-010 / GA-003 — Lighthouse CI configuration (production-ready).
 *
 * Run against a local production server:
 *   npm run build
 *   npm run start          # default :3000
 *   npm run lighthouse:ci  # requires Chrome / Chromium
 *
 * Scores below are **advisory baselines** aligned with RC3 PASS WITH CONDITIONS —
 * they establish automation, not an unrestricted Commercial GA unlock.
 *
 * Categories tracked: Performance, Accessibility, Best Practices, SEO.
 */

module.exports = {
  ci: {
    collect: {
      url: [
        "http://127.0.0.1:3000/",
        "http://127.0.0.1:3000/login",
        "http://127.0.0.1:3000/dashboard",
        "http://127.0.0.1:3000/settings",
      ],
      numberOfRuns: 1,
      settings: {
        preset: "desktop",
        // Form-factor mobile can be re-run manually; desktop is the CI baseline.
        formFactor: "desktop",
        screenEmulation: { disabled: true },
        // Thin-client app; block third-party noise when absent.
        skipAudits: ["uses-http2"],
      },
    },
    assert: {
      // Assert as warn so CI can run without blocking on env/host variance;
      // Commercial GA still requires honest human review of scores.
      assertMatrix: [
        {
          matchingUrlPattern: ".*",
          assertions: {
            "categories:performance": ["warn", { minScore: 0.7 }],
            "categories:accessibility": ["warn", { minScore: 0.9 }],
            "categories:best-practices": ["warn", { minScore: 0.85 }],
            "categories:seo": ["warn", { minScore: 0.8 }],
            "largest-contentful-paint": ["warn", { maxNumericValue: 4000 }],
            "cumulative-layout-shift": ["warn", { maxNumericValue: 0.15 }],
            "interaction-to-next-paint": ["warn", { maxNumericValue: 300 }],
          },
        },
      ],
    },
    upload: {
      target: "temporary-public-storage",
    },
  },
};
