import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { LEGAL_DOCUMENTS, LEGAL_DOC_VERSION } from "@/lib/legal";

const DOCS = [
  {
    href: "/docs/quick-start",
    title: "Quick Start",
    file: "docs/P6_1_COMMERCIAL_READINESS.md",
  },
  { href: "/docs/faq", title: "FAQ", file: "docs/FAQ_CLOSED_BETA_RC.md" },
  {
    href: "/docs/pricing",
    title: "Editions & Pricing",
    file: "docs/commercial/PRODUCT_PACKAGING.md",
  },
  {
    href: "/docs/support",
    title: "Customer Support",
    file: "docs/commercial/CUSTOMER_SUPPORT.md",
  },
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
  { href: "/docs/release-notes", title: "Release Notes", file: "docs/RELEASE_NOTES_v2.0.0-rc.md" },
  {
    href: LEGAL_DOCUMENTS.privacy.href,
    title: LEGAL_DOCUMENTS.privacy.title,
    file: LEGAL_DOCUMENTS.privacy.repoDoc,
  },
  {
    href: LEGAL_DOCUMENTS.terms.href,
    title: LEGAL_DOCUMENTS.terms.title,
    file: LEGAL_DOCUMENTS.terms.repoDoc,
  },
  {
    href: LEGAL_DOCUMENTS.disclaimer.href,
    title: LEGAL_DOCUMENTS.disclaimer.title,
    file: LEGAL_DOCUMENTS.disclaimer.repoDoc,
  },
  {
    href: LEGAL_DOCUMENTS.risk.href,
    title: LEGAL_DOCUMENTS.risk.title,
    file: LEGAL_DOCUMENTS.risk.repoDoc,
  },
  {
    href: LEGAL_DOCUMENTS.cookies.href,
    title: LEGAL_DOCUMENTS.cookies.title,
    file: LEGAL_DOCUMENTS.cookies.repoDoc,
  },
  {
    href: LEGAL_DOCUMENTS["data-usage"].href,
    title: LEGAL_DOCUMENTS["data-usage"].title,
    file: LEGAL_DOCUMENTS["data-usage"].repoDoc,
  },
] as const;

export default function DocsIndexPage() {
  return (
    <div>
      <PageHeader
        title="Documentation"
        description={`Web ${LEGAL_DOC_VERSION} published guides — presentation summaries for operators and users.`}
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
