"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bot,
  Check,
  Cpu,
  Layers3,
  Loader2,
  MessageSquareText,
  Sparkles,
  Wand2,
} from "lucide-react";
import { toast } from "sonner";

import {
  acceptHabitSuggestions,
  generateHabitSuggestions,
  getLatestCoachingReview,
  getOnboardingQuestions,
  respondToCoachingReview,
  submitOnboardingAnswers,
  triggerCoachingReview,
  type CoachingReview,
  type HabitSuggestion,
  type OnboardingQuestion,
} from "@/lib/api/ai";
import { ApiError } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type Answers = Record<string, unknown>;

export default function AiCoachPage() {
  const [questions, setQuestions] = useState<OnboardingQuestion[]>([]);
  const [onboardingComplete, setOnboardingComplete] = useState(false);
  const [answers, setAnswers] = useState<Answers>({});
  const [suggestions, setSuggestions] = useState<HabitSuggestion[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [review, setReview] = useState<CoachingReview | null>(null);
  const [mode, setMode] = useState<"starter" | "expanded">("starter");
  const [loading, setLoading] = useState(true);
  const [submittingAnswers, setSubmittingAnswers] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [reviewing, setReviewing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const questionRes = await getOnboardingQuestions();
      setQuestions(questionRes.questions ?? []);
      setOnboardingComplete(questionRes.onboarding_completed);
      try {
        setReview(await getLatestCoachingReview());
      } catch (err) {
        if (!(err instanceof ApiError && err.status === 404)) throw err;
      }
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not load AI Coach.";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const answeredCount = useMemo(() => {
    return questions.filter((q) => answers[q.id] !== undefined && answers[q.id] !== "").length;
  }, [answers, questions]);

  function setAnswer(question: OnboardingQuestion, value: unknown) {
    setAnswers((prev) => ({ ...prev, [question.id]: value }));
  }

  async function handleSaveAnswers() {
    setSubmittingAnswers(true);
    try {
      const result = await submitOnboardingAnswers(answers);
      setOnboardingComplete(result.onboarding_completed);
      toast.success("AI profile updated.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not save answers.";
      toast.error(message);
    } finally {
      setSubmittingAnswers(false);
    }
  }

  async function handleGenerate() {
    setGenerating(true);
    try {
      const result = await generateHabitSuggestions(mode);
      setSuggestions(result.suggestions ?? []);
      setSelected(new Set((result.suggestions ?? []).map((item) => item.suggestion_id)));
      toast.success(result.from_cache ? "Cached suggestions loaded." : "Suggestions generated.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not generate suggestions.";
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  }

  async function handleAccept() {
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    setAccepting(true);
    try {
      const result = await acceptHabitSuggestions(ids);
      setSuggestions((prev) =>
        prev.map((item) =>
          ids.includes(item.suggestion_id) ? { ...item, is_accepted: true } : item,
        ),
      );
      toast.success(`${result.created_habits.length} habit(s) created.`);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not accept suggestions.";
      toast.error(message);
    } finally {
      setAccepting(false);
    }
  }

  async function handleReview() {
    setReviewing(true);
    try {
      const result = await triggerCoachingReview();
      setReview({
        review_id: result.review_id,
        proposals: result.proposals ?? [],
        status: "pending",
        created_at: new Date().toISOString(),
        responded_at: null,
      });
      toast.success("Coaching review generated.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not generate coaching review.";
      toast.error(message);
    } finally {
      setReviewing(false);
    }
  }

  async function handleProposalAction(action: "accept" | "dismiss") {
    if (!review) return;
    const decisions = review.proposals.map((proposal, index) => ({
      proposal_id: proposal.proposal_id ?? String(index),
      action,
    }));
    try {
      await respondToCoachingReview(review.review_id, decisions);
      setReview({ ...review, status: "responded", responded_at: new Date().toISOString() });
      toast.success(action === "accept" ? "Review proposals applied." : "Review dismissed.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not respond to review.";
      toast.error(message);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-5 p-6">
      <div className="relative overflow-hidden rounded-lg border bg-[linear-gradient(135deg,oklch(0.22_0.04_250),oklch(0.16_0.03_180))] p-5 text-white">
        <div className="absolute inset-0 opacity-30 [background-image:linear-gradient(oklch(1_0_0/.14)_1px,transparent_1px),linear-gradient(90deg,oklch(1_0_0/.14)_1px,transparent_1px)] [background-size:28px_28px]" />
        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <div className="mb-3 flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-md bg-white/12">
                <Bot className="h-5 w-5" />
              </div>
              <Badge className="border-white/20 bg-white/10 text-white hover:bg-white/10">AIC Engine</Badge>
            </div>
            <h1 className="text-2xl font-semibold tracking-tight">AI Coach</h1>
            <p className="mt-1 text-sm text-white/75">
              A focused command center for onboarding signals, habit generation, and coaching reviews.
            </p>
          </div>
          <div className="grid min-w-64 grid-cols-3 gap-2 text-center text-xs">
            <Signal label="Profile" value={onboardingComplete ? "ready" : `${answeredCount}/${questions.length}`} />
            <Signal label="Ideas" value={String(suggestions.length)} />
            <Signal label="Review" value={review?.status ?? "none"} />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="grid gap-4 lg:grid-cols-3">
          <Skeleton className="h-72 lg:col-span-1" />
          <Skeleton className="h-72 lg:col-span-2" />
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm font-medium">
                <Cpu className="h-4 w-4" />
                Profile Signals
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {questions.length === 0 ? (
                <p className="text-sm text-muted-foreground">No onboarding prompts are available.</p>
              ) : (
                questions.map((question) => (
                  <div key={question.id} className="space-y-2">
                    <p className="text-sm font-medium">{question.prompt}</p>
                    <QuestionInput question={question} value={answers[question.id]} onChange={(value) => setAnswer(question, value)} />
                  </div>
                ))
              )}
              <Button onClick={handleSaveAnswers} disabled={submittingAnswers || questions.length === 0} className="w-full">
                {submittingAnswers ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                Save profile
              </Button>
            </CardContent>
          </Card>

          <div className="flex flex-col gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between gap-3">
                <CardTitle className="flex items-center gap-2 text-sm font-medium">
                  <Wand2 className="h-4 w-4" />
                  Habit Generator
                </CardTitle>
                <Tabs value={mode} onValueChange={(value) => setMode(value as "starter" | "expanded")}>
                  <TabsList>
                    <TabsTrigger value="starter">Starter</TabsTrigger>
                    <TabsTrigger value="expanded">Expanded</TabsTrigger>
                  </TabsList>
                </Tabs>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button onClick={handleGenerate} disabled={generating || !onboardingComplete}>
                  {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  Generate suggestions
                </Button>
                {suggestions.length === 0 ? (
                  <p className="py-6 text-sm text-muted-foreground">
                    {onboardingComplete ? "No suggestions generated yet." : "Complete the profile signals first."}
                  </p>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2">
                    {suggestions.map((suggestion) => {
                      const checked = selected.has(suggestion.suggestion_id);
                      return (
                        <button
                          key={suggestion.suggestion_id}
                          type="button"
                          onClick={() =>
                            setSelected((prev) => {
                              const next = new Set(prev);
                              if (next.has(suggestion.suggestion_id)) next.delete(suggestion.suggestion_id);
                              else next.add(suggestion.suggestion_id);
                              return next;
                            })
                          }
                          className={cn(
                            "rounded-lg border p-3 text-left transition-colors",
                            checked ? "border-primary bg-primary/5" : "hover:bg-muted/50",
                          )}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <p className="text-sm font-semibold">{suggestion.title}</p>
                            <Badge variant={suggestion.is_accepted ? "default" : "secondary"}>
                              {suggestion.is_accepted ? "Accepted" : suggestion.difficulty}
                            </Badge>
                          </div>
                          <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{suggestion.description}</p>
                          <p className="mt-2 text-xs text-muted-foreground">{suggestion.rationale}</p>
                        </button>
                      );
                    })}
                  </div>
                )}
                {suggestions.length > 0 ? (
                  <Button onClick={handleAccept} disabled={accepting || selected.size === 0}>
                    Accept selected
                  </Button>
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between gap-3">
                <CardTitle className="flex items-center gap-2 text-sm font-medium">
                  <MessageSquareText className="h-4 w-4" />
                  Coaching Review
                </CardTitle>
                <Button variant="outline" size="sm" onClick={handleReview} disabled={reviewing}>
                  {reviewing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Layers3 className="h-4 w-4" />}
                  Review
                </Button>
              </CardHeader>
              <CardContent className="space-y-3">
                {!review ? (
                  <p className="py-6 text-sm text-muted-foreground">No coaching review yet.</p>
                ) : review.proposals.length === 0 ? (
                  <p className="py-6 text-sm text-muted-foreground">No changes proposed for the latest review.</p>
                ) : (
                  review.proposals.map((proposal, index) => (
                    <div key={proposal.proposal_id ?? index} className="rounded-md border px-3 py-2">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-medium">{proposal.title ?? proposal.proposal_type ?? "Proposal"}</p>
                        <Badge variant="outline">{proposal.proposal_type ?? "coach"}</Badge>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{proposal.explanation ?? "Review this coaching proposal."}</p>
                    </div>
                  ))
                )}
                {review && review.status === "pending" && review.proposals.length > 0 ? (
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => handleProposalAction("accept")}>Accept all</Button>
                    <Button size="sm" variant="outline" onClick={() => handleProposalAction("dismiss")}>Dismiss</Button>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

function Signal({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-white/12 bg-white/8 px-3 py-2">
      <p className="text-[11px] uppercase text-white/55">{label}</p>
      <p className="mt-1 truncate font-medium">{value}</p>
    </div>
  );
}

function QuestionInput({
  question,
  value,
  onChange,
}: {
  question: OnboardingQuestion;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  if (question.question_type === "free_text") {
    return (
      <Textarea
        value={typeof value === "string" ? value : ""}
        onChange={(event) => onChange(event.target.value)}
        className="min-h-20"
      />
    );
  }

  if (question.question_type === "scale") {
    return (
      <Input
        type="number"
        min={1}
        max={5}
        value={typeof value === "number" || typeof value === "string" ? value : ""}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    );
  }

  if (question.question_type === "multi_select") {
    const selectedValues = Array.isArray(value) ? value : [];
    return (
      <div className="flex flex-wrap gap-2">
        {question.options.map((option) => {
          const active = selectedValues.includes(option);
          return (
            <Button
              key={option}
              type="button"
              size="sm"
              variant={active ? "default" : "outline"}
              onClick={() => {
                const next = active
                  ? selectedValues.filter((item) => item !== option)
                  : [...selectedValues, option].slice(0, question.max_selections || undefined);
                onChange(next);
              }}
            >
              {option}
            </Button>
          );
        })}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {question.options.map((option) => (
        <Button
          key={option}
          type="button"
          size="sm"
          variant={value === option ? "default" : "outline"}
          onClick={() => onChange(option)}
        >
          {option}
        </Button>
      ))}
    </div>
  );
}
