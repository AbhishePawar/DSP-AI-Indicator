"use client";

import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Spinner,
} from "@/components/ds";
import { api } from "@/lib/api/client";
import type { ProviderRecord, TaskRoutingPolicy } from "@/lib/api/providerTypes";

export type TaskRoutingPanelProps = {
  policies: TaskRoutingPolicy[];
  availableProviders: ProviderRecord[];
  token?: string | null;
  onRefresh: () => void;
};

export function TaskRoutingPanel({
  policies,
  availableProviders,
  token,
  onRefresh,
}: TaskRoutingPanelProps) {
  const [editingTask, setEditingTask] = useState<string | null>(null);
  const [primary, setPrimary] = useState("");
  const [fallback, setFallback] = useState("");
  const [corroborate, setCorroborate] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const activeAiProviders = availableProviders.filter(
    (p) => p.category === "ai" && p.is_active,
  );

  const startEdit = (policy: TaskRoutingPolicy) => {
    setEditingTask(policy.task_id);
    setPrimary(policy.primary_provider);
    setFallback(policy.fallback_providers?.[0] || "");
    setCorroborate(policy.require_independent_corroboration);
    setError(null);
    setSuccess(null);
  };

  const cancelEdit = () => {
    setEditingTask(null);
    setError(null);
  };

  const handleSave = async (taskId: string) => {
    if (corroborate && (!fallback || fallback.toLowerCase() === primary.toLowerCase())) {
      setError("Independent corroboration requires selecting a distinct fallback provider.");
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      await api.adminUpdateTaskRouting(
        taskId,
        {
          primary_provider: primary,
          fallback_providers: fallback ? [fallback] : [],
          require_independent_corroboration: corroborate,
        },
        { token },
      );
      setSuccess(`Task routing for '${taskId}' updated.`);
      setEditingTask(null);
      onRefresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update routing policy.");
    } finally {
      setSaving(false);
    }
  };

  const getTaskLabel = (id: string) => {
    switch (id) {
      case "equity_research_synthesis":
        return "Equity Research Synthesis";
      case "financial_statement_extraction":
        return "Financial Statement Extraction";
      case "copilot_reasoning":
        return "AI Copilot & Conversational Reasoning";
      case "valuation_corroboration":
        return "Valuation Independent Corroboration";
      default:
        return id.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
    }
  };

  return (
    <Card className="border-[var(--border)] bg-[var(--surface)]">
      <CardHeader>
        <CardTitle className="text-base font-semibold">Model Task Routing & Corroboration Policies</CardTitle>
        <CardDescription className="text-xs text-[var(--muted)]">
          Configure model execution hierarchies, fallbacks, and multi-model corroboration gates. Research extraction enforces dual-model independence.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-3">
        {error ? (
          <Alert variant="error" title="Routing Error">
            {error}
          </Alert>
        ) : null}

        {success ? (
          <Alert variant="success" title="Success">
            {success}
          </Alert>
        ) : null}

        <div className="space-y-3">
          {policies.map((policy) => {
            const isEditing = editingTask === policy.task_id;
            return (
              <div
                key={policy.task_id}
                className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)]/60 p-3 text-xs"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-[var(--border)]">
                  <div>
                    <span className="font-semibold text-sm text-[var(--fg)]">
                      {getTaskLabel(policy.task_id)}
                    </span>
                    <span className="font-mono text-[10px] text-[var(--muted)] ml-2">
                      ({policy.task_id})
                    </span>
                  </div>

                  {policy.require_independent_corroboration ? (
                    <Badge variant="accent">Independent Corroboration Active</Badge>
                  ) : (
                    <Badge variant="outline">Single Provider Execution</Badge>
                  )}
                </div>

                {isEditing ? (
                  <div className="pt-3 space-y-3">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-semibold text-[var(--muted)] uppercase mb-1">
                          Primary Provider
                        </label>
                        <Select value={primary} onValueChange={(val) => setPrimary(val)}>
                          <SelectTrigger className="h-8 text-xs w-full bg-[var(--surface)]">
                            <SelectValue placeholder="Select primary" />
                          </SelectTrigger>
                          <SelectContent>
                            {availableProviders.map((p) => (
                              <SelectItem key={p.provider_id} value={p.provider_id} className="text-xs">
                                {p.display_name} ({p.selected_model})
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-[var(--muted)] uppercase mb-1">
                          Fallback / Secondary Provider
                        </label>
                        <Select value={fallback} onValueChange={(val) => setFallback(val)}>
                          <SelectTrigger className="h-8 text-xs w-full bg-[var(--surface)]">
                            <SelectValue placeholder="Select fallback" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="" className="text-xs italic">
                              None
                            </SelectItem>
                            {availableProviders.map((p) => (
                              <SelectItem key={p.provider_id} value={p.provider_id} className="text-xs">
                                {p.display_name} ({p.selected_model})
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pt-1">
                      <input
                        type="checkbox"
                        id={`corroborate-${policy.task_id}`}
                        checked={corroborate}
                        onChange={(e) => setCorroborate(e.target.checked)}
                        className="h-4 w-4 rounded border-[var(--border)] text-[var(--accent)] focus:ring-[var(--accent)]"
                      />
                      <label
                        htmlFor={`corroborate-${policy.task_id}`}
                        className="text-xs text-[var(--fg)] cursor-pointer"
                      >
                        Enforce independent dual-model corroboration (5% reconciliation threshold)
                      </label>
                    </div>

                    <div className="flex items-center justify-end gap-2 pt-1">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={cancelEdit}
                        disabled={saving}
                      >
                        Cancel
                      </Button>
                      <Button
                        type="button"
                        variant="primary"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => handleSave(policy.task_id)}
                        disabled={saving}
                      >
                        {saving ? <Spinner className="h-3 w-3 mr-1" /> : null}
                        Save Policy
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-4 text-xs">
                      <div>
                        <span className="text-[var(--muted)]">Primary: </span>
                        <span className="font-semibold text-[var(--fg)]">
                          {policy.primary_provider}
                        </span>
                      </div>
                      <div>
                        <span className="text-[var(--muted)]">Fallback: </span>
                        <span className="font-semibold text-[var(--fg)]">
                          {policy.fallback_providers?.join(", ") || "None"}
                        </span>
                      </div>
                    </div>

                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs self-end sm:self-auto"
                      onClick={() => startEdit(policy)}
                    >
                      Configure Routing
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
