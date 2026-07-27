import { PageHeader } from "@/components/layout/PageHeader";
import { UserProfile } from "@/components/profile/UserProfile";

export default function ProfilePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Profile"
        description="Your session identity and authentication status."
      />
      <UserProfile />
    </div>
  );
}
