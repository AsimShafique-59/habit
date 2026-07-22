"""Models for the motivation (bad-habit removal) app."""
import uuid

from django.conf import settings
from django.db import models


class BadHabitProgram(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    habit_type = models.CharField(max_length=50)
    program_length_days = models.PositiveIntegerField()
    has_medical_risk = models.BooleanField(default=False)
    crisis_resource_url = models.URLField(blank=True)
    savings_unit = models.CharField(max_length=50, blank=True)
    savings_per_day = models.FloatField(default=0)
    savings_money_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    calories_per_unit = models.FloatField(default=0)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "motivation_programs"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class ProgramDay(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(
        BadHabitProgram,
        on_delete=models.CASCADE,
        related_name="days",
    )
    day_number = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    task_description = models.TextField()
    reflection_prompt = models.TextField()
    audio = models.ForeignKey(
        "insights.AudioContent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="program_days",
    )

    class Meta:
        db_table = "motivation_program_days"
        ordering = ["day_number"]
        unique_together = [("program", "day_number")]

    def __str__(self):
        return f"{self.program.name} – Day {self.day_number}: {self.title}"


class UserEnrollment(models.Model):
    STATUS_ENROLLED = "enrolled"
    STATUS_COMPLETED = "completed"
    STATUS_ABANDONED = "abandoned"
    STATUS_CHOICES = [
        (STATUS_ENROLLED, "Enrolled"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_ABANDONED, "Abandoned"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="motivation_enrollments",
    )
    program = models.ForeignKey(
        BadHabitProgram,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ENROLLED)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_slip_at = models.DateField(null=True, blank=True)
    slip_count = models.PositiveIntegerField(default=0)
    replacement_habit_id = models.UUIDField(null=True, blank=True)
    triggers_captured = models.BooleanField(default=False)

    class Meta:
        db_table = "motivation_enrollments"
        unique_together = [("user", "program")]

    def __str__(self):
        return f"{self.user_id} → {self.program.name} ({self.status})"


class UserTrigger(models.Model):
    TRIGGER_EMOTION = "emotion"
    TRIGGER_LOCATION = "location"
    TRIGGER_TIME = "time"
    TRIGGER_PERSON = "person"
    TRIGGER_SITUATION = "situation"
    TRIGGER_CHOICES = [
        (TRIGGER_EMOTION, "Emotion"),
        (TRIGGER_LOCATION, "Location"),
        (TRIGGER_TIME, "Time"),
        (TRIGGER_PERSON, "Person"),
        (TRIGGER_SITUATION, "Situation"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        UserEnrollment,
        on_delete=models.CASCADE,
        related_name="triggers",
    )
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_CHOICES)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "motivation_triggers"

    def __str__(self):
        return f"{self.enrollment_id} – {self.trigger_type}"


class DayCompletion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        UserEnrollment,
        on_delete=models.CASCADE,
        related_name="completions",
    )
    day_number = models.PositiveIntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)
    task_done = models.BooleanField(default=True)
    reflection_response = models.TextField(blank=True)

    class Meta:
        db_table = "motivation_day_completions"
        unique_together = [("enrollment", "day_number")]

    def __str__(self):
        return f"{self.enrollment_id} – Day {self.day_number}"


class PersonalMotivation(models.Model):
    MEDIA_AUDIO = "audio"
    MEDIA_IMAGE = "image"
    MEDIA_CHOICES = [
        (MEDIA_AUDIO, "Audio"),
        (MEDIA_IMAGE, "Image"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="personal_motivations",
    )
    enrollment = models.ForeignKey(
        UserEnrollment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="personal_motivations",
    )
    title = models.CharField(max_length=200)
    media_type = models.CharField(max_length=10, choices=MEDIA_CHOICES)
    file = models.FileField(upload_to="motivation/personal/%Y/%m/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "motivation_personal_media"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} – {self.title}"


class QuitReason(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        UserEnrollment,
        on_delete=models.CASCADE,
        related_name="quit_reasons",
    )
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "motivation_quit_reasons"
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.enrollment_id} – {self.text[:50]}"


class UrgeSOS(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        UserEnrollment,
        on_delete=models.CASCADE,
        related_name="sos_activations",
    )
    activated_at = models.DateTimeField(auto_now_add=True)
    breathing_completed = models.BooleanField(default=False)
    audio_played = models.BooleanField(default=False)
    accountability_message_sent = models.BooleanField(default=False)

    class Meta:
        db_table = "motivation_urge_sos"
        ordering = ["-activated_at"]

    def __str__(self):
        return f"{self.enrollment_id} SOS @ {self.activated_at}"

