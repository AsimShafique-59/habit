"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Circle, Flame, TrendingUp } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/contexts/auth-context";
import { getWidgetSnapshot, type WidgetSnapshot } from "@/lib/api/integrations";
import { ApiError } from "@/lib/api-client";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardPage() {
  const { user } = useAuth();
  const [snapshot, setSnapshot] = useState<WidgetSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getWidgetSnapshot()
      .then((data) => {
        if (!cancelled) setSnapshot(data);
      })
      .catch((err) => {
        const message = err instanceof ApiError ? err.message : "Could not load your dashboard.";
        toast.error(message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const momentumPercent = snapshot ? Math.round(snapshot.momentum_index_7d * 100) : 0;

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4 p-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">
          Welcome back{user?.name ? `, ${user.name}` : ""}
        </h1>
        <p className="text-sm text-muted-foreground">Here&apos;s where things stand today.</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
              <Flame className="h-4 w-4 text-orange-500" />
              Best streak
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <p className="text-3xl font-semibold tracking-tight">
                {snapshot?.streak_count ?? 0}
                <span className="ml-1 text-sm font-normal text-muted-foreground">days</span>
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
              <TrendingUp className="h-4 w-4 text-primary" />
              7-day momentum
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <p className="text-3xl font-semibold tracking-tight">{momentumPercent}%</p>
                <Progress value={momentumPercent} />
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Today&apos;s habits</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-9 w-full" />)
          ) : !snapshot || snapshot.habits_today.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No habits scheduled for today.{" "}
              <Link href="/habits" className="font-medium text-foreground underline underline-offset-4">
                Create one
              </Link>
              .
            </p>
          ) : (
            snapshot.habits_today.map((h) => (
              <div key={h.habit_id} className="flex items-center gap-2.5 rounded-md px-1 py-1.5 text-sm">
                {h.completed ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-primary" />
                ) : (
                  <Circle className="h-4 w-4 shrink-0 text-muted-foreground/40" />
                )}
                <span className={h.completed ? "text-muted-foreground line-through" : ""}>
                  {h.name}
                </span>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Link href="/habits" className={buttonVariants({ variant: "outline" }) + " w-fit"}>
        Manage habits
      </Link>
    </div>
  );
}
