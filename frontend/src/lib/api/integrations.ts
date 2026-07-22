import { apiFetch } from "@/lib/api-client";

export type IntegrationType =
  | "apple_health"
  | "google_fit"
  | "apple_calendar"
  | "google_calendar";

export type IntegrationConsent = {
  id: string | null;
  integration_type: IntegrationType;
  is_enabled: boolean;
  granted_at: string | null;
  revoked_at: string | null;
  data_categories: string[];
  created_at: string | null;
  updated_at: string | null;
};

export type WidgetSnapshot = {
  id: string;
  habits_today: { habit_id: string; name: string; completed: boolean }[];
  streak_count: number;
  momentum_index_7d: number;
  updated_at: string;
};

export type HealthDataPoint = {
  id: string;
  source: "apple_health" | "google_fit";
  metric:
    | "steps"
    | "sleep_minutes"
    | "workout_minutes"
    | "mindful_minutes"
    | "water_ml"
    | "weight_kg";
  value: number;
  recorded_date: string;
  recorded_at: string;
};

export async function listIntegrations() {
  return apiFetch<{ integrations: IntegrationConsent[] }>("/integrations/");
}

export async function updateIntegrationConsent(
  integrationType: IntegrationType,
  input: { is_enabled: boolean; data_categories: string[] },
) {
  return apiFetch<IntegrationConsent>(`/integrations/${integrationType}/consent/`, {
    method: "POST",
    body: input,
  });
}

export async function getWidgetSnapshot() {
  return apiFetch<WidgetSnapshot>("/integrations/widget/snapshot/");
}

export async function refreshWidgetSnapshot() {
  return apiFetch<WidgetSnapshot>("/integrations/widget/refresh/", { method: "POST" });
}

export async function listHealthData(params?: {
  metric?: HealthDataPoint["metric"];
  from?: string;
  to?: string;
}) {
  const query = new URLSearchParams();
  if (params?.metric) query.set("metric", params.metric);
  if (params?.from) query.set("from", params.from);
  if (params?.to) query.set("to", params.to);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiFetch<{ items: HealthDataPoint[] }>(`/integrations/health/${suffix}`);
}

export async function getNotificationSuppression() {
  return apiFetch<{ suppressed: boolean; reason: string | null }>(
    "/integrations/calendar/suppress-now/",
  );
}
