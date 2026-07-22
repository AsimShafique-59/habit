import uuid
from django.conf import settings
from django.db import models


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=80, blank=True, help_text="Icon name or emoji")
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "insight_categories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class AudioContent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audio_contents",
        db_column="category_id",
    )
    audio_file = models.FileField(upload_to="insights/audio/")
    thumbnail = models.ImageField(upload_to="insights/thumbnails/", null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    tags = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "audio_content"
        ordering = ["-published_at"]

    def __str__(self):
        return self.title


class UserInsightInteraction(models.Model):
    """DI-004 — Tracks saves, favourites and personal notes per user per insight."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="insight_interactions",
    )
    audio_content = models.ForeignKey(
        AudioContent,
        on_delete=models.CASCADE,
        related_name="user_interactions",
    )
    is_saved = models.BooleanField(default=False)
    is_favorited = models.BooleanField(default=False)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_insight_interactions"
        unique_together = [("user", "audio_content")]

    def __str__(self):
        return f"{self.user_id} — {self.audio_content_id}"
