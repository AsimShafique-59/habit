"use client";

import { Archive, ArchiveRestore, Check, Flame, Loader2 } from "lucide-react";

import type { Habit } from "@/lib/api/habits";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const FREQUENCY_LABEL: Record<Habit["frequency_type"], string> = {
  daily: "Every day",
  weekdays: "Specific days",
  n_per_week: "N times / week",
};

type Props = {
  habit: Habit;
  completedToday: boolean;
  completing: boolean;
  archiving: boolean;
  onComplete: () => void;
  onArchive: () => void;
};

export function HabitCard({ habit, completedToday, completing, archiving, onComplete, onArchive }: Props) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 py-1">
        <button
          onClick={onComplete}
          disabled={completing || completedToday || habit.is_archived}
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 transition-colors",
            completedToday
              ? "border-primary bg-primary text-primary-foreground"
              : "border-muted-foreground/30 text-transparent hover:border-primary",
          )}
          aria-label={completedToday ? "Completed today" : "Mark complete for today"}
        >
          {completing ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : (
            <Check className="h-5 w-5" />
          )}
        </button>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{habit.title}</p>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            <Badge variant="secondary" className="text-[10px]">
              {habit.category}
            </Badge>
            <Badge variant="outline" className="text-[10px]">
              {FREQUENCY_LABEL[habit.frequency_type]}
            </Badge>
            {habit.current_streak > 0 && (
              <span className="flex items-center gap-1 text-xs font-medium text-orange-500">
                <Flame className="h-3.5 w-3.5" />
                {habit.current_streak}
              </span>
            )}
          </div>
        </div>

        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onArchive}
          disabled={archiving}
          aria-label={habit.is_archived ? "Unarchive habit" : "Archive habit"}
        >
          {archiving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : habit.is_archived ? (
            <ArchiveRestore className="h-4 w-4" />
          ) : (
            <Archive className="h-4 w-4" />
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
