import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";

const DOCS = [
  { href: "/docs/user-guide", title: "User Guide", file: "docs/USER_GUIDE_v1.0.0.md" },
  {
    href: "/docs/administrator-guide",
    title: "Administrator Guide",
    file: "docs/ADMINISTRATOR_GUIDE_v1.0.0.md",
  },
  {
    href: "/docs/architecture-guide",
    title: "Architecture Guide",
    file: "docs/ARCHITECTURE_GUIDE_v1.0.0.md",
  },
  {
    href: "/docs/research-methodology",
    title: "Research Methodology",
    file: "docs/RESEARCH_METHODOLOGY_v1.0.0.md",
  },
  { href: "/docs/release-notes", title: "Release Notes", file: "docs/RELEASE_NOTES_v1.0.0.md" },
  { href: "/docs/privacy", title: "Privacy Policy", file: "docs/PRIVACY_POLICY_v1.0.0.md" },
  { href: "/docs/terms", title: "Terms of Use", file: "docs/TERMS_OF_USE_v1.0.0.md" },
  { href: "/docs/disclaimer", title: "Disclaimer", file: "docs/DISCLAIMER_v1.0.0.md" },
] as const;

export default function DocsIndexPage() {
  return (
    <div>
      <PageHeader
        title="Documentation"
        description="Web 1.0.0 published guides — presentation summaries for operators and users."
      />
      <div className="grid gap-3 sm:grid-cols-2">
        {DOCS.map((doc) => (
          <Card key={doc.href} className="dsp-interactive">
            <CardHeader title={doc.title} />
            <CardBody className="space-y-2 text-sm">
              <p className="text-[var(--muted)]">{doc.file}</p>
              <Link className="text-[var(--accent)] underline" href={doc.href}>
                Open summary
              </Link>
            </CardBody>
          </Card>
        ))}
      </div>
      <p className="mt-6 text-sm text-[var(--muted)]">
        Full markdown lives in the repository <code>docs/</code> folder.{" "}
        <Link className="text-[var(--accent)] underline" href="/launch">
          Back to Launch Dashboard
        </Link>
      </p>
    </div>
  );
}
