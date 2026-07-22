import { apiFetch } from "@/lib/api-client";

export type WidgetSnapshot = {
  id: string;
  habits_today: { habit_id: string; name: string; completed: boolean }[];
  streak_count: number;
  momentum_index_7d: number;
  updated_at: string;
};

export async function getWidgetSnapshot() {
  return apiFetch<WidgetSnapshot>("/integrations/widget/snapshot/");
}
