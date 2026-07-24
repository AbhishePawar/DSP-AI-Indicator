import { DocArticle } from "@/components/launch/DocArticle";
import { PageHeader } from "@/components/layout/PageHeader";

export default function AdminGuidePage() {
  return (
    <div>
      <PageHeader title="Administrator Guide" description="Web 1.0.0" />
      <DocArticle
        title="DSP Platform — Administrator Guide (1.0.0)"
        sections={[
          {
            heading: "Deploy",
            body: [
              "API: DSP_ENABLE_SECURITY=true · uvicorn api_platform.api.app:app",
              "Web: npm ci && npm run build && npm run start with NEXT_PUBLIC_API_BASE_URL pointing at /api/v1.",
              "Terminate TLS at the edge. Confirm /health and /launch quality gates.",
            ],
          },
          {
            heading: "Freeze",
            body: [
              "Respect apps/web/VERSION_MANIFEST.json and docs/VERSION_FREEZE_v1.0.0.md.",
              "Do not change Research Mode / Feature Flag defaults without governance.",
            ],
          },
          {
            heading: "Operate",
            body: [
              "Monitor /launch for release health, /launch/performance for vitals, /beta for feedback.",
              "Critical bugs must remain 0. Regression suite must stay GREEN before promoting traffic.",
            ],
          },
        ]}
      />
    </div>
  );
}
