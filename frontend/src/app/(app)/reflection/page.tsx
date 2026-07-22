"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpen, Check, Loader2, SmilePlus } from "lucide-react";
import { toast } from "sonner";

import {
  createJournalEntry,
  getMoodSummary,
  getTodayPrompt,
  listJournalEntries,
  listMoodLogs,
  logMood,
  type JournalEntry,
  type MoodLog,
  type MoodSummary,
  type ReflectionPrompt,
} from "@/lib/api/reflection";
import { ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

const moodLabels = ["Awful", "Bad", "Okay", "Good", "Great"];

export default function ReflectionPage() {
  const [prompt, setPrompt] = useState<ReflectionPrompt | null>(null);
  const [summary, setSummary] = useState<MoodSummary | null>(null);
  const [moods, setMoods] = useState<MoodLog[]>([]);
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [score, setScore] = useState(4);
  const [note, setNote] = useState("");
  const [journalText, setJournalText] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingMood, setSavingMood] = useState(false);
  const [savingJournal, setSavingJournal] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [promptRes, summaryRes, moodRes, journalRes] = await Promise.all([
        getTodayPrompt(),
        getMoodSummary(),
        listMoodLogs(),
        listJournalEntries(),
      ]);
      setPrompt(promptRes.prompt);
      setSummary(summaryRes);
      setMoods(moodRes);
      setEntries(journalRes);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not load reflection.";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleMood() {
    setSavingMood(true);
    try {
      const created = await logMood({ score, note });
      setMoods((prev) => [created, ...prev.filter((item) => item.id !== created.id)]);
      setNote("");
      setSummary((prev) =>
        prev
          ? {
              ...prev,
              total_logs: prev.total_logs + 1,
              average_score: Number(((prev.average_score * prev.total_logs + score) / (prev.total_logs + 1)).toFixed(2)),
              by_score: { ...prev.by_score, [score]: (prev.by_score[String(score)] ?? 0) + 1 },
            }
          : prev,
      );
      toast.success("Mood logged.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not log mood.";
      toast.error(message);
    } finally {
      setSavingMood(false);
    }
  }

  async function handleJournal() {
    if (!journalText.trim()) return;
    setSavingJournal(true);
    try {
      const entry = await createJournalEntry({
        text: journalText.trim(),
        prompt_id: prompt?.id ?? null,
      });
      setEntries((prev) => [entry, ...prev]);
      setJournalText("");
      toast.success("Journal entry saved.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not save journal.";
      toast.error(message);
    } finally {
      setSavingJournal(false);
    }
  }

  return (
    <div className="mx-auto grid w-full max-w-6xl flex-1 gap-4 p-6 lg:grid-cols-[0.85fr_1.15fr]">
      <div className="space-y-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Reflection</h1>
          <p className="text-sm text-muted-foreground">Mood, prompts, and short journal entries.</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <SmilePlus className="h-4 w-4" />
              Mood Check-in
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-5 gap-2">
              {moodLabels.map((label, index) => {
                const value = index + 1;
                return (
                  <Button
                    key={label}
                    type="button"
                    variant={score === value ? "default" : "outline"}
                    onClick={() => setScore(value)}
                    className="h-12 px-1 text-xs"
                  >
                    {label}
                  </Button>
                );
              })}
            </div>
            <Textarea value={note} onChange={(event) => setNote(event.target.value)} className="min-h-20" />
            <Button onClick={handleMood} disabled={savingMood}>
              {savingMood ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              Save mood
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Mood Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <Skeleton className="h-28 w-full" />
            ) : (
              <>
                <div className="flex items-end justify-between">
                  <p className="text-3xl font-semibold tracking-tight">{summary?.average_score ?? 0}</p>
                  <p className="text-sm text-muted-foreground">{summary?.streak_days ?? 0} day streak</p>
                </div>
                {[5, 4, 3, 2, 1].map((value) => {
                  const count = summary?.by_score[String(value)] ?? 0;
                  const total = summary?.total_logs || 1;
                  return (
                    <div key={value} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span>{moodLabels[value - 1]}</span>
                        <span className="text-muted-foreground">{count}</span>
                      </div>
                      <Progress value={(count / total) * 100} />
                    </div>
                  );
                })}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <BookOpen className="h-4 w-4" />
              Journal
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {prompt ? (
              <div className="rounded-md border bg-muted/30 px-3 py-2 text-sm">{prompt.text}</div>
            ) : null}
            <Textarea
              value={journalText}
              onChange={(event) => setJournalText(event.target.value)}
              className="min-h-32"
            />
            <Button onClick={handleJournal} disabled={savingJournal || !journalText.trim()}>
              {savingJournal ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              Save entry
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Recent Entries</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)
            ) : entries.length === 0 ? (
              <p className="py-8 text-sm text-muted-foreground">No journal entries yet.</p>
            ) : (
              entries.slice(0, 6).map((entry) => (
                <div key={entry.id} className="rounded-md border px-3 py-2">
                  <p className="text-xs text-muted-foreground">{entry.entry_date}</p>
                  <p className="mt-1 line-clamp-3 text-sm">{entry.text}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Mood History</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {loading ? (
              <Skeleton className="h-20 w-full" />
            ) : moods.length === 0 ? (
              <p className="py-6 text-sm text-muted-foreground">No mood logs yet.</p>
            ) : (
              moods.slice(0, 7).map((mood) => (
                <div key={mood.id} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                  <span>{mood.date}</span>
                  <span className="font-medium">{moodLabels[mood.score - 1] ?? mood.emoji_label}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
