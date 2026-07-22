"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Flame, HeartPulse, Loader2, Plus, Shield, Sparkles } from "lucide-react";
import { toast } from "sonner";

import {
  activateSos,
  addQuitReason,
  completeProgramDay,
  enrollInProgram,
  getTodayProgramDay,
  listEnrollments,
  listPrograms,
  listQuitReasons,
  logSlip,
  type BadHabitProgram,
  type ProgramDay,
  type QuitReason,
  type UserEnrollment,
} from "@/lib/api/motivation";
import { ApiError } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

export default function MotivationPage() {
  const [programs, setPrograms] = useState<BadHabitProgram[]>([]);
  const [enrollments, setEnrollments] = useState<UserEnrollment[]>([]);
  const [selectedEnrollmentId, setSelectedEnrollmentId] = useState<string | null>(null);
  const [today, setToday] = useState<ProgramDay | null>(null);
  const [reasons, setReasons] = useState<QuitReason[]>([]);
  const [reasonText, setReasonText] = useState("");
  const [reflection, setReflection] = useState("");
  const [sos, setSos] = useState<Awaited<ReturnType<typeof activateSos>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [programRes, enrollmentRes] = await Promise.all([listPrograms(), listEnrollments()]);
      setPrograms(programRes);
      setEnrollments(enrollmentRes);
      setSelectedEnrollmentId((current) => current ?? enrollmentRes[0]?.id ?? null);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not load motivation.";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const selectedEnrollment = useMemo(
    () => enrollments.find((item) => item.id === selectedEnrollmentId) ?? null,
    [enrollments, selectedEnrollmentId],
  );

  useEffect(() => {
    if (!selectedEnrollmentId) {
      setToday(null);
      setReasons([]);
      return;
    }
    let cancelled = false;
    Promise.all([
      getTodayProgramDay(selectedEnrollmentId).catch(() => null),
      listQuitReasons(selectedEnrollmentId).catch(() => []),
    ]).then(([day, reasonRes]) => {
      if (cancelled) return;
      setToday(day);
      setReasons(reasonRes);
    });
    return () => {
      cancelled = true;
    };
  }, [selectedEnrollmentId]);

  async function handleEnroll(program: BadHabitProgram) {
    setPending(program.slug);
    try {
      const enrollment = await enrollInProgram(program.slug);
      setEnrollments((prev) => [enrollment, ...prev]);
      setSelectedEnrollmentId(enrollment.id);
      toast.success(`Enrolled in ${program.name}.`);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not enroll.";
      toast.error(message);
    } finally {
      setPending(null);
    }
  }

  async function handleCompleteDay() {
    if (!selectedEnrollment) return;
    setPending("complete");
    try {
      await completeProgramDay(selectedEnrollment.id, reflection);
      setReflection("");
      await load();
      toast.success("Program day completed.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not complete day.";
      toast.error(message);
    } finally {
      setPending(null);
    }
  }

  async function handleSlip() {
    if (!selectedEnrollment) return;
    setPending("slip");
    try {
      const result = await logSlip(selectedEnrollment.id);
      setEnrollments((prev) =>
        prev.map((item) =>
          item.id === selectedEnrollment.id
            ? { ...item, slip_count: result.slip_count, days_since_last_slip: result.days_since_last_slip }
            : item,
        ),
      );
      toast.success(result.encouragement);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not log slip.";
      toast.error(message);
    } finally {
      setPending(null);
    }
  }

  async function handleSos() {
    if (!selectedEnrollment) return;
    setPending("sos");
    try {
      setSos(await activateSos(selectedEnrollment.id));
      toast.success("SOS activated.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not activate SOS.";
      toast.error(message);
    } finally {
      setPending(null);
    }
  }

  async function handleReason() {
    if (!selectedEnrollment || !reasonText.trim()) return;
    setPending("reason");
    try {
      const reason = await addQuitReason(selectedEnrollment.id, reasonText.trim());
      setReasons((prev) => [...prev, reason]);
      setReasonText("");
      toast.success("Reason added.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not add reason.";
      toast.error(message);
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-4 p-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Motivation</h1>
        <p className="text-sm text-muted-foreground">Programs, daily tasks, reasons, slip recovery, and SOS support.</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Sparkles className="h-4 w-4" />
              Programs
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)
            ) : programs.length === 0 ? (
              <p className="py-8 text-sm text-muted-foreground">No programs available.</p>
            ) : (
              programs.map((program) => {
                const enrolled = enrollments.some((item) => item.program.slug === program.slug);
                return (
                  <div key={program.id} className="rounded-md border px-3 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium">{program.name}</p>
                        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{program.description}</p>
                      </div>
                      <Badge variant={program.has_medical_risk ? "destructive" : "secondary"}>
                        {program.program_length_days}d
                      </Badge>
                    </div>
                    <Button
                      size="sm"
                      className="mt-3"
                      variant={enrolled ? "outline" : "default"}
                      onClick={() => (enrolled ? setSelectedEnrollmentId(enrollments.find((item) => item.program.slug === program.slug)?.id ?? null) : handleEnroll(program))}
                      disabled={pending === program.slug}
                    >
                      {pending === program.slug ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                      {enrolled ? "Open" : "Enroll"}
                    </Button>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm font-medium">
                <Flame className="h-4 w-4" />
                Current Enrollment
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {!selectedEnrollment ? (
                <p className="py-8 text-sm text-muted-foreground">No active enrollment selected.</p>
              ) : (
                <>
                  <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
                    <div>
                      <p className="text-base font-semibold">{selectedEnrollment.program.name}</p>
                      <p className="text-sm text-muted-foreground">
                        Day {selectedEnrollment.current_day} of {selectedEnrollment.program.program_length_days}
                      </p>
                    </div>
                    <Badge>{selectedEnrollment.status}</Badge>
                  </div>
                  <Progress value={(selectedEnrollment.current_day / selectedEnrollment.program.program_length_days) * 100} />
                  <div className="grid gap-3 sm:grid-cols-3">
                    <Metric label="Clean days" value={String(selectedEnrollment.days_since_last_slip)} />
                    <Metric label="Slips" value={String(selectedEnrollment.slip_count)} />
                    <Metric label="Saved" value={`$${selectedEnrollment.savings.money_saved}`} />
                  </div>
                  {today ? (
                    <div className="rounded-md border px-3 py-3">
                      <p className="text-sm font-medium">{today.title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{today.task_description}</p>
                      <p className="mt-3 text-xs font-medium text-muted-foreground">{today.reflection_prompt}</p>
                      <Textarea value={reflection} onChange={(event) => setReflection(event.target.value)} className="mt-2 min-h-20" />
                      <div className="mt-3 flex flex-wrap gap-2">
                        <Button size="sm" onClick={handleCompleteDay} disabled={pending === "complete"}>
                          {pending === "complete" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Shield className="h-4 w-4" />}
                          Complete day
                        </Button>
                        <Button size="sm" variant="outline" onClick={handleSlip} disabled={pending === "slip"}>
                          Log slip
                        </Button>
                        <Button size="sm" variant="outline" onClick={handleSos} disabled={pending === "sos"}>
                          <HeartPulse className="h-4 w-4" />
                          SOS
                        </Button>
                      </div>
                    </div>
                  ) : null}
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Quit Reasons</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                <Input value={reasonText} onChange={(event) => setReasonText(event.target.value)} />
                <Button onClick={handleReason} disabled={!selectedEnrollment || pending === "reason" || !reasonText.trim()}>
                  Add
                </Button>
              </div>
              {reasons.length === 0 ? (
                <p className="text-sm text-muted-foreground">No reasons saved.</p>
              ) : (
                reasons.map((reason) => (
                  <div key={reason.id} className="rounded-md border px-3 py-2 text-sm">{reason.text}</div>
                ))
              )}
            </CardContent>
          </Card>

          {sos ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">SOS Session</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Badge variant="secondary">{sos.breathing_exercise.pattern}</Badge>
                <p className="text-sm text-muted-foreground">{sos.breathing_exercise.instructions}</p>
                {sos.urge_surfing_audio_url ? <audio controls src={sos.urge_surfing_audio_url} className="h-9 w-full" /> : null}
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border px-3 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-semibold tracking-tight">{value}</p>
    </div>
  );
}
