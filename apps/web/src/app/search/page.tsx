import { redirect } from "next/navigation";

/** L1.0 route — redirects to Company Analysis (L1.1). */
export default function SearchRedirectPage() {
  redirect("/analysis");
}
