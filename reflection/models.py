"""Models for the reflection app."""
import uuid
from datetime import date

from django.conf import settings
from django.db import models


class ReflectionPrompt(models.Model):
    """Admin-managed daily reflection prompt."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.TextField()
    date = models.DateField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reflection_prompts"
        ordering = ["-date"]

    def __str__(self):
        return f"Prompt {self.date}: {self.text[:60]}"


class MoodLog(models.Model):
    """Daily mood check-in (one per user per day)."""

    EMOJI_LABELS = {
        1: "awful",
        2: "bad",
        3: "okay",
        4: "good",
        5: "great",
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mood_logs",
    )
    score = models.PositiveSmallIntegerField()
    emoji_label = models.CharField(max_length=20, blank=True)
    logged_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField()
    note = models.TextField(blank=True)

    class Meta:
        db_table = "mood_logs"
        ordering = ["-date"]
        unique_together = [("user", "date")]

    def save(self, *args, **kwargs):
        if not self.date:
            self.date = date.today()
        self.emoji_label = self.EMOJI_LABELS.get(self.score, "")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user_id} – {self.score} on {self.date}"


class JournalEntry(models.Model):
    """Free-text journal entry with optional habit tags and mood link."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="journal_entries",
    )
    prompt = models.ForeignKey(
        ReflectionPrompt,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="journal_entries",
    )
    # TODO: encrypt `text` at rest using Fernet before storing (store ciphertext, decrypt on read)
    text = models.TextField()
    mood = models.ForeignKey(
        MoodLog,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="journal_entries",
    )
    habits = models.ManyToManyField(
        "habits.Habit",
        blank=True,
        through="JournalHabitTag",
        related_name="journal_entries",
    )
    entry_date = models.DateField(default=date.today)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "journal_entries"
        ordering = ["-entry_date"]

    def __str__(self):
        return f"{self.user_id} – journal {self.entry_date}"


class JournalHabitTag(models.Model):
    """Through table linking journal entries to habits."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="habit_tags",
    )
    habit = models.ForeignKey(
        "habits.Habit",
        on_delete=models.CASCADE,
        related_name="journal_tags",
    )

    class Meta:
        db_table = "journal_habit_tags"
        unique_together = [("journal_entry", "habit")]

    def __str__(self):
        return f"Entry {self.journal_entry_id} → Habit {self.habit_id}"
