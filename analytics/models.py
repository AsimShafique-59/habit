"""Models for the analytics app."""
import uuid

from django.conf import settings
from django.db import models


class DailyAggregation(models.Model):
    """Pre-aggregated daily statistics per user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_aggregations",
    )
    date = models.DateField()
    total_habits = models.PositiveIntegerField(default=0)
    completed_habits = models.PositiveIntegerField(default=0)
    completion_rate = models.FloatField(default=0.0)
    mood_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_daily_aggregations"
        unique_together = [("user", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user_id} – {self.date} ({self.completion_rate:.0%})"


class WeeklyReport(models.Model):
    """Auto-generated Sunday report summarising the week."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_reports",
    )
    week_start = models.DateField()   # Monday of the week
    week_end = models.DateField()     # Sunday of the week
    completion_rate = models.FloatField(default=0.0)
    best_day = models.CharField(max_length=20, blank=True)
    worst_day = models.CharField(max_length=20, blank=True)
    mood_average = models.FloatField(null=True, blank=True)
    narrative = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_weekly_reports"
        unique_together = [("user", "week_start")]
        ordering = ["-week_start"]

    def __str__(self):
        return f"{self.user_id} – week {self.week_start} / {self.week_end}"
