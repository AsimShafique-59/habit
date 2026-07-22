"use client";

import { useCallback, useEffect, useState } from "react";
import { Bookmark, Headphones, Heart, Loader2, StickyNote } from "lucide-react";
import { toast } from "sonner";

import {
  listInsightCategories,
  listInsights,
  saveInsightNote,
  setInsightFavorite,
  setInsightSaved,
  type AudioInsight,
  type InsightCategory,
} from "@/lib/api/insights";
import { ApiError } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

function duration(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

export default function InsightsPage() {
  const [categories, setCategories] = useState<InsightCategory[]>([]);
  const [items, setItems] = useState<AudioInsight[]>([]);
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [savingNote, setSavingNote] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [categoryRes, insightRes] = await Promise.all([listInsightCategories(), listInsights()]);
      setCategories(categoryRes);
      setItems(insightRes);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not load insights.";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSaved(item: AudioInsight) {
    const next = !item.is_saved;
    setItems((prev) => prev.map((current) => (current.id === item.id ? { ...current, is_saved: next } : current)));
    try {
      await setInsightSaved(item.id, next);
    } catch (err) {
      setItems((prev) => prev.map((current) => (current.id === item.id ? { ...current, is_saved: item.is_saved } : current)));
      const message = err instanceof ApiError ? err.message : "Could not update saved state.";
      toast.error(message);
    }
  }

  async function handleFavorite(item: AudioInsight) {
    const next = !item.is_favorited;
    setItems((prev) => prev.map((current) => (current.id === item.id ? { ...current, is_favorited: next } : current)));
    try {
      await setInsightFavorite(item.id, next);
    } catch (err) {
      setItems((prev) => prev.map((current) => (current.id === item.id ? { ...current, is_favorited: item.is_favorited } : current)));
      const message = err instanceof ApiError ? err.message : "Could not update favorite state.";
      toast.error(message);
    }
  }

  async function handleNote(id: string) {
    setSavingNote(id);
    try {
      const result = await saveInsightNote(id, notes[id] ?? "");
      setItems((prev) => prev.map((item) => (item.id === id ? { ...item, note: result.note } : item)));
      toast.success("Note saved.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not save note.";
      toast.error(message);
    } finally {
      setSavingNote(null);
    }
  }

  const visibleItems =
    activeCategory === "all"
      ? items
      : items.filter((item) => item.category?.slug === activeCategory);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-4 p-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Insights</h1>
        <p className="text-sm text-muted-foreground">Audio content, categories, saves, favorites, and notes.</p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant={activeCategory === "all" ? "default" : "outline"} onClick={() => setActiveCategory("all")}>
          All
        </Button>
        {categories.map((category) => (
          <Button
            key={category.id}
            size="sm"
            variant={activeCategory === category.slug ? "default" : "outline"}
            onClick={() => setActiveCategory(category.slug)}
          >
            {category.name}
          </Button>
        ))}
      </div>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-64 w-full" />)}
        </div>
      ) : visibleItems.length === 0 ? (
        <Card>
          <CardContent className="py-14 text-center text-sm text-muted-foreground">No insights available.</CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visibleItems.map((item) => (
            <Card key={item.id}>
              <CardHeader>
                <CardTitle className="flex items-start justify-between gap-3 text-sm font-medium">
                  <span className="line-clamp-2">{item.title}</span>
                  <Headphones className="h-4 w-4 shrink-0 text-primary" />
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="line-clamp-3 text-sm text-muted-foreground">{item.description || "No description."}</p>
                <div className="flex flex-wrap items-center gap-2">
                  {item.category ? <Badge variant="secondary">{item.category.name}</Badge> : null}
                  <Badge variant="outline">{duration(item.duration_seconds)}</Badge>
                </div>
                {item.audio_url ? <audio controls src={item.audio_url} className="h-9 w-full" /> : null}
                <div className="flex gap-2">
                  <Button size="icon" variant="outline" onClick={() => handleSaved(item)} className={cn(item.is_saved && "bg-primary/10 text-primary")}>
                    <Bookmark className="h-4 w-4" />
                  </Button>
                  <Button size="icon" variant="outline" onClick={() => handleFavorite(item)} className={cn(item.is_favorited && "bg-primary/10 text-primary")}>
                    <Heart className="h-4 w-4" />
                  </Button>
                </div>
                <Textarea
                  value={notes[item.id] ?? item.note ?? ""}
                  onChange={(event) => setNotes((prev) => ({ ...prev, [item.id]: event.target.value }))}
                  className="min-h-16"
                />
                <Button size="sm" variant="outline" onClick={() => handleNote(item.id)} disabled={savingNote === item.id}>
                  {savingNote === item.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <StickyNote className="h-4 w-4" />}
                  Save note
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
