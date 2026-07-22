import { apiFetch } from "@/lib/api-client";

export type NotificationItem = {
  id: string;
  title: string;
  body: string;
  notification_type: string;
  data: Record<string, unknown>;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
};

export type DeviceToken = {
  id: string;
  token: string;
  platform: "ios" | "android";
  is_active: boolean;
  created_at: string;
};

export async function listNotifications(params?: { unread?: boolean }) {
  const query = params?.unread ? "?unread=true" : "";
  return apiFetch<{ items: NotificationItem[]; unread_count: number }>(
    `/notifications/${query}`,
  );
}

export async function markNotificationRead(id: string) {
  return apiFetch<NotificationItem>(`/notifications/${id}/read/`, { method: "PATCH" });
}

export async function markAllNotificationsRead() {
  return apiFetch<void>("/notifications/mark-all-read/", { method: "POST" });
}

export async function registerDeviceToken(input: { token: string; platform: "ios" | "android" }) {
  return apiFetch<DeviceToken>("/notifications/device-token/", {
    method: "POST",
    body: input,
  });
}
