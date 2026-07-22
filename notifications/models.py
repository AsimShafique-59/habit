import uuid
from django.conf import settings
from django.db import models


class Platform(models.TextChoices):
    IOS = "ios", "iOS"
    ANDROID = "android", "Android"


class NotificationType(models.TextChoices):
    HABIT_REMINDER = "habit_reminder", "Habit Reminder"
    STREAK_ALERT = "streak_alert", "Streak Alert"
    ACHIEVEMENT = "achievement", "Achievement"
    DAILY_INSIGHT = "daily_insight", "Daily Insight"
    SYSTEM = "system", "System"


class DeviceToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="device_tokens"
    )
    token = models.TextField(unique=True)
    platform = models.CharField(max_length=10, choices=Platform.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "device_tokens"

    def __str__(self):
        return f"{self.user.email} — {self.platform}"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=120)
    body = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    data = models.JSONField(default=dict, blank=True)   # extra payload for mobile
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} — {self.title}"
