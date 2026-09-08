/**
 * Research History Service — Supabase-backed CRUD for /research/history.
 */

import { createClient } from "@/lib/supabase/client";

export interface ResearchHistoryEntry {
  id: string;
  userId: string;
  ticker: string;
  company: string;
  exchange: string;
  recommendation: string;
  analysedAt: string;
  savedAt: string;
  label?: string | null;
  keyFindings?: string | null;
  request?: Record<string, unknown> | null;
  response?: Record<string, unknown> | null;
}

function toEntry(row: Record<string, unknown>): ResearchHistoryEntry {
  return {
    id: row.id as string,
    userId: row.user_id as string,
    ticker: row.ticker as string,
    company: row.company as string,
    exchange: row.exchange as string,
    recommendation: row.recommendation as string,
    analysedAt: row.analysed_at as string,
    savedAt: row.saved_at as string,
    label: row.label as string | null,
    keyFindings: row.key_findings as string | null,
    request: row.request as Record<string, unknown> | null,
    response: row.response as Record<string, unknown> | null,
  };
}

export async function fetchResearchHistory(): Promise<ResearchHistoryEntry[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from("research_history")
    .select("*")
    .order("saved_at", { ascending: false });

  if (error) throw new Error(error.message);
  return (data ?? []).map(toEntry);
}

export async function saveResearchHistory(
  entry: Omit<ResearchHistoryEntry, "id" | "userId">,
  userId: string,
): Promise<ResearchHistoryEntry> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from("research_history")
    .insert({
      user_id: userId,
      ticker: entry.ticker,
      company: entry.company,
      exchange: entry.exchange,
      recommendation: entry.recommendation,
      analysed_at: entry.analysedAt,
      saved_at: entry.savedAt,
      label: entry.label ?? null,
      key_findings: entry.keyFindings ?? null,
      request: entry.request ?? null,
      response: entry.response ?? null,
    })
    .select()
    .single();

  if (error) throw new Error(error.message);
  return toEntry(data as Record<string, unknown>);
}

export async function deleteResearchHistory(id: string): Promise<void> {
  const supabase = createClient();
  const { error } = await supabase
    .from("research_history")
    .delete()
    .eq("id", id);

  if (error) throw new Error(error.message);
}
