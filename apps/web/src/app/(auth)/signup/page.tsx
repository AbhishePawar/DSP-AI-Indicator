"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { AuthCard, AuthShell, isValidEmail } from "@/components/auth";
import {
  Alert,
  Button,
  FormField,
  Input,
  Stack,
  Textarea,
  ValidationMessage,
} from "@/components/ds";
import { SUPPORT_CONTACT } from "@/lib/commercial";

/**
 * RC3-002 — Honest Request Access workflow.
 * No self-service registration API; no password collection.
 */
export default function SignUpPage() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [organization, setOrganization] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [prepared, setPrepared] = useState(false);

  function onSubmit(event: FormEvent) {
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
    // Local preparation only — no registration API, no account creation.
    setPrepared(true);
  }

  return (
    <AuthShell>
      <AuthCard
        title="Request access"
        description="Accounts are provisioned by DSP AI Indicator administrators. This form does not create an account or call a registration API."
      >
        <Stack gap={4}>
          {prepared ? (
            <>
              <Alert variant="info" title="Access request not submitted online">
                No account was created and no request was sent to DSP servers.
                Share your details with your programme administrator so they can
                provision access.
              </Alert>
              <dl className="space-y-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-sm">
                <div>
                  <dt className="text-[var(--muted)]">Name</dt>
                  <dd className="font-medium">{name.trim()}</dd>
                </div>
                <div>
                  <dt className="text-[var(--muted)]">Email</dt>
                  <dd className="font-medium">{email.trim()}</dd>
                </div>
                {organization.trim() ? (
                  <div>
                    <dt className="text-[var(--muted)]">Organization</dt>
                    <dd className="font-medium">{organization.trim()}</dd>
                  </div>
                ) : null}
                {reason.trim() ? (
                  <div>
                    <dt className="text-[var(--muted)]">Reason for access</dt>
                    <dd className="font-medium">{reason.trim()}</dd>
                  </div>
                ) : null}
              </dl>
              <div className="flex flex-wrap gap-2">
                <Button type="button" variant="secondary" onClick={() => setPrepared(false)}>
                  Edit details
                </Button>
                <Link href="/login">
                  <Button>Sign in if already provisioned</Button>
                </Link>
              </div>
            </>
          ) : (
            <>
              <Alert variant="info" title="Administrator provisioning">
                Accounts are provisioned by the DSP AI Indicator administrators.
                Prepare your details below, then contact your programme
                administrator. Passwords are never collected on this page.
              </Alert>
              <form className="space-y-4" onSubmit={onSubmit} noValidate>
                <FormField label="Full name" htmlFor="signup-name" required>
                  <Input
                    id="signup-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    autoComplete="name"
                    required
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
                  />
                </FormField>
                <FormField
                  label="Organization"
                  htmlFor="signup-org"
                  hint="Optional"
                >
                  <Input
                    id="signup-org"
                    value={organization}
                    onChange={(e) => setOrganization(e.target.value)}
                    autoComplete="organization"
                  />
                </FormField>
                <FormField
                  label="Reason for access"
                  htmlFor="signup-reason"
                  hint="Optional"
                >
                  <Textarea
                    id="signup-reason"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    rows={3}
                  />
                </FormField>
                {error ? (
                  <ValidationMessage tone="error">{error}</ValidationMessage>
                ) : null}
                <Button type="submit" className="w-full">
                  Prepare access details
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
