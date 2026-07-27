import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { CopilotLayout } from "@/components/copilot/CopilotLayout";

export default function CopilotPage() {
  return (
    <ProtectedRoute>
      <CopilotLayout />
    </ProtectedRoute>
  );
}
