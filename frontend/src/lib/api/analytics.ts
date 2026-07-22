import { apiFetch } from "@/lib/api-client";

export type DateRange = { from?: string; to?: string };

function rangeQuery(params?: DateRange) {
  const query = new URLSearchParams();
  if (params?.from) query.set("from", params.from);
  if (params?.to) query.set("to", params.to);
  const value = query.toString();
  return value ? `?${value}` : "";
}

export type CompletionRate = {
  overall_rate?: number;
  completion_rate?: number;
  completed?: number;
  scheduled?: number;
  total_completed?: number;
  total_scheduled?: number;
  habits?: {
    habit_id?: string;
    title?: string;
    name?: string;
    completion_rate?: number;
    completed?: number;
    scheduled?: number;
  }[];
  from: string;
  to: string;
};

export type MomentumIndex = {
  momentum_7d?: number;
  momentum_30d?: number;
  momentum_90d?: number;
  seven_day?: number;
  thirty_day?: number;
  ninety_day?: number;
  [key: string]: unknown;
};

export type ConsistencyScore = {
  score?: number;
  consistency_score?: number;
  label?: string;
  [key: string]: unknown;
};

export type StreakDashboard = {
  streaks?: {
    habit_id?: string;
    title?: string;
    name?: string;
    current_streak?: number;
    longest_streak?: number;
    at_risk?: boolean;
  }[];
  [key: string]: unknown;
};

export type HeatmapPoint = {
  date: string;
  value?: number;
  completion_rate?: number;
  completed?: number;
  total?: number;
};

export type DayOfWeekBreakdown = {
  breakdown: {
    day?: string;
    weekday?: string;
    completion_rate?: number;
    rate?: number;
  }[];
  from: string;
  to: string;
};

export type WeeklyReport = {
  id: string;
  week_start: string;
  week_end: string;
  summary?: string;
  completion_rate?: number;
  momentum_index?: number;
  insights?: string[];
  created_at?: string;
};

export async function getCompletionRate(params?: DateRange) {
  return apiFetch<CompletionRate>(`/analytics/reports/completion-rate/${rangeQuery(params)}`);
}

export async function getMomentumIndex() {
  return apiFetch<MomentumIndex>("/analytics/reports/momentum/");
}

export async function getConsistencyScore() {
  return apiFetch<ConsistencyScore>("/analytics/reports/consistency-score/");
}

export async function getStreakDashboard() {
  return apiFetch<StreakDashboard>("/analytics/reports/streaks/");
}

export async function getHeatmap() {
  return apiFetch<{ heatmap: HeatmapPoint[] }>("/analytics/reports/heatmap/");
}

export async function getDayOfWeekBreakdown(params?: DateRange) {
  return apiFetch<DayOfWeekBreakdown>(`/analytics/reports/day-of-week/${rangeQuery(params)}`);
}

export async function listWeeklyReports() {
  return apiFetch<{ reports: WeeklyReport[]; count: number }>("/analytics/reports/weekly/");
}

export async function generateWeeklyReport() {
  return apiFetch<WeeklyReport>("/analytics/reports/weekly/generate/", { method: "POST" });
}
