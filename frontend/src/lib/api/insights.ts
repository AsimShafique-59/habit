import { apiFetch } from "@/lib/api-client";

export type InsightCategory = {
  id: string;
  name: string;
  slug: string;
  description: string;
  icon: string;
  order: number;
  is_active: boolean;
};

export type AudioInsight = {
  id: string;
  title: string;
  description: string;
  category: InsightCategory | null;
  audio_url: string | null;
  thumbnail_url: string | null;
  duration_seconds: number;
  tags: string[];
  is_published: boolean;
  published_at: string | null;
  is_saved?: boolean;
  is_favorited?: boolean;
  note?: string;
};

export async function listInsightCategories() {
  return apiFetch<InsightCategory[]>("/insights/categories/", { auth: false });
}

export async function listInsights() {
  return apiFetch<AudioInsight[]>("/insights/");
}

export async function listInsightsByCategory(slug: string) {
  return apiFetch<{ category: InsightCategory; audios: AudioInsight[] }>(
    `/insights/categories/${slug}/audios/`,
  );
}

export async function setInsightSaved(id: string, saved: boolean) {
  return apiFetch<{ insight_id: string; is_saved: boolean }>(`/insights/${id}/save/`, {
    method: saved ? "POST" : "DELETE",
  });
}

export async function setInsightFavorite(id: string, favorite: boolean) {
  return apiFetch<{ insight_id: string; is_favorited: boolean }>(
    `/insights/${id}/favorite/`,
    { method: favorite ? "POST" : "DELETE" },
  );
}

export async function saveInsightNote(id: string, note: string) {
  return apiFetch<{ insight_id: string; note: string }>(`/insights/${id}/note/`, {
    method: "PUT",
    body: { note },
  });
}
