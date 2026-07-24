import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";

export default function ComparePage() {
  return (
    <div>
      <PageHeader
        title="Compare Companies"
        description="Comparison requests will call the backend orchestration API. No peer scoring runs in the browser."
      />
      <Card>
        <CardBody>
          <Alert tone="info" title="Workspace stub">
            Full compare UX lands in a later L1 phase. Navigation and layout are
            ready.
          </Alert>
          <div className="mt-4">
            <EmptyState
              title="No comparison yet"
              description="Select companies via the API-backed workspace when L1.x compare ships."
            />
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
