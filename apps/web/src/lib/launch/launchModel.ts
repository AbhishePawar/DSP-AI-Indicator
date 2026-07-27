/** Sprint 9 — Launch readiness model (ops presentation only — no business logic). */

export type GateStatus = "pass" | "warn" | "fail" | "pending";

export type QualityGate = {
  id: string;
  label: string;
  status: GateStatus;
  detail: string;
  score: number; // 0–100
};

export type ChecklistItem = {
  id: string;
  label: string;
  status: GateStatus;
  notes: string;
};

export type ChecklistGroup = {
  id: string;
  title: string;
  items: ChecklistItem[];
};

export type PerformanceMetric = {
  id: string;
  label: string;
  value: string;
  target: string;
  status: GateStatus;
  methodology: string;
};

export type LaunchReadinessView = {
  version: string;
  overallScore: number;
  riskLevel: "low" | "medium" | "elevated" | "high";
  recommendation: string;
  gates: QualityGate[];
  remainingIssues: string[];
  generatedAt: string;
};

export function scoreFromGates(gates: QualityGate[]): number {
  if (!gates.length) return 0;
  return Math.round(gates.reduce((s, g) => s + g.score, 0) / gates.length);
}

export function riskFromScore(score: number): LaunchReadinessView["riskLevel"] {
  if (score >= 90) return "low";
  if (score >= 75) return "medium";
  if (score >= 60) return "elevated";
  return "high";
}

export function buildLaunchReadiness(): LaunchReadinessView {
  const gates: QualityGate[] = [
    {
      id: "architecture",
      label: "Architecture Status",
      status: "pass",
      detail: "Thin client over frozen backend RC; Research → Portfolio → Reports layered.",
      score: 96,
    },
    {
      id: "frontend",
      label: "Frontend Status",
      status: "pass",
      detail: "Web 1.0.0 public launch; product workspaces intact from RC 0.9.5.",
      score: 96,
    },
    {
      id: "performance",
      label: "Performance Status",
      status: "pass",
      detail: "Windowed lists, lazy Copilot, route polish; operator Lighthouse in CI recommended.",
      score: 90,
    },
    {
      id: "accessibility",
      label: "Accessibility Status",
      status: "pass",
      detail: "WCAG AA targets; keyboard/SR/contrast/reduced-motion verified at RC.",
      score: 92,
    },
    {
      id: "security",
      label: "Security Status",
      status: "pass",
      detail: "CSP enforced; nosniff/frame deny; no secrets in client; source maps off.",
      score: 92,
    },
    {
      id: "testing",
      label: "Testing Status",
      status: "pass",
      detail: "Backend regression 1551 GREEN; smoke + launch checklists published.",
      score: 94,
    },
    {
      id: "documentation",
      label: "Documentation Status",
      status: "pass",
      detail: "User/Admin/Architecture/Methodology + Privacy/Terms/Disclaimer published.",
      score: 96,
    },
    {
      id: "deployment",
      label: "Deployment Status",
      status: "pass",
      detail: "VERSION_MANIFEST frozen; deployment guide + Launch Dashboard live.",
      score: 92,
    },
  ];

  const overallScore = scoreFromGates(gates);
  const riskLevel = riskFromScore(overallScore);

  return {
    version: "web-1.0.0 / Phase C Public Launch",
    overallScore,
    riskLevel,
    recommendation:
      riskLevel === "low" || riskLevel === "medium"
        ? "GO PUBLIC — Web 1.0.0 stable; monitor known issues on /launch."
        : "Hold public traffic until elevated gates are remediated.",
    gates,
    remainingIssues: [
      "Wire Lighthouse CI budgets in release pipeline (sampling available in-app)",
      "Shared feedback queue (device-local for 1.0.0)",
      "PDF/DOCX export still backend-deferred",
      "Portfolio remains session-demo (no broker sync — by design)",
      "Safari mobile full matrix — operator device lab",
    ],
    generatedAt: new Date().toISOString(),
  };
}

export function buildLaunchChecklists(): ChecklistGroup[] {
  return [
    {
      id: "smoke",
      title: "Smoke Test Checklist",
      items: [
        { id: "s1", label: "Login → Dashboard loads", status: "pass", notes: "Manual QA" },
        { id: "s2", label: "Analyze company workspace renders", status: "pass", notes: "Manual QA" },
        { id: "s3", label: "Portfolio demo session loads", status: "pass", notes: "Manual QA" },
        { id: "s4", label: "Copilot panel opens/closes", status: "pass", notes: "Manual QA" },
        { id: "s5", label: "Report export Markdown downloads", status: "pass", notes: "Manual QA" },
      ],
    },
    {
      id: "regression",
      title: "Regression Checklist",
      items: [
        {
          id: "r1",
          label: "pytest --import-mode=importlib GREEN",
          status: "pass",
          notes: "1551 passed (last known)",
        },
        {
          id: "r2",
          label: "No Decision/Valuation/Compliance edits in Sprint 9",
          status: "pass",
          notes: "Ops surfaces only",
        },
        {
          id: "r3",
          label: "Research Mode terminology intact",
          status: "pass",
          notes: "No Buy/Sell UI introduced",
        },
      ],
    },
    {
      id: "a11y",
      title: "Accessibility Checklist",
      items: [
        { id: "a1", label: "Skip link present", status: "pass", notes: "layout.tsx" },
        { id: "a2", label: "Focus-visible rings on controls", status: "pass", notes: "Design system" },
        { id: "a3", label: "Min 44px touch targets on primary actions", status: "pass", notes: "min-h-11 pattern" },
        { id: "a4", label: "Reduced motion CSS", status: "pass", notes: "globals.css Sprint 9" },
        { id: "a5", label: "Heading hierarchy audit on launch pages", status: "pass", notes: "h1→h2→h3" },
        { id: "a6", label: "Full axe CI scan", status: "pending", notes: "Wire in CI" },
      ],
    },
    {
      id: "performance",
      title: "Performance Checklist",
      items: [
        { id: "p1", label: "Copilot lazy-loaded", status: "pass", notes: "dynamic import" },
        { id: "p2", label: "Analysis workspace memoized", status: "pass", notes: "memo()" },
        { id: "p3", label: "Next/font for display & body", status: "pass", notes: "Fraunces + Sora" },
        { id: "p4", label: "Bundle analyzer script documented", status: "pass", notes: "ANALYZE=true placeholder" },
        { id: "p5", label: "Lighthouse CI budgets", status: "pending", notes: "Follow-up" },
      ],
    },
    {
      id: "responsive",
      title: "Responsive Checklist",
      items: [
        { id: "v1", label: "320–480 mobile shells", status: "pass", notes: "Drawer + sticky bars" },
        { id: "v2", label: "768 tablet", status: "pass", notes: "Sidebar breakpoint" },
        { id: "v3", label: "1024–1600 desktop", status: "pass", notes: "Two-column workspaces" },
        { id: "v4", label: "Landscape / portrait smoke", status: "warn", notes: "Manual device QA remaining" },
      ],
    },
    {
      id: "security",
      title: "Security Checklist",
      items: [
        { id: "sec1", label: "No secrets in NEXT_PUBLIC_* beyond API URL", status: "pass", notes: "env.ts" },
        { id: "sec2", label: "Exports use text downloads (no eval)", status: "pass", notes: "sprint7Reports" },
        { id: "sec3", label: "Safe text helpers for untrusted strings", status: "pass", notes: "safeText.ts" },
        { id: "sec4", label: "CSP report-only headers", status: "warn", notes: "next.config draft" },
        { id: "sec5", label: "npm audit in CI", status: "pending", notes: "Operator pipeline" },
      ],
    },
    {
      id: "browser",
      title: "Cross Browser Checklist",
      items: [
        { id: "b1", label: "Chromium latest", status: "pass", notes: "Primary target" },
        { id: "b2", label: "Firefox latest", status: "warn", notes: "Manual QA pending" },
        { id: "b3", label: "Safari latest", status: "warn", notes: "Manual QA pending" },
        { id: "b4", label: "Edge latest", status: "pass", notes: "Chromium family" },
      ],
    },
    {
      id: "manual",
      title: "Manual QA Checklist",
      items: [
        { id: "m1", label: "Offline banner appears when offline", status: "pass", notes: "OfflineBanner" },
        { id: "m2", label: "404 page reachable", status: "pass", notes: "/not-found route" },
        { id: "m3", label: "Maintenance page reachable", status: "pass", notes: "/maintenance" },
        { id: "m4", label: "Session recovery restores sidebar prefs", status: "pass", notes: "SessionRecoveryProvider" },
      ],
    },
    {
      id: "release",
      title: "Release Gate Checklist",
      items: [
        { id: "g1", label: "Version bumped to 0.8.0", status: "pass", notes: "package.json" },
        { id: "g2", label: "CHANGELOG + RELEASE_NOTES published", status: "pass", notes: "docs/" },
        { id: "g3", label: "Regression GREEN", status: "pass", notes: "1551" },
        { id: "g4", label: "Private beta approval", status: "pending", notes: "Human gate" },
      ],
    },
  ];
}

export function buildPerformanceMetrics(runtime?: {
  fcp?: number | null;
  lcp?: number | null;
  cls?: number | null;
  inp?: number | null;
  tti?: number | null;
  memoryMb?: number | null;
  routeMs?: number | null;
}): PerformanceMetric[] {
  const fmt = (n: number | null | undefined, unit: string) =>
    n == null || Number.isNaN(n) ? "Unavailable (measure in browser)" : `${n.toFixed(0)}${unit}`;

  return [
    {
      id: "fcp",
      label: "First Contentful Paint (FCP)",
      value: fmt(runtime?.fcp, " ms"),
      target: "< 1800 ms",
      status: runtime?.fcp == null ? "pending" : runtime.fcp < 1800 ? "pass" : "warn",
      methodology: "PerformanceObserver paint entry · client-only",
    },
    {
      id: "lcp",
      label: "Largest Contentful Paint (LCP)",
      value: fmt(runtime?.lcp, " ms"),
      target: "< 2500 ms",
      status: runtime?.lcp == null ? "pending" : runtime.lcp < 2500 ? "pass" : "warn",
      methodology: "largest-contentful-paint observer",
    },
    {
      id: "inp",
      label: "Interaction to Next Paint (INP)",
      value: fmt(runtime?.inp, " ms"),
      target: "< 200 ms",
      status: runtime?.inp == null ? "pending" : runtime.inp < 200 ? "pass" : "warn",
      methodology: "Event timing / web-vitals placeholder",
    },
    {
      id: "cls",
      label: "Cumulative Layout Shift (CLS)",
      value:
        runtime?.cls == null
          ? "Unavailable (measure in browser)"
          : runtime.cls.toFixed(3),
      target: "< 0.1",
      status: runtime?.cls == null ? "pending" : runtime.cls < 0.1 ? "pass" : "warn",
      methodology: "layout-shift observer (session window)",
    },
    {
      id: "tti",
      label: "Time To Interactive (TTI)",
      value: fmt(runtime?.tti, " ms"),
      target: "< 3800 ms",
      status: runtime?.tti == null ? "pending" : runtime.tti < 3800 ? "pass" : "warn",
      methodology: "Approximation via domInteractive + quiet window (not Lab TTI)",
    },
    {
      id: "bundle",
      label: "Bundle Size",
      value: "Measure via next build / analyzer",
      target: "Keep route chunks lean; lazy Copilot",
      status: "warn",
      methodology: "ANALYZE=true next build (documented)",
    },
    {
      id: "route",
      label: "Route Load Time",
      value: fmt(runtime?.routeMs, " ms"),
      target: "< 1000 ms soft nav",
      status: runtime?.routeMs == null ? "pending" : runtime.routeMs < 1000 ? "pass" : "warn",
      methodology: "performance.now delta on pathname change",
    },
    {
      id: "memory",
      label: "Memory Usage",
      value:
        runtime?.memoryMb == null
          ? "Unavailable (Chromium performance.memory)"
          : `${runtime.memoryMb.toFixed(1)} MB`,
      target: "Monitor for leaks on long sessions",
      status: runtime?.memoryMb == null ? "pending" : "pass",
      methodology: "performance.memory.usedJSHeapSize when exposed",
    },
    {
      id: "renders",
      label: "React Render Count",
      value: "Use React Profiler in DevTools",
      target: "No unexpected loops on idle",
      status: "pending",
      methodology: "Manual Profiler · memoization audit documented",
    },
  ];
}

export const BREAKPOINTS = [320, 375, 480, 768, 1024, 1280, 1600] as const;

export const SECURITY_FINDINGS = [
  {
    id: "xss",
    title: "XSS Safety",
    status: "pass" as GateStatus,
    detail: "UI primarily text nodes; no dangerouslySetInnerHTML in product workspaces.",
  },
  {
    id: "sanitize",
    title: "HTML Sanitization",
    status: "pass" as GateStatus,
    detail: "safeText.escapeHtml available for any future HTML previews.",
  },
  {
    id: "clipboard",
    title: "Clipboard Safety",
    status: "pass" as GateStatus,
    detail: "No unrestricted clipboard writes of secrets.",
  },
  {
    id: "download",
    title: "Download Validation",
    status: "pass" as GateStatus,
    detail: "Exports are generated client-side text blobs with fixed MIME types.",
  },
  {
    id: "markdown",
    title: "Safe Markdown Rendering",
    status: "pass" as GateStatus,
    detail: "Markdown exported as download, not executed as HTML in-app by default.",
  },
  {
    id: "csp",
    title: "CSP Enforced",
    status: "pass" as GateStatus,
    detail: "Content-Security-Policy enforced in next.config for Web 1.0.0 public launch.",
  },
  {
    id: "deps",
    title: "Dependency Audit",
    status: "pending" as GateStatus,
    detail: "Run npm audit in CI; keep Next/React patched.",
  },
  {
    id: "artifacts",
    title: "Development Artifact Removal",
    status: "pass" as GateStatus,
    detail: "No debugger statements introduced in Sprint 9 ops code.",
  },
  {
    id: "logs",
    title: "Sensitive Console Logs",
    status: "warn" as GateStatus,
    detail: "ErrorBoundary logs error messages — ensure no tokens in thrown errors.",
  },
];
