"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, Cable, CalendarCheck, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import {
  getNotificationSuppression,
  getWidgetSnapshot,
  listHealthData,
  listIntegrations,
  refreshWidgetSnapshot,
  updateIntegrationConsent,
  type HealthDataPoint,
  type IntegrationConsent,
  type IntegrationType,
  type WidgetSnapshot,
} from "@/lib/api/integrations";
import { ApiError } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";

const integrationLabels: Record<IntegrationType, { name: string; categories: string[] }> = {
  apple_health: { name: "Apple Health", categories: ["steps", "sleep", "workouts", "mindfulness"] },
  google_fit: { name: "Google Fit", categories: ["steps", "sleep", "workouts", "water"] },
  apple_calendar: { name: "Apple Calendar", categories: ["busy_blocks", "focus_time"] },
  google_calendar: { name: "Google Calendar", categories: ["busy_blocks", "focus_time"] },
};

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<IntegrationConsent[]>([]);
  const [snapshot, setSnapshot] = useState<WidgetSnapshot | null>(null);
  const [health, setHealth] = useState<HealthDataPoint[]>([]);
  const [suppressed, setSuppressed] = useState<{ suppressed: boolean; reason: string | null } | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<IntegrationType | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [integrationRes, snapshotRes, healthRes, suppressRes] = await Promise.all([
        listIntegrations(),
        getWidgetSnapshot(),
        listHealthData(),
        getNotificationSuppression(),
      ]);
      setIntegrations(integrationRes.integrations ?? []);
      setSnapshot(snapshotRes);
      setHealth(healthRes.items ?? []);
      setSuppressed(suppressRes);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not load integrations.";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const totals = useMemo(() => {
    return health.reduce<Record<string, number>>((acc, item) => {
      acc[item.metric] = (acc[item.metric] ?? 0) + item.value;
      return acc;
    }, {});
  }, [health]);

  async function handleToggle(integration: IntegrationConsent, enabled: boolean) {
    setPending(integration.integration_type);
    try {
      const meta = integrationLabels[integration.integration_type];
      const updated = await updateIntegrationConsent(integration.integration_type, {
        is_enabled: enabled,
        data_categories: enabled ? meta.categories : integration.data_categories,
      });
      setIntegrations((prev) =>
        prev.map((item) => (item.integration_type === updated.integration_type ? updated : item)),
      );
      toast.success(`${meta.name} ${enabled ? "enabled" : "disabled"}.`);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not update consent.";
      toast.error(message);
    } finally {
      setPending(null);
    }
  }

  async function handleRefreshWidget() {
    setRefreshing(true);
    try {
      setSnapshot(await refreshWidgetSnapshot());
      toast.success("Widget snapshot refreshed.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not refresh widget.";
      toast.error(message);
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-4 p-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Integrations</h1>
        <p className="text-sm text-muted-foreground">Consent, health data, calendar suppression, and widget state.</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Cable className="h-4 w-4" />
              Connected Sources
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)
            ) : (
              integrations.map((integration) => {
                const meta = integrationLabels[integration.integration_type];
                return (
                  <div key={integration.integration_type} className="flex items-center justify-between gap-3 rounded-md border px-3 py-3">
                    <div>
                      <p className="text-sm font-medium">{meta.name}</p>
                      <p className="text-xs text-muted-foreground">{integration.data_categories.join(", ") || "No categories shared"}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {pending === integration.integration_type ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                      <Switch
                        checked={integration.is_enabled}
                        onCheckedChange={(checked) => handleToggle(integration, checked)}
                        disabled={pending === integration.integration_type}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <CardTitle className="flex items-center gap-2 text-sm font-medium">
                <Activity className="h-4 w-4" />
                Widget Snapshot
              </CardTitle>
              <Button size="sm" variant="outline" onClick={handleRefreshWidget} disabled={refreshing}>
                {refreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                Refresh
              </Button>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-3">
              <Metric label="Streak" value={`${snapshot?.streak_count ?? 0}d`} />
              <Metric label="Momentum" value={`${Math.round((snapshot?.momentum_index_7d ?? 0) * 100)}%`} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm font-medium">
                <CalendarCheck className="h-4 w-4" />
                Calendar Suppression
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Badge variant={suppressed?.suppressed ? "default" : "secondary"}>
                {suppressed?.suppressed ? `Suppressed: ${suppressed.reason}` : "No suppression active"}
              </Badge>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Health Totals</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)
          ) : Object.keys(totals).length === 0 ? (
            <p className="text-sm text-muted-foreground">No health data synced yet.</p>
          ) : (
            Object.entries(totals).map(([metric, value]) => (
              <Metric key={metric} label={metric.replaceAll("_", " ")} value={String(Math.round(value))} />
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border px-3 py-3">
      <p className="text-xs capitalize text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold tracking-tight">{value}</p>
    </div>
  );
}
