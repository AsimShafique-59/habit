"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { BarChart3, CalendarDays, Flame, RefreshCw, Target, TrendingUp } from "lucide-react";
import { toast } from "sonner";

import {
  generateWeeklyReport,
  getCompletionRate,
  getConsistencyScore,
  getDayOfWeekBreakdown,
  getHeatmap,
  getMomentumIndex,
  getStreakDashboard,
  listWeeklyReports,
  type CompletionRate,
  type ConsistencyScore,
  type DayOfWeekBreakdown,
  type HeatmapPoint,
  type MomentumIndex,
  type StreakDashboard,
  type WeeklyReport,
} from "@/lib/api/analytics";
import { ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";

function pct(value: unknown) {
  const num = typeof value === "number" ? value : Number(value ?? 0);
  if (Number.isNaN(num)) return 0;
  return Math.round(num <= 1 ? num * 100 : num);
}

function firstNumber(source: Record<string, unknown> | undefined, keys: string[]) {
  for (const key of keys) {
    const value = source?.[key];
    if (typeof value === "number") return value;
  }
  return 0;
}

export default function AnalyticsPage() {
  const [completion, setCompletion] = useState<CompletionRate | null>(null);
  const [momentum, setMomentum] = useState<MomentumIndex | null>(null);
  const [consistency, setConsistency] = useState<ConsistencyScore | null>(null);
  const [streaks, setStreaks] = useState<StreakDashboard | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapPoint[]>([]);
  const [weekdays, setWeekdays] = useState<DayOfWeekBreakdown["breakdown"]>([]);
  const [reports, setReports] = useState<WeeklyReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [completionRes, momentumRes, consistencyRes, streakRes, heatmapRes, weekdayRes, reportsRes] =
        await Promise.all([
          getCompletionRate(),
          getMomentumIndex(),
          getConsistencyScore(),
          getStreakDashboard(),
          getHeatmap(),
          getDayOfWeekBreakdown(),
          listWeeklyReports(),
        ]);
      setCompletion(completionRes);
      setMomentum(momentumRes);
      setConsistency(consistencyRes);
      setStreaks(streakRes);
      setHeatmap(heatmapRes.heatmap ?? []);
      setWeekdays(weekdayRes.breakdown ?? []);
      setReports(reportsRes.reports ?? []);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not load analytics.";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleGenerateReport() {
    setGenerating(true);
    try {
      const report = await generateWeeklyReport();
      setReports((prev) => [report, ...prev.filter((item) => item.id !== report.id)]);
      toast.success("Weekly report refreshed.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not generate report.";
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  }

  const completionRate = pct(
    completion?.overall_rate ?? completion?.completion_rate ?? completion?.total_completed,
  );
  const consistencyScore = pct(consistency?.score ?? consistency?.consistency_score);
  const momentum7 = pct(firstNumber(momentum ?? undefined, ["momentum_7d", "seven_day", "7d"]));
  const bestStreak = useMemo(() => {
    const rows = Array.isArray(streaks?.streaks) ? streaks?.streaks ?? [] : [];
    return rows.reduce((best, item) => Math.max(best, item.current_streak ?? 0), 0);
  }, [streaks]);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-5 p-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Analytics</h1>
          <p className="text-sm text-muted-foreground">Completion, streak, and consistency signals.</p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard icon={Target} label="Completion" value={`${completionRate}%`} loading={loading} />
        <MetricCard icon={TrendingUp} label="Momentum 7d" value={`${momentum7}%`} loading={loading} />
        <MetricCard icon={BarChart3} label="Consistency" value={`${consistencyScore}%`} loading={loading} />
        <MetricCard icon={Flame} label="Best streak" value={`${bestStreak}d`} loading={loading} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Last 365 Days</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-44 w-full" />
            ) : (
              <div className="grid grid-cols-[repeat(26,minmax(0,1fr))] gap-1">
                {heatmap.slice(-156).map((day, index) => {
                  const value = pct(day.value ?? day.completion_rate ?? 0);
                  return (
                    <div
                      key={`${day.date}-${index}`}
                      title={`${day.date}: ${value}%`}
                      className="aspect-square rounded-[3px] border border-border/40"
                      style={{
                        backgroundColor:
                          value >= 80
                            ? "oklch(0.68 0.18 150)"
                            : value >= 50
                              ? "oklch(0.78 0.15 80)"
                              : value > 0
                                ? "oklch(0.72 0.13 35)"
                                : "oklch(0.94 0.02 250)",
                      }}
                    />
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Weekday Pattern</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              Array.from({ length: 7 }).map((_, i) => <Skeleton key={i} className="h-7 w-full" />)
            ) : weekdays.length === 0 ? (
              <p className="py-8 text-sm text-muted-foreground">No weekday data yet.</p>
            ) : (
              weekdays.map((day, index) => {
                const value = pct(day.completion_rate ?? day.rate);
                return (
                  <div key={`${day.day ?? day.weekday ?? index}`} className="space-y-1.5">
                    <div className="flex justify-between text-xs">
                      <span className="font-medium">{day.day ?? day.weekday ?? `Day ${index + 1}`}</span>
                      <span className="text-muted-foreground">{value}%</span>
                    </div>
                    <Progress value={value} />
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Habit Streaks</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)
            ) : !Array.isArray(streaks?.streaks) || streaks.streaks.length === 0 ? (
              <p className="py-8 text-sm text-muted-foreground">No streak data yet.</p>
            ) : (
              streaks.streaks.slice(0, 6).map((habit) => (
                <div key={habit.habit_id ?? habit.title} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                  <span className="truncate font-medium">{habit.title ?? habit.name ?? "Habit"}</span>
                  <span className="shrink-0 text-muted-foreground">
                    {habit.current_streak ?? 0} current / {habit.longest_streak ?? 0} best
                  </span>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <CalendarDays className="h-4 w-4" />
              Weekly Reports
            </CardTitle>
            <Button size="sm" onClick={handleGenerateReport} disabled={generating}>
              Generate
            </Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {loading ? (
              <Skeleton className="h-24 w-full" />
            ) : reports.length === 0 ? (
              <p className="py-8 text-sm text-muted-foreground">No weekly reports yet.</p>
            ) : (
              reports.slice(0, 3).map((report) => (
                <div key={report.id} className="rounded-md border px-3 py-2">
                  <div className="flex justify-between gap-3 text-sm">
                    <span className="font-medium">{report.week_start} to {report.week_end}</span>
                    <span className="text-muted-foreground">{pct(report.completion_rate)}%</span>
                  </div>
                  {report.summary ? (
                    <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{report.summary}</p>
                  ) : null}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  loading,
}: {
  icon: typeof Target;
  label: string;
  value: string;
  loading: boolean;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
          <Icon className="h-4 w-4 text-primary" />
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-8 w-20" /> : <p className="text-3xl font-semibold tracking-tight">{value}</p>}
      </CardContent>
    </Card>
  );
}
