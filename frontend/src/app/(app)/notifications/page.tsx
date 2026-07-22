"use client";

import { useCallback, useEffect, useState } from "react";
import { Bell, CheckCheck, Loader2, Smartphone } from "lucide-react";
import { toast } from "sonner";

import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  registerDeviceToken,
  type NotificationItem,
} from "@/lib/api/notifications";
import { ApiError } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [platform, setPlatform] = useState<"ios" | "android">("ios");
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingToken, setSavingToken] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listNotifications();
      setItems(data.items ?? []);
      setUnreadCount(data.unread_count ?? 0);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not load notifications.";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRead(item: NotificationItem) {
    if (item.is_read) return;
    try {
      const updated = await markNotificationRead(item.id);
      setItems((prev) => prev.map((n) => (n.id === item.id ? updated : n)));
      setUnreadCount((prev) => Math.max(prev - 1, 0));
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not mark notification read.";
      toast.error(message);
    }
  }

  async function handleAllRead() {
    try {
      await markAllNotificationsRead();
      setItems((prev) => prev.map((item) => ({ ...item, is_read: true, read_at: item.read_at ?? new Date().toISOString() })));
      setUnreadCount(0);
      toast.success("Notifications marked read.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not update notifications.";
      toast.error(message);
    }
  }

  async function handleDeviceToken() {
    if (!token.trim()) return;
    setSavingToken(true);
    try {
      await registerDeviceToken({ token: token.trim(), platform });
      setToken("");
      toast.success("Device token registered.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not register device token.";
      toast.error(message);
    } finally {
      setSavingToken(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-4 p-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Notifications</h1>
          <p className="text-sm text-muted-foreground">{unreadCount} unread notification(s).</p>
        </div>
        <Button variant="outline" onClick={handleAllRead} disabled={unreadCount === 0}>
          <CheckCheck className="h-4 w-4" />
          Mark all read
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <Smartphone className="h-4 w-4" />
            Push Device
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 sm:grid-cols-[140px_1fr_auto]">
          <Select value={platform} onValueChange={(value) => setPlatform(value as "ios" | "android")}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ios">iOS</SelectItem>
              <SelectItem value="android">Android</SelectItem>
            </SelectContent>
          </Select>
          <Input value={token} onChange={(event) => setToken(event.target.value)} />
          <Button onClick={handleDeviceToken} disabled={savingToken || !token.trim()}>
            {savingToken ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bell className="h-4 w-4" />}
            Register
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Inbox</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-18 w-full" />)
          ) : items.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">No notifications yet.</p>
          ) : (
            items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => handleRead(item)}
                className="w-full rounded-md border px-3 py-2 text-left transition-colors hover:bg-muted/50"
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-medium">{item.title}</p>
                  <Badge variant={item.is_read ? "secondary" : "default"}>{item.is_read ? "Read" : "New"}</Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{item.body}</p>
                <p className="mt-2 text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString()}</p>
              </button>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
