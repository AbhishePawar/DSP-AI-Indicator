import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { PageHeader } from "@/components/layout/PageHeader";
import { DiagnosticsDashboard } from "@/components/observability/DiagnosticsDashboard";

export default function DiagnosticsPage() {
  return (
    <ProtectedRoute>
      <div className="space-y-6">
        <PageHeader
          title="Diagnostics"
          description="Production readiness visibility — version, session, errors, and timings. No external telemetry."
        />
        <DiagnosticsDashboard />
      </div>
    </ProtectedRoute>
  );
}
