import { apiFetch } from "@/lib/api-client";

export type SubscriptionPlan = {
  id: string;
  name: string;
  slug: string;
  tier: "free" | "premium";
  description: string;
  price_usd: string;
  duration_days: number;
  apple_product_id: string;
  google_product_id: string;
  features: string[];
  is_featured: boolean;
};

export type UserSubscription = {
  id: string;
  plan: SubscriptionPlan | null;
  tier: "free" | "premium";
  provider: "apple" | "google" | "manual";
  status: "active" | "expired" | "cancelled" | "pending";
  started_at: string | null;
  expires_at: string | null;
  auto_renew: boolean;
  cancelled_at: string | null;
};

export async function listSubscriptionPlans() {
  return apiFetch<SubscriptionPlan[]>("/subscriptions/plans/", { auth: false });
}

export async function getMySubscription() {
  return apiFetch<UserSubscription>("/subscriptions/me/");
}

export async function cancelSubscription() {
  return apiFetch<UserSubscription>("/subscriptions/cancel/", { method: "POST" });
}
