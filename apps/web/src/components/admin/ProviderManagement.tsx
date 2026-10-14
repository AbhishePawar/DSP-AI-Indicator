"use client";

import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Spinner,
} from "@/components/ds";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import type { ProviderRecord } from "@/lib/api/providerTypes";
import { ProviderCard } from "./ProviderCard";
import { CredentialModal } from "./CredentialModal";
import { ProviderAuditModal } from "./ProviderAuditModal";
import { TaskRoutingPanel } from "./TaskRoutingPanel";

export function ProviderManagement() {
  const { session } = useAuth();
  const token = session?.accessToken;
  const opts = useMemo(() => ({ token }), [token]);
  const qc = useQueryClient();

  const [categoryFilter, setCategoryFilter] = useState<"all" | "ai" | "market_data">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedProviderForCredential, setSelectedProviderForCredential] =
    useState<ProviderRecord | null>(null);
  const [credentialModalOpen, setCredentialModalOpen] = useState(false);
  const [selectedProviderForAudit, setSelectedProviderForAudit] =
    useState<ProviderRecord | null>(null);
  const [auditModalOpen, setAuditModalOpen] = useState(false);

  // Queries
  const providersQuery = useQuery({
    queryKey: ["admin", "providers"],
    queryFn: () => api.adminListProviders(undefined, opts),
    staleTime: 5000,
  });

  const routingQuery = useQuery({
    queryKey: ["admin", "routing"],
    queryFn: () => api.adminGetRoutingPolicies(opts),
    staleTime: 5000,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["admin", "providers"] });
    qc.invalidateQueries({ queryKey: ["admin", "routing"] });
  };

  const providers = providersQuery.data?.providers || [];
  const policies = routingQuery.data?.policies || [];

  // Filtered providers
  const filteredProviders = useMemo(() => {
    return providers.filter((p) => {
      const matchCat = categoryFilter === "all" || p.category === categoryFilter;
      const matchSearch =
        !searchQuery.trim() ||
        p.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.provider_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.selected_model.toLowerCase().includes(searchQuery.toLowerCase());
      return matchCat && matchSearch;
    });
  }, [providers, categoryFilter, searchQuery]);

  // Aggregate stats
  const total = providers.length;
  const activeCount = providers.filter((p) => p.is_active).length;
  const configuredCount = providers.filter((p) => p.has_credential).length;
  const healthyCount = providers.filter((p) => p.health_status === "healthy").length;

  return (
    <div className="space-y-6">
      {/* Overview Stat Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="border-[var(--border)] bg-[var(--surface)] p-3">
          <div className="text-xs text-[var(--muted)]">Total Registered</div>
          <div className="text-2xl font-bold text-[var(--fg)]">{total}</div>
        </Card>
        <Card className="border-[var(--border)] bg-[var(--surface)] p-3">
          <div className="text-xs text-[var(--muted)]">Active for Routing</div>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {activeCount}
          </div>
        </Card>
        <Card className="border-[var(--border)] bg-[var(--surface)] p-3">
          <div className="text-xs text-[var(--muted)]">Credentials Configured</div>
          <div className="text-2xl font-bold text-[var(--accent)]">{configuredCount}</div>
        </Card>
        <Card className="border-[var(--border)] bg-[var(--surface)] p-3">
          <div className="text-xs text-[var(--muted)]">Healthy Verified</div>
          <div className="text-2xl font-bold text-[var(--fg)]">{healthyCount}</div>
        </Card>
      </div>

      {/* Control Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 border border-[var(--border)] bg-[var(--surface-2)] p-1 rounded-lg">
          <button
            type="button"
            className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
              categoryFilter === "all"
                ? "bg-[var(--surface)] text-[var(--fg)] shadow-xs"
                : "text-[var(--muted)] hover:text-[var(--fg)]"
            }`}
            onClick={() => setCategoryFilter("all")}
          >
            All Providers ({total})
          </button>
          <button
            type="button"
            className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
              categoryFilter === "ai"
                ? "bg-[var(--surface)] text-[var(--fg)] shadow-xs"
                : "text-[var(--muted)] hover:text-[var(--fg)]"
            }`}
            onClick={() => setCategoryFilter("ai")}
          >
            AI Models ({providers.filter((p) => p.category === "ai").length})
          </button>
          <button
            type="button"
            className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
              categoryFilter === "market_data"
                ? "bg-[var(--surface)] text-[var(--fg)] shadow-xs"
                : "text-[var(--muted)] hover:text-[var(--fg)]"
            }`}
            onClick={() => setCategoryFilter("market_data")}
          >
            Market Data ({providers.filter((p) => p.category === "market_data").length})
          </button>
        </div>

        <div className="flex items-center gap-2">
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search provider or model..."
            className="h-8 text-xs w-48 sm:w-64"
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8 text-xs"
            onClick={invalidate}
            disabled={providersQuery.isFetching}
          >
            {providersQuery.isFetching ? <Spinner className="h-3 w-3 mr-1" /> : null}
            Refresh
          </Button>
        </div>
      </div>

      {/* Loading or Error states */}
      {providersQuery.isLoading ? (
        <div className="flex flex-col items-center justify-center p-12 text-sm text-[var(--muted)] space-y-2">
          <Spinner className="h-6 w-6 text-[var(--accent)]" />
          <p>Loading AI and market data providers...</p>
        </div>
      ) : null}

      {providersQuery.isError ? (
        <Alert variant="error" title="Failed to load providers">
          {providersQuery.error instanceof Error
            ? providersQuery.error.message
            : "Data unavailable."}
        </Alert>
      ) : null}

      {/* Providers Grid */}
      {!providersQuery.isLoading && !providersQuery.isError ? (
        filteredProviders.length === 0 ? (
          <div className="text-center py-12 border border-dashed border-[var(--border)] rounded-xl text-sm text-[var(--muted)]">
            No providers found matching your filter criteria.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredProviders.map((provider) => (
              <ProviderCard
                key={provider.provider_id}
                provider={provider}
                token={token}
                onRefresh={invalidate}
                onOpenCredentialModal={(p) => {
                  setSelectedProviderForCredential(p);
                  setCredentialModalOpen(true);
                }}
                onOpenAuditModal={(p) => {
                  setSelectedProviderForAudit(p);
                  setAuditModalOpen(true);
                }}
              />
            ))}
          </div>
        )
      ) : null}

      {/* Task Routing & Fallback Section */}
      <div className="pt-4 border-t border-[var(--border)]">
        <TaskRoutingPanel
          policies={policies}
          availableProviders={providers}
          token={token}
          onRefresh={invalidate}
        />
      </div>

      {/* Modals */}
      <CredentialModal
        provider={selectedProviderForCredential}
        open={credentialModalOpen}
        onOpenChange={setCredentialModalOpen}
        token={token}
        onSuccess={invalidate}
      />

      <ProviderAuditModal
        provider={selectedProviderForAudit}
        open={auditModalOpen}
        onOpenChange={setAuditModalOpen}
        token={token}
      />
    </div>
  );
}
