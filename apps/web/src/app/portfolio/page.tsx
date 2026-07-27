"use client";

import { PortfolioFoundation } from "@/components/portfolio/PortfolioFoundation";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";

export default function PortfolioPage() {
  return (
    <ProtectedRoute>
      <PortfolioFoundation />
    </ProtectedRoute>
  );
}
