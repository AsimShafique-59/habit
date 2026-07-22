import { apiFetch } from "@/lib/api-client";
import type { AudioInsight } from "@/lib/api/insights";

export type BadHabitProgram = {
  id: string;
  name: string;
  slug: string;
  description: string;
  habit_type: string;
  program_length_days: number;
  has_medical_risk: boolean;
  crisis_resource_url: string;
  savings_unit: string;
  savings_per_day: number;
  savings_money_per_unit: string;
  calories_per_unit: number;
  is_active: boolean;
  order: number;
  created_at: string;
  updated_at: string;
};

export type ProgramDay = {
  id: string;
  program?: string;
  day_number: number;
  title: string;
  task_description: string;
  reflection_prompt: string;
  audio?: string | null;
  audio_detail?: AudioInsight | null;
};

export type UserEnrollment = {
  id: string;
  program: BadHabitProgram;
  status: "enrolled" | "completed" | "abandoned";
  enrolled_at: string;
  started_at: string;
  completed_at: string | null;
  last_slip_at: string | null;
  slip_count: number;
  replacement_habit_id: string | null;
  triggers_captured: boolean;
  current_day: number;
  days_since_last_slip: number;
  savings: {
    units_saved: number;
    money_saved: number;
    calories_saved: number;
    unit_label: string;
  };
};

export type QuitReason = {
  id: string;
  text: string;
  order: number;
  created_at: string;
};

export async function listPrograms() {
  return apiFetch<BadHabitProgram[]>("/motivation/programs/", { auth: false });
}

export async function listEnrollments() {
  return apiFetch<UserEnrollment[]>("/motivation/enrollments/");
}

export async function enrollInProgram(programSlug: string) {
  return apiFetch<UserEnrollment>("/motivation/enroll/", {
    method: "POST",
    body: { program_slug: programSlug },
  });
}

export async function getTodayProgramDay(enrollmentId: string) {
  return apiFetch<ProgramDay>(`/motivation/enrollments/${enrollmentId}/today/`);
}

export async function completeProgramDay(enrollmentId: string, reflection_response: string) {
  return apiFetch<unknown>(`/motivation/enrollments/${enrollmentId}/complete-day/`, {
    method: "POST",
    body: { reflection_response },
  });
}

export async function logSlip(enrollmentId: string) {
  return apiFetch<{
    days_since_last_slip: number;
    slip_count: number;
    encouragement: string;
  }>(`/motivation/enrollments/${enrollmentId}/slip/`, { method: "POST" });
}

export async function activateSos(enrollmentId: string) {
  return apiFetch<{
    sos_id: string;
    quit_reasons: QuitReason[];
    urge_surfing_audio_url: string | null;
    breathing_exercise: {
      duration_seconds: number;
      pattern: string;
      instructions: string;
    };
  }>(`/motivation/enrollments/${enrollmentId}/sos/`, { method: "POST" });
}

export async function listQuitReasons(enrollmentId: string) {
  return apiFetch<QuitReason[]>(`/motivation/enrollments/${enrollmentId}/reasons/`);
}

export async function addQuitReason(enrollmentId: string, text: string) {
  return apiFetch<QuitReason>(`/motivation/enrollments/${enrollmentId}/reasons/`, {
    method: "POST",
    body: { text },
  });
}
