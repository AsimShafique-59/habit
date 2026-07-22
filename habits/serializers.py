"""Serializers for the habits app."""
import re

from rest_framework import serializers

from .models import Habit, HabitCompletion, VacationPeriod


# ---------------------------------------------------------------------------
# Output serializers
# ---------------------------------------------------------------------------

class HabitSerializer(serializers.ModelSerializer):
    """Full habit output, used in list/detail responses."""

    anchor_habit_id = serializers.SerializerMethodField()
    user_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Habit
        fields = [
            "id",
            "user_id",
            "title",
            "description",
            "category",
            "icon",
            "color_hex",
            "frequency_type",
            "frequency_days",
            "frequency_count",
            "quantity_target",
            "quantity_unit",
            "duration_minutes",
            "time_window_start",
            "time_window_end",
            "identity_tags",
            "difficulty",
            "anchor_habit_id",
            "reminder_times",
            "is_quit_habit",
            "current_streak",
            "longest_streak",
            "streak_freezes_available",
            "is_archived",
            "archived_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_anchor_habit_id(self, obj):
        return str(obj.anchor_habit_id) if obj.anchor_habit_id else None


class HabitCompletionSerializer(serializers.ModelSerializer):
    """Completion record output."""

    class Meta:
        model = HabitCompletion
        fields = [
            "id",
            "habit_id",
            "user_id",
            "completion_date",
            "quantity",
            "completed_at",
            "source",
            "client_id",
            "streak_freeze_used",
        ]
        read_only_fields = fields


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ["id", "user_id", "start_date", "end_date", "created_at"]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Input serializers
# ---------------------------------------------------------------------------

class HabitCreateSerializer(serializers.Serializer):
    """Validates input for habit creation (POST) and update (PATCH via partial=True)."""

    title = serializers.CharField(max_length=80)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    category = serializers.ChoiceField(choices=[c[0] for c in Habit.CATEGORY_CHOICES])
    icon = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    color_hex = serializers.CharField(max_length=7, required=False, default="#4F46E5")
    frequency_type = serializers.ChoiceField(choices=[c[0] for c in Habit.FREQUENCY_CHOICES])
    frequency_days = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=7),
        required=False,
        default=list,
    )
    frequency_count = serializers.IntegerField(min_value=1, max_value=7, required=False, default=1)
    quantity_target = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True, default=None
    )
    quantity_unit = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    duration_minutes = serializers.IntegerField(min_value=1, required=False, allow_null=True, default=None)
    time_window_start = serializers.TimeField(required=False, allow_null=True, default=None)
    time_window_end = serializers.TimeField(required=False, allow_null=True, default=None)
    identity_tags = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    difficulty = serializers.ChoiceField(
        choices=[c[0] for c in Habit.DIFFICULTY_CHOICES], required=False, default="small"
    )
    anchor_habit_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    reminder_times = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    is_quit_habit = serializers.BooleanField(required=False, default=False)

    def validate_color_hex(self, value):
        if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise serializers.ValidationError("color_hex must be in #RRGGBB format.")
        return value

    def validate_identity_tags(self, value):
        if len(value) > 5:
            raise serializers.ValidationError("Maximum 5 identity tags allowed.")
        return value

    def validate_reminder_times(self, value):
        if len(value) > 3:
            raise serializers.ValidationError("Maximum 3 reminder times allowed.")
        for t in value:
            if not re.match(r"^\d{2}:\d{2}$", t):
                raise serializers.ValidationError(
                    f"Invalid reminder time '{t}'. Use HH:MM format."
                )
        return value

    def validate(self, data):
        frequency_type = data.get("frequency_type")
        frequency_days = data.get("frequency_days", [])
        frequency_count = data.get("frequency_count", 1)
        time_start = data.get("time_window_start")
        time_end = data.get("time_window_end")

        if frequency_type == "weekdays" and not frequency_days:
            raise serializers.ValidationError(
                {"frequency_days": "frequency_days is required for weekdays frequency type."}
            )
        if frequency_type == "n_per_week" and not (1 <= frequency_count <= 7):
            raise serializers.ValidationError(
                {"frequency_count": "frequency_count must be 1–7 for n_per_week."}
            )
        if time_start and time_end and time_start >= time_end:
            raise serializers.ValidationError(
                {"time_window_start": "time_window_start must be before time_window_end."}
            )
        return data


class BatchCompletionItemSerializer(serializers.Serializer):
    """Single item in a batch completion sync request."""

    habit_id = serializers.UUIDField()
    completion_date = serializers.DateField()
    quantity = serializers.DecimalField(max_digits=8, decimal_places=2, default=1)
    completed_at = serializers.DateTimeField()
    client_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    source = serializers.ChoiceField(
        choices=[c[0] for c in HabitCompletion.SOURCE_CHOICES], default="manual"
    )
