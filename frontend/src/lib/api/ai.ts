import { apiFetch } from "@/lib/api-client";
import type { Habit } from "@/lib/api/habits";

export type OnboardingQuestion = {
  id: string;
  question_type: "single_select" | "multi_select" | "scale" | "free_text";
  prompt: string;
  options: string[];
  max_selections: number;
  order: number;
  is_progressive: boolean;
};

export type HabitSuggestion = {
  suggestion_id: string;
  title: string;
  description: string;
  category: string;
  frequency_type: string;
  quantity_target: number | null;
  duration_minutes: number | null;
  difficulty: "tiny" | "small" | "medium";
  rationale: string;
  mode: "starter" | "expanded";
  is_accepted: boolean;
  is_dismissed: boolean;
  created_at: string;
};

export type CoachingProposal = {
  proposal_id?: string;
  proposal_type?: string;
  habit_id?: string;
  title?: string;
  explanation?: string;
  proposed_changes?: Record<string, unknown>;
};

export type CoachingReview = {
  review_id: string;
  proposals: CoachingProposal[];
  status: "pending" | "responded";
  created_at: string;
  responded_at: string | null;
};

export async function getOnboardingQuestions() {
  return apiFetch<{ questions: OnboardingQuestion[]; onboarding_completed: boolean }>(
    "/ai/onboarding/questions/",
  );
}

export async function submitOnboardingAnswers(answers: Record<string, unknown>) {
  return apiFetch<{ onboarding_completed: boolean; archetype_hash: string }>(
    "/ai/onboarding/answers/",
    { method: "POST", body: { answers } },
  );
}

export async function generateHabitSuggestions(mode: "starter" | "expanded") {
  return apiFetch<{ suggestions: HabitSuggestion[]; mode: string; from_cache: boolean }>(
    "/ai/habits/generate/",
    { method: "POST", body: { mode } },
  );
}

export async function acceptHabitSuggestions(suggestionIds: string[]) {
  return apiFetch<{ created_habits: { habit_id: string; suggestion_id: string }[] }>(
    "/ai/habits/accept/",
    { method: "POST", body: { suggestion_ids: suggestionIds } },
  );
}

export async function proposeHabitModification(habitId: string, instruction: string) {
  return apiFetch<{
    proposed_changes: Partial<Habit>;
    explanation: string;
    modification_id: string;
  }>(`/habits/${habitId}/modify-nl/`, {
    method: "POST",
    body: { instruction },
  });
}

export async function getLatestCoachingReview() {
  return apiFetch<CoachingReview>("/ai/coaching/reviews/latest/");
}

export async function triggerCoachingReview() {
  return apiFetch<Pick<CoachingReview, "review_id" | "proposals">>(
    "/ai/coaching/reviews/trigger/",
    { method: "POST", body: {} },
  );
}

export async function respondToCoachingReview(
  reviewId: string,
  decisions: {
    proposal_id: string;
    action: "accept" | "modify" | "dismiss";
    modification?: Record<string, unknown>;
  }[],
) {
  return apiFetch<{
    applied: { proposal_id: string; action: string; habit_id?: string }[];
    skipped: { proposal_id: string; reason: string }[];
  }>(`/ai/coaching/reviews/${reviewId}/respond/`, {
    method: "POST",
    body: { decisions },
  });
}
