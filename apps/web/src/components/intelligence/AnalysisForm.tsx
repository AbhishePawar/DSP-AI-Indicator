"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import type { AnalyseRequest } from "@/lib/api/compositionTypes";
import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";

export function AnalysisForm({
  initial,
  busy,
  onValidate,
  onAnalyse,
}: {
  initial?: AnalyseRequest;
  busy?: boolean;
  onValidate: (request: AnalyseRequest) => void;
  onAnalyse: (request: AnalyseRequest) => void;
}) {
  const seed = initial ?? SAMPLE_ANALYSE_REQUEST;
  const [ticker, setTicker] = useState(seed.ticker);
  const [exchange, setExchange] = useState(seed.exchange ?? "");
  const [company, setCompany] = useState(seed.company ?? "");
  const [intrinsic, setIntrinsic] = useState(
    String(seed.valuation_signals?.intrinsic_value_per_share ?? ""),
  );
  const [price, setPrice] = useState(
    String(seed.valuation_signals?.current_market_price ?? ""),
  );
  const [confidence, setConfidence] = useState(
    String(seed.valuation_signals?.confidence ?? 0.7),
  );
  const [statementsJson, setStatementsJson] = useState(
    JSON.stringify(seed.financial_statements, null, 2),
  );
  const [jsonError, setJsonError] = useState<string | null>(null);

  function buildRequest(): AnalyseRequest | null {
    try {
      const financial_statements = JSON.parse(
        statementsJson,
      ) as AnalyseRequest["financial_statements"];
      setJsonError(null);
      const iv = intrinsic.trim() === "" ? null : Number(intrinsic);
      const px = price.trim() === "" ? null : Number(price);
      const conf = confidence.trim() === "" ? 0.55 : Number(confidence);
      return {
        ticker: ticker.trim().toUpperCase(),
        exchange: exchange.trim() || null,
        company: company.trim(),
        financial_statements,
        valuation_signals: {
          intrinsic_value_per_share: Number.isFinite(iv as number) ? iv : null,
          current_market_price: Number.isFinite(px as number) ? px : null,
          confidence: Number.isFinite(conf) ? conf : 0.55,
        },
        current_market_price: Number.isFinite(px as number) ? px : null,
      };
    } catch {
      setJsonError("Financial statements JSON is invalid");
      return null;
    }
  }

  function handleValidate() {
    const req = buildRequest();
    if (req) onValidate(req);
  }

  function handleAnalyse() {
    const req = buildRequest();
    if (req) onAnalyse(req);
  }

  function loadSample() {
    const sample = SAMPLE_ANALYSE_REQUEST;
    setTicker(sample.ticker);
    setExchange(sample.exchange ?? "");
    setCompany(sample.company ?? "");
    setIntrinsic(
      String(sample.valuation_signals?.intrinsic_value_per_share ?? ""),
    );
    setPrice(String(sample.valuation_signals?.current_market_price ?? ""));
    setConfidence(String(sample.valuation_signals?.confidence ?? 0.7));
    setStatementsJson(JSON.stringify(sample.financial_statements, null, 2));
    setJsonError(null);
  }

  return (
    <Card>
      <CardHeader
        title="Analysis Input"
        description="Submit JSON financial statements and valuation signals to /api/v1"
        action={
          <Button type="button" variant="ghost" size="sm" onClick={loadSample}>
            Load sample
          </Button>
        }
      />
      <CardBody>
        <form className="space-y-4" aria-label="Intelligence analysis form">
          <div className="grid gap-4 md:grid-cols-3">
            <label className="text-sm">
              <span className="text-[var(--muted)]">Ticker</span>
              <Input
                className="mt-1 min-h-11"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                required
                autoComplete="off"
                aria-required
              />
            </label>
            <label className="text-sm">
              <span className="text-[var(--muted)]">Exchange</span>
              <Input
                className="mt-1 min-h-11"
                value={exchange}
                onChange={(e) => setExchange(e.target.value)}
                autoComplete="off"
              />
            </label>
            <label className="text-sm">
              <span className="text-[var(--muted)]">Company</span>
              <Input
                className="mt-1 min-h-11"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
              />
            </label>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <label className="text-sm">
              <span className="text-[var(--muted)]">Intrinsic value / share</span>
              <Input
                className="mt-1 min-h-11"
                inputMode="decimal"
                value={intrinsic}
                onChange={(e) => setIntrinsic(e.target.value)}
              />
            </label>
            <label className="text-sm">
              <span className="text-[var(--muted)]">Market price</span>
              <Input
                className="mt-1 min-h-11"
                inputMode="decimal"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
              />
            </label>
            <label className="text-sm">
              <span className="text-[var(--muted)]">Valuation confidence</span>
              <Input
                className="mt-1 min-h-11"
                inputMode="decimal"
                value={confidence}
                onChange={(e) => setConfidence(e.target.value)}
              />
            </label>
          </div>

          <label className="block text-sm">
            <span className="text-[var(--muted)]">Financial statements (JSON)</span>
            <textarea
              className="mt-1 min-h-48 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2 font-mono text-xs leading-relaxed text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              value={statementsJson}
              onChange={(e) => setStatementsJson(e.target.value)}
              spellCheck={false}
              aria-invalid={Boolean(jsonError)}
              aria-describedby={jsonError ? "statements-json-error" : undefined}
            />
          </label>
          {jsonError ? (
            <p
              id="statements-json-error"
              className="text-sm text-[var(--danger-fg)]"
              role="alert"
            >
              {jsonError}
            </p>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={busy}
              onClick={handleValidate}
            >
              Validate
            </Button>
            <Button type="button" disabled={busy} onClick={handleAnalyse}>
              {busy ? "Running…" : "Run analyse"}
            </Button>
          </div>
        </form>
      </CardBody>
    </Card>
  );
}
