"""Models for the integrations app."""
import uuid

from django.conf import settings
from django.db import models


class IntegrationConsent(models.Model):
    INTEGRATION_TYPE_CHOICES = [
        ("apple_health", "Apple Health"),
        ("google_fit", "Google Fit"),
        ("apple_calendar", "Apple Calendar"),
        ("google_calendar", "Google Calendar"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="integration_consents",
    )
    integration_type = models.CharField(max_length=20, choices=INTEGRATION_TYPE_CHOICES)
    is_enabled = models.BooleanField(default=False)
    granted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    data_categories = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration_consents"
        unique_together = ("user", "integration_type")
        ordering = ["integration_type"]

    def __str__(self):
        return f"{self.user_id} – {self.integration_type} ({'on' if self.is_enabled else 'off'})"


class HealthDataPoint(models.Model):
    SOURCE_CHOICES = [
        ("apple_health", "Apple Health"),
        ("google_fit", "Google Fit"),
    ]
    METRIC_CHOICES = [
        ("steps", "Steps"),
        ("sleep_minutes", "Sleep Minutes"),
        ("workout_minutes", "Workout Minutes"),
        ("mindful_minutes", "Mindful Minutes"),
        ("water_ml", "Water (ml)"),
        ("weight_kg", "Weight (kg)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="health_data_points",
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    value = models.FloatField()
    recorded_date = models.DateField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "health_data_points"
        unique_together = ("user", "source", "metric", "recorded_date")
        ordering = ["-recorded_date"]

    def __str__(self):
        return f"{self.user_id} – {self.source}/{self.metric} on {self.recorded_date}"


class CalendarBlock(models.Model):
    SOURCE_CHOICES = [
        ("apple_calendar", "Apple Calendar"),
        ("google_calendar", "Google Calendar"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar_blocks",
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "calendar_blocks"
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.user_id} – {self.source} {self.start_time} to {self.end_time}"


class WidgetSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="widget_snapshot",
    )
    habits_today = models.JSONField(default=list)
    streak_count = models.PositiveIntegerField(default=0)
    momentum_index_7d = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "widget_snapshots"

    def __str__(self):
        return f"{self.user_id} – widget snapshot"
