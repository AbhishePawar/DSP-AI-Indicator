"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { AuthCard, AuthShell, isValidEmail, mapAuthError } from "@/components/auth";
import {
  Alert,
  Button,
  FormField,
  Input,
  Stack,
  Textarea,
  ValidationMessage,
} from "@/components/ds";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import { SUPPORT_CONTACT } from "@/lib/commercial";

/**
 * Enterprise Request Access workflow — Submit → Admin Approval → Invitation.
 * Coexists with self-service /register.
 */
export default function SignUpPage() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [organization, setOrganization] = useState("");
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
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.submitAccessRequest({
        name: name.trim(),
        email: email.trim(),
        organization: organization.trim(),
        reason: reason.trim(),
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
                <FormField label="Organization" htmlFor="signup-org" hint="Optional">
                  <Input
                    id="signup-org"
                    value={organization}
                    onChange={(e) => setOrganization(e.target.value)}
                    autoComplete="organization"
                    disabled={pending}
                  />
                </FormField>
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
