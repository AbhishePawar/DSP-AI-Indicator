"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import { AuthCard, AuthShell, mapAuthError } from "@/components/auth";
import {
  Alert,
  Button,
  FormField,
  Input,
  PasswordInput,
  Stack,
  ValidationMessage,
} from "@/components/ds";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";

function InviteForm() {
  const searchParams = useSearchParams();
  const [token, setToken] = useState(searchParams.get("token") || "");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("Password confirmation does not match.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.acceptInvitation({
        token: token.trim(),
        password,
        confirm_password: confirm,
        username: username.trim() || undefined,
      });
      if (!envelope.ok) throw new Error(envelope.error || "Invitation failed");
      setDone(true);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthCard
      title="Accept invitation"
      description="Create your password after enterprise access approval."
    >
      <Stack gap={4}>
        {done ? (
          <>
            <Alert variant="success" title="Account created">
              Your enterprise account is ready. Sign in with your credentials.
            </Alert>
            <Link href="/login">
              <Button className="w-full">Sign in</Button>
            </Link>
          </>
        ) : (
          <form className="space-y-4" onSubmit={onSubmit} noValidate>
            <FormField label="Invitation token" htmlFor="invite-token" required>
              <Input
                id="invite-token"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                required
                disabled={pending}
              />
            </FormField>
            <FormField label="Username (optional)" htmlFor="invite-username">
              <Input
                id="invite-username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={pending}
              />
            </FormField>
            <FormField label="Password" htmlFor="invite-password" required>
              <PasswordInput
                id="invite-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={pending}
              />
            </FormField>
            <FormField label="Confirm password" htmlFor="invite-confirm" required>
              <PasswordInput
                id="invite-confirm"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                disabled={pending}
              />
            </FormField>
            {error ? (
              <ValidationMessage tone="error">{error}</ValidationMessage>
            ) : null}
            <Button type="submit" className="w-full" disabled={pending}>
              {pending ? "Creating…" : "Create password & activate"}
            </Button>
          </form>
        )}
      </Stack>
    </AuthCard>
  );
}

export default function InvitePage() {
  return (
    <AuthShell>
      <Suspense fallback={<AuthCard title="Accept invitation" description="Loading…" />}>
        <InviteForm />
      </Suspense>
    </AuthShell>
  );
}
