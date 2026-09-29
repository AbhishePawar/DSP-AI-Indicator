import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { PageHeader } from "@/components/layout/PageHeader";
import { DiagnosticsDashboard } from "@/components/observability/DiagnosticsDashboard";

export default function DiagnosticsPage() {
  return (
    <ProtectedRoute>
      <div className="space-y-6">
        <PageHeader
          title="Diagnostics"
          description="System health from the live diagnostics dashboard. Design-file service checks and sample logs are not shown."
        />
        <DiagnosticsDashboard />
      </div>
    </ProtectedRoute>
  );
}
