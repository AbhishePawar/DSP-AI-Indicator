"use client";

import { useState } from "react";
import {
  Alert,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  PasswordInput,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Spinner,
} from "@/components/ds";
import { api } from "@/lib/api/client";
import type { ConnectionTestResponse, ProviderRecord } from "@/lib/api/providerTypes";

export type CredentialModalProps = {
  provider: ProviderRecord | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  token?: string | null;
  onSuccess: () => void;
};

export function CredentialModal({
  provider,
  open,
  onOpenChange,
  token,
  onSuccess,
}: CredentialModalProps) {
  const [secret, setSecret] = useState("");
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [validateBeforeSave, setValidateBeforeSave] = useState(true);

  // Test state
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<ConnectionTestResponse | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  // Save state
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  if (!provider) return null;

  const currentModel = selectedModel || provider.selected_model;

  const handleTest = async () => {
    if (!secret.trim()) {
      setTestError("Please enter an API key or token to test.");
      return;
    }
    setTesting(true);
    setTestError(null);
    setTestResult(null);

    try {
      const res = await api.adminTestProvider(
        provider.provider_id,
        {
          secret: secret.trim(),
          model: currentModel || undefined,
        },
        { token },
      );
      setTestResult(res);
      if (!res.success) {
        setTestError(res.sanitized_error || "Connection test failed.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Connection test request failed.";
      setTestError(msg);
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    if (!secret.trim()) {
      setSaveError("API key or secret cannot be empty.");
      return;
    }
    setSaving(true);
    setSaveError(null);

    try {
      const res = await api.adminSaveProviderCredential(
        provider.provider_id,
        {
          secret: secret.trim(),
          validate: validateBeforeSave,
          selected_model: currentModel || undefined,
        },
        { token },
      );
      if (res.ok) {
        setSecret("");
        setTestResult(null);
        setTestError(null);
        onOpenChange(false);
        onSuccess();
      } else {
        setSaveError("Failed to update credential.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to store credential.";
      setSaveError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    setSecret("");
    setTestResult(null);
    setTestError(null);
    setSaveError(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={(val) => (!val ? handleClose() : onOpenChange(val))}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Configure {provider.display_name} Credential</DialogTitle>
          <DialogDescription>
            Securely replace the API key or token for {provider.display_name} ({provider.provider_id}). Keys are validated server-side and never exposed in the browser or logs.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {saveError ? (
            <Alert variant="error" title="Validation / Storage Failed">
              {saveError}
            </Alert>
          ) : null}

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">
              Active Model
            </label>
            {provider.available_models && provider.available_models.length > 0 ? (
              <Select
                value={currentModel}
                onValueChange={(val) => setSelectedModel(val)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select model" />
                </SelectTrigger>
                <SelectContent>
                  {provider.available_models.map((m) => (
                    <SelectItem key={m} value={m}>
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <p className="text-sm font-medium text-[var(--fg)]">{provider.selected_model || "Default model"}</p>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">
              New API Key / Token
            </label>
            <PasswordInput
              value={secret}
              onChange={(e) => {
                setSecret(e.target.value);
                setTestResult(null);
                setTestError(null);
                setSaveError(null);
              }}
              placeholder={`Enter ${provider.display_name} key...`}
              autoFocus
            />
            <p className="mt-1 text-xs text-[var(--muted)]">
              Secret is encrypted and stored at rest. Old working keys are preserved if test validation fails.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="validateBeforeSave"
              checked={validateBeforeSave}
              onChange={(e) => setValidateBeforeSave(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--border)] text-[var(--accent)] focus:ring-[var(--accent)]"
            />
            <label htmlFor="validateBeforeSave" className="text-xs text-[var(--fg)] cursor-pointer">
              Validate connection before saving (prevents broken keys from being activated)
            </label>
          </div>

          {/* Test Feedback Area */}
          {testResult?.success ? (
            <Alert variant="success" title="Connection Successful">
              <div className="text-xs space-y-1">
                <p>Status: <span className="font-semibold">{testResult.status}</span></p>
                <p>Latency: <span className="font-semibold">{testResult.latency_ms} ms</span></p>
              </div>
            </Alert>
          ) : null}

          {testError ? (
            <Alert variant="error" title="Connection Test Failed">
              <p className="text-xs">{testError}</p>
              {testResult?.recommended_action ? (
                <p className="mt-1 text-xs italic">Recommendation: {testResult.recommended_action}</p>
              ) : null}
            </Alert>
          ) : null}
        </div>

        <DialogFooter className="flex items-center justify-between sm:justify-between gap-2 border-t border-[var(--border)] pt-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleTest}
            disabled={testing || saving || !secret.trim()}
          >
            {testing ? (
              <>
                <Spinner className="mr-2 h-3.5 w-3.5" />
                Testing...
              </>
            ) : (
              "Test Connection First"
            )}
          </Button>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleClose}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={handleSave}
              disabled={saving || testing || !secret.trim()}
            >
              {saving ? (
                <>
                  <Spinner className="mr-2 h-3.5 w-3.5" />
                  Saving...
                </>
              ) : (
                "Save & Activate"
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
