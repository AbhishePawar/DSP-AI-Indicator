import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Set new password",
};

export default function ResetPasswordLayout({ children }: { children: ReactNode }) {
  return children;
}
