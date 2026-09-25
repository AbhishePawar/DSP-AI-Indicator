/**
 * /profile/account — account identity, sessions and security (the view that
 * previously rendered at /profile before that route took the Figma
 * Financial Profile). Unchanged component; relocated route only.
 */

import { UserProfile } from "@/components/profile/UserProfile";

export default function AccountProfilePage() {
  return <UserProfile />;
}
