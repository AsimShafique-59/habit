"use client";

import { useCallback, useEffect, useState } from "react";
import { ListChecks } from "lucide-react";
import { toast } from "sonner";

import {
  archiveHabit,
  completeHabit,
  createHabit,
  listHabits,
  unarchiveHabit,
  type Habit,
} from "@/lib/api/habits";
import { getWidgetSnapshot } from "@/lib/api/integrations";
import { ApiError } from "@/lib/api-client";
import { CreateHabitDialog } from "@/components/habits/create-habit-dialog";
import { HabitCard } from "@/components/habits/habit-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate(),
  ).padStart(2, "0")}`;
}

export default function HabitsPage() {
  const [tab, setTab] = useState<"active" | "archived">("active");
  const [habits, setHabits] = useState<Habit[]>([]);
  const [completedToday, setCompletedToday] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set());
  const [archivingIds, setArchivingIds] = useState<Set<string>>(new Set());

  const load = useCallback(async (status: "active" | "archived") => {
    setLoading(true);
    try {
      const [habitsRes, snapshot] = await Promise.all([
        listHabits({ status }),
        status === "active" ? getWidgetSnapshot().catch(() => null) : Promise.resolve(null),
      ]);
      setHabits(habitsRes.items);
      if (snapshot) {
        setCompletedToday(
          new Set(snapshot.habits_today.filter((h) => h.completed).map((h) => h.habit_id)),
        );
      }
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not load habits.";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(tab);
  }, [tab, load]);

  async function handleCreate(input: Parameters<typeof createHabit>[0]) {
    const habit = await createHabit(input);
    setHabits((prev) => [habit, ...prev]);
    return habit;
  }

  async function handleComplete(habit: Habit) {
    setPendingIds((prev) => new Set(prev).add(habit.id));
    try {
      const result = await completeHabit(habit.id, {
        completion_date: todayIso(),
        source: "manual",
      });
      setHabits((prev) =>
        prev.map((h) =>
          h.id === habit.id
            ? { ...h, current_streak: result.current_streak, longest_streak: result.longest_streak }
            : h,
        ),
      );
      setCompletedToday((prev) => new Set(prev).add(habit.id));
      toast.success(`"${habit.title}" marked complete.`);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not log completion.";
      toast.error(message);
    } finally {
      setPendingIds((prev) => {
        const next = new Set(prev);
        next.delete(habit.id);
        return next;
      });
    }
  }

  async function handleArchiveToggle(habit: Habit) {
    setArchivingIds((prev) => new Set(prev).add(habit.id));
    try {
      if (habit.is_archived) {
        await unarchiveHabit(habit.id);
        toast.success(`"${habit.title}" restored.`);
      } else {
        await archiveHabit(habit.id);
        toast.success(`"${habit.title}" archived.`);
      }
      setHabits((prev) => prev.filter((h) => h.id !== habit.id));
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not update habit.";
      toast.error(message);
    } finally {
      setArchivingIds((prev) => {
        const next = new Set(prev);
        next.delete(habit.id);
        return next;
      });
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4 p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Habits</h1>
          <p className="text-sm text-muted-foreground">
            Create, track, and complete your daily and weekly habits.
          </p>
        </div>
        <CreateHabitDialog onCreate={handleCreate} />
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as "active" | "archived")}>
        <TabsList>
          <TabsTrigger value="active">Active</TabsTrigger>
          <TabsTrigger value="archived">Archived</TabsTrigger>
        </TabsList>
      </Tabs>

      {loading ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-18 w-full rounded-xl" />
          ))}
        </div>
      ) : habits.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-16 text-center">
          <ListChecks className="h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            {tab === "active" ? "No habits yet — create your first one." : "No archived habits."}
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {habits.map((habit) => (
            <HabitCard
              key={habit.id}
              habit={habit}
              completedToday={completedToday.has(habit.id)}
              completing={pendingIds.has(habit.id)}
              archiving={archivingIds.has(habit.id)}
              onComplete={() => handleComplete(habit)}
              onArchive={() => handleArchiveToggle(habit)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
