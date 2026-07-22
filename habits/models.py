"""Models for the habits app."""
import uuid

from django.conf import settings
from django.db import models


class Habit(models.Model):
    CATEGORY_CHOICES = [
        ("Health", "Health"),
        ("Fitness", "Fitness"),
        ("Mindfulness", "Mindfulness"),
        ("Productivity", "Productivity"),
        ("Learning", "Learning"),
        ("Finance", "Finance"),
        ("Relationships", "Relationships"),
        ("Other", "Other"),
    ]
    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekdays", "Weekdays"),
        ("n_per_week", "N Per Week"),
    ]
    DIFFICULTY_CHOICES = [
        ("tiny", "Tiny"),
        ("small", "Small"),
        ("medium", "Medium"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habits",
    )
    title = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    icon = models.CharField(max_length=80, blank=True)
    color_hex = models.CharField(max_length=7, default="#4F46E5")
    frequency_type = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    frequency_days = models.JSONField(default=list)
    frequency_count = models.PositiveIntegerField(default=1)
    quantity_target = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    quantity_unit = models.CharField(max_length=40, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    time_window_start = models.TimeField(null=True, blank=True)
    time_window_end = models.TimeField(null=True, blank=True)
    identity_tags = models.JSONField(default=list)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="small")
    anchor_habit = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="anchored_habits",
    )
    reminder_times = models.JSONField(default=list)
    is_quit_habit = models.BooleanField(default=False)
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    streak_freezes_available = models.PositiveIntegerField(default=0)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "habits"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} – {self.title}"


class HabitCompletion(models.Model):
    SOURCE_CHOICES = [
        ("manual", "Manual"),
        ("auto_health", "Auto Health"),
        ("widget", "Widget"),
        ("watch", "Watch"),
        ("shortcut", "Shortcut"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="completions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habit_completions",
    )
    completion_date = models.DateField()
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    completed_at = models.DateTimeField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="manual")
    client_id = models.UUIDField(null=True, blank=True)
    streak_freeze_used = models.BooleanField(default=False)

    class Meta:
        db_table = "habit_completions"
        unique_together = [("habit", "completion_date")]

    def __str__(self):
        return f"{self.habit_id} on {self.completion_date}"


class VacationPeriod(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vacation_periods",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vacation_periods"

    def __str__(self):
        return f"{self.user_id} vacation {self.start_date}–{self.end_date}"


class StreakEvent(models.Model):
    EVENT_CHOICES = [
        ("freeze_used", "Freeze Used"),
        ("freeze_earned", "Freeze Earned"),
        ("streak_broken", "Streak Broken"),
        ("streak_started", "Streak Started"),
        ("milestone", "Milestone"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="streak_events")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="streak_events",
    )
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    event_date = models.DateField()
    streak_value = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "streak_events"

    def __str__(self):
        return f"{self.habit_id} – {self.event_type} on {self.event_date}"
