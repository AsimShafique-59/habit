import { apiFetch } from "@/lib/api-client";

export type ReflectionPrompt = {
  id: string;
  text: string;
  date: string;
  is_active: boolean;
};

export type MoodLog = {
  id: string;
  score: number;
  emoji_label: string;
  note: string;
  logged_at: string;
  date: string;
};

export type MoodSummary = {
  average_score: number;
  total_logs: number;
  by_score: Record<string, number>;
  streak_days: number;
};

export type JournalEntry = {
  id: string;
  prompt: ReflectionPrompt | null;
  text: string;
  mood: MoodLog | null;
  habits: { id: string; title: string }[];
  entry_date: string;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
};

function rangeQuery(params?: { from?: string; to?: string }) {
  const query = new URLSearchParams();
  if (params?.from) query.set("from", params.from);
  if (params?.to) query.set("to", params.to);
  const value = query.toString();
  return value ? `?${value}` : "";
}

export async function getTodayPrompt() {
  return apiFetch<{ prompt: ReflectionPrompt | null }>("/reflection/prompt/today/");
}

export async function listMoodLogs(params?: { from?: string; to?: string }) {
  return apiFetch<MoodLog[]>(`/reflection/mood/${rangeQuery(params)}`);
}

export async function logMood(input: { score: number; note?: string }) {
  return apiFetch<MoodLog>("/reflection/mood/", { method: "POST", body: input });
}

export async function getMoodSummary() {
  return apiFetch<MoodSummary>("/reflection/mood/summary/");
}

export async function listJournalEntries(params?: { from?: string; to?: string }) {
  return apiFetch<JournalEntry[]>(`/reflection/journal/${rangeQuery(params)}`);
}

export async function createJournalEntry(input: {
  text: string;
  prompt_id?: string | null;
  mood_id?: string | null;
  habit_ids?: string[];
  entry_date?: string;
}) {
  return apiFetch<JournalEntry>("/reflection/journal/", { method: "POST", body: input });
}
