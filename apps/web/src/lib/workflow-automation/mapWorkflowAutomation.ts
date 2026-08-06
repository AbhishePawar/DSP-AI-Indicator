/**
 * Presentation mapper for Workflow Automation (RC1 Milestone 5,
 * /api/v1/workflow-automation/*). Display only — every alert
 * evaluation/schedule/notification value is computed or stored
 * server-side; the client never evaluates a rule or computes a schedule
 * outcome itself.
 */

import type {
  AlertEvaluationResult,
  AlertRuleType,
  EvaluateAlertsPayload,
  ServerAlertRule,
  ServerNotification,
  ServerScheduledReport,
} from "@/lib/api/client";

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Data unavailable.";
  }
  return String(value);
}

export const ALERT_RULE_TYPE_LABELS: Record<AlertRuleType, string> = {
  price_above: "Price above",
  price_below: "Price below",
  valuation_flip: "Valuation change",
  research_stale: "Research refresh",
  earnings_upcoming: "Earnings (coming soon)",
};

export type AlertRuleView = {
  ruleId: string;
  ruleType: AlertRuleType;
  ruleTypeLabel: string;
  symbol: string;
  portfolioId: string | null;
  active: boolean;
  paramsSummary: string;
  lastStatus: string;
  lastEvaluatedAt: string;
  createdAt: string;
};

function summarizeParams(rule: ServerAlertRule): string {
  const params = rule.params || {};
  switch (rule.rule_type) {
    case "price_above":
    case "price_below":
      return typeof params.threshold_price === "number"
        ? `Threshold ${params.threshold_price}`
        : "Data unavailable.";
    case "valuation_flip":
      return typeof params.watch_class === "string"
        ? `Watching for ${String(params.watch_class).replace("_", " ")}`
        : "Watching for overvalued";
    case "research_stale":
      return typeof params.max_age_days === "number"
        ? `Stale after ${params.max_age_days} days`
        : "Data unavailable.";
    case "earnings_upcoming":
      return "No earnings-calendar data source connected";
    default:
      return "Data unavailable.";
  }
}

export function mapAlertRuleView(rule: ServerAlertRule): AlertRuleView {
  return {
    ruleId: rule.rule_id,
    ruleType: rule.rule_type,
    ruleTypeLabel: ALERT_RULE_TYPE_LABELS[rule.rule_type] ?? rule.rule_type,
    symbol: display(rule.symbol),
    portfolioId: rule.portfolio_id,
    active: rule.active,
    paramsSummary: summarizeParams(rule),
    lastStatus: display(rule.last_status),
    lastEvaluatedAt: display(rule.last_evaluated_at),
    createdAt: display(rule.created_at),
  };
}

export function mapAlertRuleViews(rules: ServerAlertRule[] | null | undefined): AlertRuleView[] {
  return (rules ?? []).map(mapAlertRuleView);
}

export type AlertEvaluationView = {
  ruleId: string;
  ruleTypeLabel: string;
  symbol: string;
  status: "triggered" | "not_triggered" | "unavailable";
  message: string;
};

export function mapEvaluationResults(
  payload: EvaluateAlertsPayload | null | undefined,
): { evaluatedCount: number; triggeredCount: number; results: AlertEvaluationView[] } {
  const results = (payload?.results ?? []).map((r: AlertEvaluationResult) => ({
    ruleId: r.rule_id,
    ruleTypeLabel: ALERT_RULE_TYPE_LABELS[r.rule_type] ?? r.rule_type,
    symbol: display(r.symbol),
    status: r.status,
    message: r.message,
  }));
  return {
    evaluatedCount: payload?.evaluated_count ?? 0,
    triggeredCount: payload?.triggered_count ?? 0,
    results,
  };
}

export type ScheduledReportView = {
  scheduleId: string;
  portfolioId: string;
  frequencyLabel: string;
  formatLabel: string;
  active: boolean;
  lastRunAt: string;
  recipients: string[];
};

const FREQUENCY_LABELS: Record<string, string> = {
  daily: "Daily",
  weekly: "Weekly",
  monthly: "Monthly",
};

export function mapScheduledReportView(schedule: ServerScheduledReport): ScheduledReportView {
  return {
    scheduleId: schedule.schedule_id,
    portfolioId: schedule.portfolio_id,
    frequencyLabel: FREQUENCY_LABELS[schedule.frequency] ?? schedule.frequency,
    formatLabel: schedule.format.toUpperCase(),
    active: schedule.active,
    lastRunAt: display(schedule.last_run_at),
    recipients: schedule.recipients ?? [],
  };
}

export function mapScheduledReportViews(
  schedules: ServerScheduledReport[] | null | undefined,
): ScheduledReportView[] {
  return (schedules ?? []).map(mapScheduledReportView);
}

export type NotificationView = {
  notificationId: string;
  kind: string;
  title: string;
  message: string;
  createdAt: string;
  read: boolean;
};

export function mapNotificationView(notification: ServerNotification): NotificationView {
  return {
    notificationId: notification.notification_id,
    kind: notification.kind,
    title: notification.title,
    message: notification.message,
    createdAt: display(notification.created_at),
    read: notification.read_at !== null,
  };
}

export function mapNotificationViews(
  notifications: ServerNotification[] | null | undefined,
): NotificationView[] {
  return (notifications ?? []).map(mapNotificationView);
}
