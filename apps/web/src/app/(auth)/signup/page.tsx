"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { AuthCard, AuthShell, isValidEmail, mapAuthError } from "@/components/auth";
import {
  Alert,
  Button,
  FormField,
  Input,
  RadioGroup,
  RadioGroupItem,
  Stack,
  Textarea,
  ValidationMessage,
} from "@/components/ds";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import { SUPPORT_CONTACT } from "@/lib/commercial";

type RequesterType = "individual" | "organization";

/**
 * Enterprise Request Access workflow — Submit → Admin Approval → Invitation.
 * Coexists with self-service /register.
 *
 * The backend access-request schema only persists {name, email, organization,
 * reason} (see AccessRequestBody in enterprise_auth_platform.py). Phone,
 * industry, country and requester type have no dedicated backend columns —
 * changing that schema is out of scope here — so they are captured honestly
 * and packed into the structured `reason` text rather than silently dropped.
 */
export default function SignUpPage() {
  const [requesterType, setRequesterType] = useState<RequesterType>("individual");
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [industry, setIndustry] = useState("");
  const [country, setCountry] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [requestId, setRequestId] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError("Full name is required.");
      return;
    }
    if (!isValidEmail(email)) {
      setError("Enter a valid work email.");
      return;
    }
    if (requesterType === "organization" && !company.trim()) {
      setError("Company name is required for organization requests.");
      return;
    }
    setPending(true);
    try {
      const metadata = [
        `Requester type: ${requesterType === "organization" ? "Organization" : "Individual"}`,
        phone.trim() ? `Phone: ${phone.trim()}` : null,
        industry.trim() ? `Industry: ${industry.trim()}` : null,
        country.trim() ? `Country: ${country.trim()}` : null,
      ]
        .filter(Boolean)
        .join(" · ");
      const composedReason = [metadata, reason.trim()].filter(Boolean).join("\n\n");

      const envelope = await enterpriseAuthApi.submitAccessRequest({
        name: name.trim(),
        email: email.trim(),
        organization: company.trim(),
        reason: composedReason,
      });
      if (!envelope.ok) {
        throw new Error(envelope.error || "Request failed");
      }
      const req = (envelope.result as { request?: { request_id?: string } } | undefined)
        ?.request;
      setRequestId(req?.request_id || null);
      setSubmitted(true);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthShell>
      <AuthCard
        title="Request access"
        description="Enterprise onboarding: submit a request for administrator approval. An invitation to create your password follows approval."
      >
        <Stack gap={4}>
          {submitted ? (
            <>
              <Alert variant="success" title="Access request submitted">
                Your request was recorded for administrator review. You will
                receive an invitation to create a password after approval.
              </Alert>
              {requestId ? (
                <p className="text-sm text-[var(--muted)]">
                  Reference: <span className="font-medium">{requestId}</span>
                </p>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <Link href="/login">
                  <Button>Sign in if already provisioned</Button>
                </Link>
                <Link href="/register">
                  <Button variant="secondary">Self-service register</Button>
                </Link>
              </div>
            </>
          ) : (
            <>
              <Alert variant="info" title="Enterprise workflow">
                Submit → Admin Approval → Invitation → Create Password → Login.
                For immediate self-service, use Register instead.
              </Alert>
              <form className="space-y-4" onSubmit={onSubmit} noValidate>
                <fieldset className="flex flex-col gap-1.5">
                  <legend className="text-sm font-medium text-[var(--fg)]">
                    Requesting access as
                  </legend>
                  <RadioGroup
                    value={requesterType}
                    onValueChange={(v) => setRequesterType(v as RequesterType)}
                    className="flex gap-4"
                    aria-label="Requester type"
                  >
                    <label className="flex items-center gap-2 text-sm text-[var(--fg)]">
                      <RadioGroupItem value="individual" id="requester-individual" disabled={pending} />
                      Individual
                    </label>
                    <label className="flex items-center gap-2 text-sm text-[var(--fg)]">
                      <RadioGroupItem value="organization" id="requester-organization" disabled={pending} />
                      Organization
                    </label>
                  </RadioGroup>
                </fieldset>

                <FormField label="Full name" htmlFor="signup-name" required>
                  <Input
                    id="signup-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    autoComplete="name"
                    required
                    disabled={pending}
                  />
                </FormField>
                <FormField
                  label="Company"
                  htmlFor="signup-company"
                  required={requesterType === "organization"}
                  hint={requesterType === "individual" ? "Optional" : undefined}
                >
                  <Input
                    id="signup-company"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    autoComplete="organization"
                    required={requesterType === "organization"}
                    disabled={pending}
                  />
                </FormField>
                <FormField label="Work email" htmlFor="signup-email" required>
                  <Input
                    id="signup-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                    disabled={pending}
                  />
                </FormField>
                <FormField label="Phone" htmlFor="signup-phone" hint="Optional">
                  <Input
                    id="signup-phone"
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    autoComplete="tel"
                    disabled={pending}
                  />
                </FormField>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <FormField label="Industry" htmlFor="signup-industry" hint="Optional">
                    <Input
                      id="signup-industry"
                      value={industry}
                      onChange={(e) => setIndustry(e.target.value)}
                      disabled={pending}
                    />
                  </FormField>
                  <FormField label="Country" htmlFor="signup-country" hint="Optional">
                    <Input
                      id="signup-country"
                      value={country}
                      onChange={(e) => setCountry(e.target.value)}
                      autoComplete="country-name"
                      disabled={pending}
                    />
                  </FormField>
                </div>
                <FormField label="Reason for access" htmlFor="signup-reason" hint="Optional">
                  <Textarea
                    id="signup-reason"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    rows={3}
                    disabled={pending}
                  />
                </FormField>
                {error ? (
                  <ValidationMessage tone="error">{error}</ValidationMessage>
                ) : null}
                <Button type="submit" className="w-full" disabled={pending}>
                  {pending ? "Submitting…" : "Submit access request"}
                </Button>
              </form>
            </>
          )}
          <p className="text-center text-sm text-[var(--muted)]">
            Already provisioned?{" "}
            <Link
              href="/login"
              className="text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Sign in
            </Link>
            {" · "}
            <Link
              href="/register"
              className="text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Register
            </Link>
          </p>
          <p className="text-xs text-[var(--muted)]">
            {SUPPORT_CONTACT.channelsPublished
              ? `Sales: ${SUPPORT_CONTACT.salesEmail}`
              : SUPPORT_CONTACT.unpublishedNote}
          </p>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
