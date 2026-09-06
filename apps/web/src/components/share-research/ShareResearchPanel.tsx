"use client";

import { useState, type ReactNode } from "react";
import { useMutation } from "@tanstack/react-query";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { api, type ShareResearchClientResult } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";

export function ShareResearchPanel({
  ticker,
  exchange = "NSE",
}: {
  ticker: string;
  exchange?: string;
}) {
  const { session } = useAuth();
  const [open, setOpen] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () =>
      api.shareResearch(
        { ticker: ticker.trim().toUpperCase(), exchange },
        { token: session?.accessToken },
      ),
  });
  const result = mutation.data?.result;
  const disabled = !ticker.trim() || mutation.isPending;

  return (
    <Card className="mb-6">
      <CardHeader
        title="Shares Outstanding"
        description="Verified share count from primary-source research. DSP validates identity, dates, and currentness before valuation."
      />
      <CardBody>
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            disabled={disabled}
            onClick={() => mutation.mutate()}
            className="min-h-11"
          >
            {mutation.isPending
              ? "Researching…"
              : `Research ${ticker.trim().toUpperCase() || "shares"}`}
          </Button>
        </div>
        {mutation.isError ? (
          <div className="mt-4">
            <Alert tone="danger" title="Share verification could not be completed.">
              {userFacingShareError(mutation.error)}
            </Alert>
          </div>
        ) : null}
        {result ? <ShareResearchResultView result={result} open={open} setOpen={setOpen} /> : null}
      </CardBody>
    </Card>
  );
}

function ShareResearchResultView({
  result,
  open,
  setOpen,
}: {
  result: ShareResearchClientResult;
  open: string | null;
  setOpen: (value: string | null) => void;
}) {
  const shares = formatShares(result.outstanding_shares);
  return (
    <div className="mt-6 space-y-4">
      <p className="text-sm text-[var(--muted)]">
        <strong className="text-[var(--fg)]">{result.company || result.ticker}</strong>
        <span className="mt-1 block">
          {result.ticker} / {result.exchange} / {result.isin || "ISIN unavailable"}
        </span>
      </p>
      <div>
        <p className="text-sm text-[var(--muted)]">Outstanding Shares</p>
        <p className="font-[family-name:var(--font-display)] text-3xl tracking-tight">
          {shares}
        </p>
      </div>
      <StatusBanner result={result} />
      <ValuationLine eligible={result.valuation_eligible} />
      <Disclosure
        id="evidence"
        title="View Evidence"
        open={open}
        setOpen={setOpen}
      >
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {result.evidence.map((row) => (
            <li key={row.url}>
              {row.label}: {row.accepted ? "accepted" : "rejected"} — {row.url}
            </li>
          ))}
        </ul>
      </Disclosure>
      <Disclosure
        id="actions"
        title="Corporate Actions"
        open={open}
        setOpen={setOpen}
      >
        {result.corporate_actions.length === 0 ? (
          <p className="text-sm">No unresolved share-count-changing event recorded.</p>
        ) : (
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {result.corporate_actions.map((row) => (
              <li key={`${row.action_type}-${row.effective_date}-${row.description}`}>
                {row.action_type}: {row.description}
              </li>
            ))}
          </ul>
        )}
      </Disclosure>
      <Disclosure
        id="history"
        title="Research History"
        open={open}
        setOpen={setOpen}
      >
        {result.research_history.length === 0 ? (
          <p className="text-sm">No prior research records.</p>
        ) : (
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {result.research_history.map((row) => (
              <li key={String(row.research_id)}>
                {String(row.status)} — {String(row.outstanding_shares ?? "unavailable")}{" "}
                as of {String(row.as_of ?? "—")}
              </li>
            ))}
          </ul>
        )}
      </Disclosure>
      <Disclosure
        id="method"
        title="Research Method"
        open={open}
        setOpen={setOpen}
      >
        <p className="text-sm">{result.research_method}</p>
      </Disclosure>
      <Disclosure
        id="audit"
        title="Full Audit Trail"
        open={open}
        setOpen={setOpen}
      >
        <p className="text-sm">
          Identity {result.identity_check}. Corporate actions{" "}
          {result.corporate_action_check}. Cross-check {result.cross_check}.{" "}
          {result.reason}
        </p>
      </Disclosure>
    </div>
  );
}

function StatusBanner({ result }: { result: ShareResearchClientResult }) {
  if (result.status === "CURRENT" && result.valuation_eligible) {
    const through = formatDate(result.current_through);
    return (
      <Alert tone="success" title="Shares Outstanding">
        Verified{through ? ` — current through ${through}` : ""}
      </Alert>
    );
  }
  if (result.status === "REFRESH_REQUIRED") {
    return (
      <Alert tone="warning" title="Shares Outstanding">
        Verification required
        {formatDate(result.last_verified_at)
          ? `. Last verified ${formatDate(result.last_verified_at)}.`
          : "."}{" "}
        Valuation unavailable — current share-count evidence could not be verified.
      </Alert>
    );
  }
  if (result.status === "CONFLICT") {
    return (
      <Alert tone="danger" title="Shares Outstanding">
        Conflicting evidence — share count could not be determined. Valuation
        unavailable — current share-count evidence could not be verified.
      </Alert>
    );
  }
  if (result.status === "INVALID") {
    return (
      <Alert tone="danger" title="Shares Outstanding">
        Share verification could not be validated. Valuation unavailable —
        current share-count evidence could not be verified.
      </Alert>
    );
  }
  return (
    <Alert tone="warning" title="Shares Outstanding">
      Current outstanding shares could not be established. Valuation unavailable —
      current share-count evidence could not be verified.
    </Alert>
  );
}

function ValuationLine({ eligible }: { eligible: boolean }) {
  return (
    <p className="text-sm">
      {eligible
        ? "Share count accepted for valuation."
        : "Valuation unavailable — current share-count evidence could not be verified."}
    </p>
  );
}

function userFacingShareError(error: unknown): string {
  const raw =
    error instanceof ApiClientError
      ? error.message
      : error instanceof Error
        ? error.message
        : "";
  if (
    /shares_outstanding|circuitopen|circuit.?open|sharecountservice|traceback|exception/i.test(
      raw,
    )
  ) {
    return "Share verification could not be completed. Data unavailable.";
  }
  return raw || "Data unavailable.";
}

function Disclosure({
  id,
  title,
  open,
  setOpen,
  children,
}: {
  id: string;
  title: string;
  open: string | null;
  setOpen: (value: string | null) => void;
  children: ReactNode;
}) {
  const expanded = open === id;
  return (
    <div>
      <button
        type="button"
        className="text-sm underline"
        aria-expanded={expanded}
        onClick={() => setOpen(expanded ? null : id)}
      >
        {title}
      </button>
      {expanded ? <div className="mt-2">{children}</div> : null}
    </div>
  );
}

function formatShares(value: number | string | null): string {
  if (value == null || value === "") return "Data unavailable.";
  const num = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(num)) return "Data unavailable.";
  return new Intl.NumberFormat("en-IN").format(num);
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  const day = value.slice(0, 10);
  const [year, month, date] = day.split("-");
  if (!year || !month || !date) return day;
  const months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];
  return `${Number(date)} ${months[Number(month) - 1]} ${year}`;
}
