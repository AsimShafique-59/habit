"use client";

import { useState } from "react";
import { Loader2, Plus } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api-client";
import { HABIT_CATEGORIES, type FrequencyType, type Habit, type HabitCategory } from "@/lib/api/habits";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

const WEEKDAYS = [
  { value: 1, label: "Mon" },
  { value: 2, label: "Tue" },
  { value: 3, label: "Wed" },
  { value: 4, label: "Thu" },
  { value: 5, label: "Fri" },
  { value: 6, label: "Sat" },
  { value: 7, label: "Sun" },
];

type Props = {
  onCreate: (input: {
    title: string;
    description?: string;
    category: HabitCategory;
    frequency_type: FrequencyType;
    frequency_days?: number[];
    frequency_count?: number;
    difficulty: "tiny" | "small" | "medium";
  }) => Promise<Habit>;
};

export function CreateHabitDialog({ onCreate }: Props) {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<HabitCategory>("Health");
  const [frequencyType, setFrequencyType] = useState<FrequencyType>("daily");
  const [frequencyDays, setFrequencyDays] = useState<number[]>([1, 2, 3, 4, 5]);
  const [frequencyCount, setFrequencyCount] = useState(3);
  const [difficulty, setDifficulty] = useState<"tiny" | "small" | "medium">("small");

  function reset() {
    setTitle("");
    setDescription("");
    setCategory("Health");
    setFrequencyType("daily");
    setFrequencyDays([1, 2, 3, 4, 5]);
    setFrequencyCount(3);
    setDifficulty("small");
  }

  function toggleDay(day: number) {
    setFrequencyDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day].sort(),
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onCreate({
        title,
        description: description || undefined,
        category,
        frequency_type: frequencyType,
        frequency_days: frequencyType === "weekdays" ? frequencyDays : undefined,
        frequency_count: frequencyType === "n_per_week" ? frequencyCount : undefined,
        difficulty,
      });
      toast.success("Habit created.");
      setOpen(false);
      reset();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not create habit.";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger>
        <Button>
          <Plus className="h-4 w-4" />
          New habit
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New habit</DialogTitle>
          <DialogDescription>Define what you want to track and how often.</DialogDescription>
        </DialogHeader>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="space-y-1.5">
            <Label htmlFor="habit-title">Title</Label>
            <Input
              id="habit-title"
              required
              maxLength={80}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Drink 8 glasses of water"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="habit-description">Description (optional)</Label>
            <Textarea
              id="habit-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Category</Label>
              <Select value={category} onValueChange={(v) => setCategory(v as HabitCategory)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {HABIT_CATEGORIES.map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>Difficulty</Label>
              <Select
                value={difficulty}
                onValueChange={(v) => setDifficulty(v as "tiny" | "small" | "medium")}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="tiny">Tiny</SelectItem>
                  <SelectItem value="small">Small</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Frequency</Label>
            <Select value={frequencyType} onValueChange={(v) => setFrequencyType(v as FrequencyType)}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">Every day</SelectItem>
                <SelectItem value="weekdays">Specific days</SelectItem>
                <SelectItem value="n_per_week">N times per week</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {frequencyType === "weekdays" && (
            <div className="flex flex-wrap gap-1.5">
              {WEEKDAYS.map((d) => (
                <button
                  type="button"
                  key={d.value}
                  onClick={() => toggleDay(d.value)}
                  className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
                    frequencyDays.includes(d.value)
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {d.label}
                </button>
              ))}
            </div>
          )}

          {frequencyType === "n_per_week" && (
            <div className="space-y-1.5">
              <Label htmlFor="habit-freq-count">Times per week</Label>
              <Input
                id="habit-freq-count"
                type="number"
                min={1}
                max={7}
                value={frequencyCount}
                onChange={(e) => setFrequencyCount(Number(e.target.value))}
              />
            </div>
          )}

          <DialogFooter>
            <Button type="submit" disabled={submitting}>
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Create habit
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
