import { AnalysisRouteClient } from "./AnalysisRouteClient";

export const dynamic = "force-dynamic";

/**
 * Dynamic server page so /analysis is not frozen as a static loading shell.
 * Search params stay inside the client subtree.
 */
export default function AnalysisPage() {
  return <AnalysisRouteClient />;
}
