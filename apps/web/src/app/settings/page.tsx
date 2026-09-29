"use client";

/**
 * Figma Settings lives at /control-center. Keep /settings as a stable alias.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { Skeleton } from "@/components/ds";

export default function SettingsRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/control-center");
  }, [router]);

  return (
    <div className="space-y-4 py-6" role="status" aria-label="Opening settings">
      <Skeleton className="h-20 w-full" />
    </div>
  );
}
