"use client";

/**
 * Workflow Automation (RC1 Milestone 5) — data-fetching + mutation hooks.
 * Wraps the authenticated /api/v1/workflow-automation/* endpoints behind
 * react-query. No client-side evaluation — every alert/schedule outcome is
 * server-computed.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  api,
  type AlertRuleType,
  type ServerAlertRule,
  type ServerNotification,
  type ServerScheduledReport,
} from "@/lib/api/client";

export function useAlertRules(token: string | null | undefined) {
  const queryClient = useQueryClient();
  const enabled = Boolean(token);

  const query = useQuery({
    queryKey: ["workflow-automation-alerts", token ?? "anon"],
    queryFn: () => api.alertRuleList(undefined, { token }),
    enabled,
    staleTime: 30_000,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["workflow-automation-alerts"] });

  const createRule = useMutation({
    mutationFn: (body: {
      rule_type: AlertRuleType;
      symbol?: string | null;
      portfolio_id?: string | null;
      params?: Record<string, unknown> | null;
    }) => api.alertRuleCreate(body, { token }),
    onSuccess: invalidate,
  });

  const updateRule = useMutation({
    mutationFn: (input: { ruleId: string; active?: boolean; params?: Record<string, unknown> }) =>
      api.alertRuleUpdate(input.ruleId, { active: input.active, params: input.params }, { token }),
    onSuccess: invalidate,
  });

  const deleteRule = useMutation({
    mutationFn: (ruleId: string) => api.alertRuleDelete(ruleId, { token }),
    onSuccess: invalidate,
  });

  return {
    rules: (query.data?.rules ?? []) as ServerAlertRule[],
    isLoading: query.isLoading,
    error: query.error,
    createRule,
    updateRule,
    deleteRule,
  };
}

export function useEvaluateAlerts(token: string | null | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (researchObjects?: Record<string, unknown> | null) =>
      api.alertRuleEvaluate({ research_objects: researchObjects ?? null }, { token }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["workflow-automation-alerts"] });
      void queryClient.invalidateQueries({ queryKey: ["workflow-automation-notifications"] });
    },
  });
}

export function useScheduledReports(token: string | null | undefined) {
  const queryClient = useQueryClient();
  const enabled = Boolean(token);

  const query = useQuery({
    queryKey: ["workflow-automation-schedules", token ?? "anon"],
    queryFn: () => api.scheduledReportList({ token }),
    enabled,
    staleTime: 30_000,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["workflow-automation-schedules"] });

  const createSchedule = useMutation({
    mutationFn: (body: {
      portfolio_id: string;
      frequency: "daily" | "weekly" | "monthly";
      format?: "json" | "csv";
    }) => api.scheduledReportCreate(body, { token }),
    onSuccess: invalidate,
  });

  const deleteSchedule = useMutation({
    mutationFn: (scheduleId: string) => api.scheduledReportDelete(scheduleId, { token }),
    onSuccess: invalidate,
  });

  const runNow = useMutation({
    mutationFn: (scheduleId: string) =>
      api.scheduledReportRunNow(scheduleId, { research_objects: null }, { token }),
    onSuccess: invalidate,
  });

  return {
    schedules: (query.data?.schedules ?? []) as ServerScheduledReport[],
    isLoading: query.isLoading,
    error: query.error,
    createSchedule,
    deleteSchedule,
    runNow,
  };
}

export function useNotifications(token: string | null | undefined) {
  const queryClient = useQueryClient();
  const enabled = Boolean(token);

  const query = useQuery({
    queryKey: ["workflow-automation-notifications", token ?? "anon"],
    queryFn: () => api.notificationList(undefined, { token }),
    enabled,
    staleTime: 15_000,
  });

  const markRead = useMutation({
    mutationFn: (notificationId: string) => api.notificationMarkRead(notificationId, { token }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["workflow-automation-notifications"] }),
  });

  return {
    notifications: (query.data?.notifications ?? []) as ServerNotification[],
    isLoading: query.isLoading,
    error: query.error,
    markRead,
  };
}
