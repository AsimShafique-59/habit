import { apiFetch } from "@/lib/api-client";
import { clearTokens, setTokens } from "@/lib/auth-storage";

export type User = {
  id: string;
  email: string;
  name: string;
  locale: string;
  timezone: string;
  email_verified: boolean;
  subscription_tier: "free" | "premium";
  identity_tags?: string[];
  notification_quiet_hours?: { start: string; end: string } | null;
  theme_preference?: "light" | "dark" | "system";
  date_joined?: string;
};

type Tokens = { access: string; refresh: string };

function browserLocale() {
  if (typeof navigator === "undefined") return "en-US";
  return navigator.language || "en-US";
}

function browserTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

export type SignupInput = {
  email: string;
  password: string;
  name: string;
  accepted_tos_version?: string;
};

export async function signup(input: SignupInput) {
  const data = await apiFetch<{ user: User; tokens: Tokens; email_verified: boolean }>(
    "/auth/signup/",
    {
      method: "POST",
      auth: false,
      body: {
        ...input,
        accepted_tos_version: input.accepted_tos_version ?? "1.0",
        locale: browserLocale(),
        timezone: browserTimezone(),
      },
    },
  );
  setTokens(data.tokens.access, data.tokens.refresh);
  return data;
}

export type LoginInput = { email: string; password: string };

export async function login(input: LoginInput) {
  const data = await apiFetch<{ user: User; tokens: Tokens }>("/auth/login/", {
    method: "POST",
    auth: false,
    body: input,
  });
  setTokens(data.tokens.access, data.tokens.refresh);
  return data;
}

export async function getProfile() {
  return apiFetch<User>("/auth/users/me/");
}

export async function updateProfile(input: Partial<User>) {
  return apiFetch<User>("/auth/users/me/", { method: "PATCH", body: input });
}

export function logout() {
  clearTokens();
}

export async function requestPasswordReset(email: string) {
  return apiFetch<void>("/auth/password-reset/request/", {
    method: "POST",
    auth: false,
    body: { email },
  });
}
