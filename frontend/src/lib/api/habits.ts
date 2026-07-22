import { apiFetch } from "@/lib/api-client";

export type HabitCategory =
  | "Health"
  | "Fitness"
  | "Mindfulness"
  | "Productivity"
  | "Learning"
  | "Finance"
  | "Relationships"
  | "Other";

export type FrequencyType = "daily" | "weekdays" | "n_per_week";
export type Difficulty = "tiny" | "small" | "medium";

export type Habit = {
  id: string;
  user_id: string;
  title: string;
  description: string;
  category: HabitCategory;
  icon: string;
  color_hex: string;
  frequency_type: FrequencyType;
  frequency_days: number[];
  frequency_count: number;
  quantity_target: string | null;
  quantity_unit: string;
  duration_minutes: number | null;
  time_window_start: string | null;
  time_window_end: string | null;
  identity_tags: string[];
  difficulty: Difficulty;
  anchor_habit_id: string | null;
  reminder_times: string[];
  is_quit_habit: boolean;
  current_streak: number;
  longest_streak: number;
  streak_freezes_available: number;
  is_archived: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type HabitListResponse = {
  items: Habit[];
  next_cursor: string | null;
  total: number;
};

export async function listHabits(params?: { status?: "active" | "archived" | "all" }) {
  const query = params?.status ? `?status=${params.status}` : "";
  return apiFetch<HabitListResponse>(`/habits/${query}`);
}

export type HabitCreateInput = {
  title: string;
  category: HabitCategory;
  frequency_type: FrequencyType;
  description?: string;
  icon?: string;
  color_hex?: string;
  frequency_days?: number[];
  frequency_count?: number;
  quantity_target?: number | null;
  quantity_unit?: string;
  duration_minutes?: number | null;
  difficulty?: Difficulty;
  identity_tags?: string[];
  reminder_times?: string[];
  is_quit_habit?: boolean;
};

export async function createHabit(input: HabitCreateInput) {
  return apiFetch<Habit>("/habits/", { method: "POST", body: input });
}

export async function updateHabit(id: string, input: Partial<HabitCreateInput>) {
  return apiFetch<Habit>(`/habits/${id}/`, { method: "PATCH", body: input });
}

export async function deleteHabit(id: string) {
  return apiFetch<void>(`/habits/${id}/?confirm=true`, { method: "DELETE" });
}

export async function archiveHabit(id: string) {
  return apiFetch<Habit>(`/habits/${id}/archive/`, { method: "POST" });
}

export async function unarchiveHabit(id: string) {
  return apiFetch<Habit>(`/habits/${id}/unarchive/`, { method: "POST" });
}

export type CompletionResult = {
  completion_id: string;
  habit_id: string;
  completion_date: string;
  quantity: string;
  is_complete: boolean;
  current_streak: number;
  longest_streak: number;
  streak_freeze_used: boolean;
};

export async function completeHabit(
  id: string,
  input: {
    completion_date: string;
    quantity?: number;
    completed_at?: string;
    source?: "manual" | "auto_health" | "widget" | "watch" | "shortcut";
  },
) {
  return apiFetch<CompletionResult>(`/habits/${id}/completions/`, {
    method: "POST",
    body: input,
  });
}

export async function undoCompletion(habitId: string, completionId: string) {
  return apiFetch<void>(`/habits/${habitId}/completions/${completionId}/`, {
    method: "DELETE",
  });
}

export const HABIT_CATEGORIES: HabitCategory[] = [
  "Health",
  "Fitness",
  "Mindfulness",
  "Productivity",
  "Learning",
  "Finance",
  "Relationships",
  "Other",
];
