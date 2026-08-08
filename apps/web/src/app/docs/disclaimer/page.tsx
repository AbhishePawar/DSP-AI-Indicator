import { DocArticle } from "@/components/launch/DocArticle";
import { PageHeader } from "@/components/layout/PageHeader";
import { LEGAL_DOCUMENTS, LEGAL_DOC_VERSION } from "@/lib/legal";

export default function DisclaimerPage() {
  const doc = LEGAL_DOCUMENTS.disclaimer;
  return (
    <div>
      <PageHeader
        title={doc.title}
        description={`Web ${LEGAL_DOC_VERSION} · ${doc.repoDoc}`}
      />
      <DocArticle
        title={`${doc.title} (${LEGAL_DOC_VERSION})`}
        sections={doc.sections}
      />
    </div>
  );
}
