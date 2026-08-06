"use client";

/**
 * Alert Rules panel (RC1 Milestone 5) — presentation + form only. Every
 * evaluation outcome comes from POST /workflow-automation/alerts/evaluate;
 * this component never evaluates a rule itself.
 */

import { useState } from "react";

import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Skeleton,
} from "@/components/ds";
import type { AlertRuleType } from "@/lib/api/client";
import {
  ALERT_RULE_TYPE_LABELS,
  mapAlertRuleViews,
  mapEvaluationResults,
} from "@/lib/workflow-automation/mapWorkflowAutomation";
import { useAlertRules, useEvaluateAlerts } from "@/lib/workflow-automation/useWorkflowAutomation";

const STATUS_BADGE: Record<string, "accent" | "outline" | "danger"> = {
  triggered: "danger",
  not_triggered: "accent",
  unavailable: "outline",
};

export function AlertRulesPanel({
  token,
  defaultPortfolioId,
}: {
  token: string | null | undefined;
  defaultPortfolioId?: string | null;
}) {
  const { rules, isLoading, createRule, updateRule, deleteRule } = useAlertRules(token);
  const evaluateAlerts = useEvaluateAlerts(token);

  const [ruleType, setRuleType] = useState<AlertRuleType>("price_above");
  const [symbol, setSymbol] = useState("");
  const [thresholdPrice, setThresholdPrice] = useState("");
  const [watchClass, setWatchClass] = useState("overvalued");
  const [maxAgeDays, setMaxAgeDays] = useState("90");

  function buildParams(): Record<string, unknown> {
    switch (ruleType) {
      case "price_above":
      case "price_below":
        return { threshold_price: parseFloat(thresholdPrice) || 0 };
      case "valuation_flip":
        return { watch_class: watchClass };
      case "research_stale":
        return { max_age_days: parseInt(maxAgeDays, 10) || 90 };
      default:
        return {};
    }
  }

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!symbol.trim()) return;
    createRule.mutate({
      rule_type: ruleType,
      symbol: symbol.trim().toUpperCase(),
      portfolio_id: ruleType === "valuation_flip" ? defaultPortfolioId : null,
      params: buildParams(),
    });
    setSymbol("");
  }

  const views = mapAlertRuleViews(rules);
  const evaluation = mapEvaluationResults(evaluateAlerts.data);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Create Alert Rule</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-wrap items-end gap-3" onSubmit={handleCreate}>
            <div>
              <label className="mb-1 block text-xs text-[var(--muted)]" htmlFor="rule-type">
                Type
              </label>
              <Select value={ruleType} onValueChange={(v) => setRuleType(v as AlertRuleType)}>
                <SelectTrigger id="rule-type" className="w-56">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(ALERT_RULE_TYPE_LABELS) as AlertRuleType[]).map((t) => (
                    <SelectItem key={t} value={t}>
                      {ALERT_RULE_TYPE_LABELS[t]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-[var(--muted)]" htmlFor="rule-symbol">
                Symbol
              </label>
              <Input
                id="rule-symbol"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder="AAPL"
                className="w-32"
              />
            </div>
            {(ruleType === "price_above" || ruleType === "price_below") && (
              <div>
                <label className="mb-1 block text-xs text-[var(--muted)]" htmlFor="rule-threshold">
                  Threshold price
                </label>
                <Input
                  id="rule-threshold"
                  type="number"
                  value={thresholdPrice}
                  onChange={(e) => setThresholdPrice(e.target.value)}
                  className="w-32"
                />
              </div>
            )}
            {ruleType === "valuation_flip" && (
              <div>
                <label className="mb-1 block text-xs text-[var(--muted)]" htmlFor="rule-watch-class">
                  Watch for
                </label>
                <Select value={watchClass} onValueChange={setWatchClass}>
                  <SelectTrigger id="rule-watch-class" className="w-44">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="overvalued">Overvalued</SelectItem>
                    <SelectItem value="undervalued">Undervalued</SelectItem>
                    <SelectItem value="fairly_valued">Fairly valued</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
            {ruleType === "research_stale" && (
              <div>
                <label className="mb-1 block text-xs text-[var(--muted)]" htmlFor="rule-max-age">
                  Stale after (days)
                </label>
                <Input
                  id="rule-max-age"
                  type="number"
                  value={maxAgeDays}
                  onChange={(e) => setMaxAgeDays(e.target.value)}
                  className="w-32"
                />
              </div>
            )}
            <Button type="submit" disabled={createRule.isPending}>
              Add rule
            </Button>
          </form>
          {ruleType === "earnings_upcoming" ? (
            <p className="mt-2 text-xs text-[var(--muted)]">
              Data unavailable. No earnings-calendar data source is connected yet — this rule
              type is reserved for a future Data Connector Framework provider.
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base">Your Alert Rules</CardTitle>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => evaluateAlerts.mutate(null)}
            disabled={evaluateAlerts.isPending}
          >
            Check now
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : views.length === 0 ? (
            <EmptyState title="No alert rules yet" description="Create one above." />
          ) : (
            <ul className="space-y-2" aria-label="Alert rules">
              {views.map((rule) => (
                <li
                  key={rule.ruleId}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border)] p-3"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-medium">{rule.symbol}</span>
                      <Badge variant="outline">{rule.ruleTypeLabel}</Badge>
                      {!rule.active ? <Badge variant="outline">Paused</Badge> : null}
                      {rule.lastStatus !== "Data unavailable." ? (
                        <Badge variant={STATUS_BADGE[rule.lastStatus] ?? "outline"}>
                          {rule.lastStatus.replace("_", " ")}
                        </Badge>
                      ) : null}
                    </div>
                    <p className="mt-1 text-xs text-[var(--muted)]">{rule.paramsSummary}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => updateRule.mutate({ ruleId: rule.ruleId, active: !rule.active })}
                    >
                      {rule.active ? "Pause" : "Resume"}
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => deleteRule.mutate(rule.ruleId)}>
                      Delete
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {evaluateAlerts.data ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Last check: {evaluation.triggeredCount} of {evaluation.evaluatedCount} triggered
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm" aria-label="Evaluation results">
              {evaluation.results.map((r) => (
                <li key={r.ruleId} className="flex items-center gap-2">
                  <Badge variant={STATUS_BADGE[r.status] ?? "outline"}>{r.status}</Badge>
                  <span className="font-mono">{r.symbol}</span>
                  <span className="text-[var(--muted)]">{r.message}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
