import { describe, expect, it } from "vitest";

import type { ServerAlertRule, ServerNotification, ServerScheduledReport } from "@/lib/api/client";
import {
  mapAlertRuleView,
  mapAlertRuleViews,
  mapEvaluationResults,
  mapNotificationView,
  mapNotificationViews,
  mapScheduledReportView,
  mapScheduledReportViews,
} from "./mapWorkflowAutomation";

function rule(overrides: Partial<ServerAlertRule> = {}): ServerAlertRule {
  return {
    rule_id: "alr_1",
    user_id: "u1",
    rule_type: "price_above",
    symbol: "AAPL",
    portfolio_id: null,
    active: true,
    params: { threshold_price: 200 },
    last_evaluated_at: null,
    last_status: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("mapAlertRuleView", () => {
  it("labels the rule type and summarizes price params", () => {
    const view = mapAlertRuleView(rule());
    expect(view.ruleTypeLabel).toBe("Price above");
    expect(view.paramsSummary).toBe("Threshold 200");
    expect(view.lastStatus).toBe("Data unavailable.");
  });

  it("summarizes valuation_flip params", () => {
    const view = mapAlertRuleView(
      rule({ rule_type: "valuation_flip", params: { watch_class: "undervalued" } }),
    );
    expect(view.paramsSummary).toBe("Watching for undervalued");
  });

  it("summarizes research_stale params", () => {
    const view = mapAlertRuleView(
      rule({ rule_type: "research_stale", params: { max_age_days: 60 } }),
    );
    expect(view.paramsSummary).toBe("Stale after 60 days");
  });

  it("summarizes earnings_upcoming honestly", () => {
    const view = mapAlertRuleView(rule({ rule_type: "earnings_upcoming", params: {} }));
    expect(view.paramsSummary).toContain("No earnings-calendar data source");
  });

  it("shows last status when present", () => {
    const view = mapAlertRuleView(rule({ last_status: "triggered" }));
    expect(view.lastStatus).toBe("triggered");
  });
});

describe("mapAlertRuleViews", () => {
  it("returns empty array for null/undefined", () => {
    expect(mapAlertRuleViews(null)).toEqual([]);
    expect(mapAlertRuleViews(undefined)).toEqual([]);
  });

  it("maps every rule", () => {
    expect(mapAlertRuleViews([rule(), rule({ rule_id: "alr_2" })])).toHaveLength(2);
  });
});

describe("mapEvaluationResults", () => {
  it("is honestly empty for a null payload", () => {
    const view = mapEvaluationResults(null);
    expect(view.evaluatedCount).toBe(0);
    expect(view.results).toEqual([]);
  });

  it("maps results with rule-type labels", () => {
    const view = mapEvaluationResults({
      ok: true,
      available: true,
      message: null,
      evaluated_count: 1,
      triggered_count: 1,
      results: [
        {
          rule_id: "alr_1",
          rule_type: "price_above",
          symbol: "AAPL",
          status: "triggered",
          message: "AAPL hit $200",
          observed_value: 205,
        },
      ],
      new_notifications: [],
    });
    expect(view.triggeredCount).toBe(1);
    expect(view.results[0]?.ruleTypeLabel).toBe("Price above");
  });
});

describe("mapScheduledReportView", () => {
  function schedule(overrides: Partial<ServerScheduledReport> = {}): ServerScheduledReport {
    return {
      schedule_id: "sch_1",
      user_id: "u1",
      portfolio_id: "pf_1",
      frequency: "weekly",
      format: "json",
      active: true,
      recipients: [],
      last_run_at: null,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
      ...overrides,
    };
  }

  it("labels frequency and format", () => {
    const view = mapScheduledReportView(schedule());
    expect(view.frequencyLabel).toBe("Weekly");
    expect(view.formatLabel).toBe("JSON");
    expect(view.lastRunAt).toBe("Data unavailable.");
  });

  it("mapScheduledReportViews returns empty array for null", () => {
    expect(mapScheduledReportViews(null)).toEqual([]);
  });
});

describe("mapNotificationView", () => {
  function notification(overrides: Partial<ServerNotification> = {}): ServerNotification {
    return {
      notification_id: "ntf_1",
      user_id: "u1",
      kind: "alert",
      title: "Price alert",
      message: "AAPL hit $200",
      related_rule_id: "alr_1",
      related_schedule_id: null,
      read_at: null,
      created_at: "2024-01-01T00:00:00Z",
      ...overrides,
    };
  }

  it("marks unread when read_at is null", () => {
    const view = mapNotificationView(notification());
    expect(view.read).toBe(false);
  });

  it("marks read when read_at is set", () => {
    const view = mapNotificationView(notification({ read_at: "2024-01-02T00:00:00Z" }));
    expect(view.read).toBe(true);
  });

  it("mapNotificationViews returns empty array for null", () => {
    expect(mapNotificationViews(null)).toEqual([]);
  });
});
