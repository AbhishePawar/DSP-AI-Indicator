import { DocArticle } from "@/components/launch/DocArticle";
import { PageHeader } from "@/components/layout/PageHeader";

export default function PrivacyPage() {
  return (
    <div>
      <PageHeader title="Privacy Policy" description="Web 1.0.0" />
      <DocArticle
        title="Privacy Policy (1.0.0)"
        sections={[
          {
            heading: "Summary",
            body: [
              "DSP Web stores session preferences and optional local beta feedback in the browser.",
              "Feedback redacts tokens/JWTs and must not include research envelopes, portfolio holdings, or API secrets.",
              "No third-party analytics SDK is required for 1.0.0. Operators configure production logging separately.",
            ],
          },
          {
            heading: "Contact",
            body: [
              "For data requests, contact your DSP platform administrator. This summary does not replace jurisdictional legal review.",
            ],
          },
        ]}
      />
    </div>
  );
}
