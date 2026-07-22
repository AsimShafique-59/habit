"""Serializers for the reflection app."""
from datetime import date

from rest_framework import serializers

from habits.models import Habit

from .models import JournalEntry, JournalHabitTag, MoodLog, ReflectionPrompt


# ---------------------------------------------------------------------------
# ReflectionPrompt
# ---------------------------------------------------------------------------

class ReflectionPromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReflectionPrompt
        fields = ["id", "text", "date", "is_active"]
        read_only_fields = ["id"]


class ReflectionPromptCreateSerializer(serializers.Serializer):
    text = serializers.CharField()
    date = serializers.DateField()
    is_active = serializers.BooleanField(default=True)


class ReflectionPromptUpdateSerializer(serializers.Serializer):
    text = serializers.CharField(required=False)
    date = serializers.DateField(required=False)
    is_active = serializers.BooleanField(required=False)


# ---------------------------------------------------------------------------
# MoodLog
# ---------------------------------------------------------------------------

class MoodLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoodLog
        fields = ["id", "score", "emoji_label", "note", "logged_at", "date"]
        read_only_fields = fields


class MoodLogCreateSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=1, max_value=5)
    note = serializers.CharField(required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# JournalEntry
# ---------------------------------------------------------------------------

class HabitMinimalSerializer(serializers.ModelSerializer):
    """Minimal habit info embedded in journal entry responses."""

    class Meta:
        model = Habit
        fields = ["id", "title"]
        read_only_fields = fields


class JournalEntrySerializer(serializers.ModelSerializer):
    """Full read serializer with nested prompt, mood, and habits."""

    prompt = ReflectionPromptSerializer(read_only=True)
    mood = MoodLogSerializer(read_only=True)
    habits = HabitMinimalSerializer(many=True, read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            "id",
            "prompt",
            "text",
            "mood",
            "habits",
            "entry_date",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class JournalEntryCreateSerializer(serializers.Serializer):
    text = serializers.CharField()
    prompt_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    mood_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    habit_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )
    entry_date = serializers.DateField(required=False, default=date.today)


class JournalEntryUpdateSerializer(serializers.Serializer):
    text = serializers.CharField(required=False)
    habit_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False
    )


# ---------------------------------------------------------------------------
# MoodSummary
# ---------------------------------------------------------------------------

class MoodSummarySerializer(serializers.Serializer):
    average_score = serializers.FloatField()
    total_logs = serializers.IntegerField()
    by_score = serializers.DictField(child=serializers.IntegerField())
    streak_days = serializers.IntegerField()
