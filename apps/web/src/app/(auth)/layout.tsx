import type { Metadata } from "next";
import type { ReactNode } from "react";

import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: {
    default: `Sign in · ${env.appName}`,
    template: `%s · ${env.appName}`,
  },
  robots: { index: false, follow: false },
};

export default function AuthLayout({ children }: { children: ReactNode }) {
  return children;
}
