"""Serializers for the motivation (bad-habit removal) app."""
from datetime import date

from rest_framework import serializers

from insights.models import AudioContent
from insights.serializers import AudioContentSerializer

from .models import (
    BadHabitProgram,
    DayCompletion,
    PersonalMotivation,
    ProgramDay,
    QuitReason,
    UrgeSOS,
    UserEnrollment,
    UserTrigger,
)


class ProgramDaySerializer(serializers.ModelSerializer):
    audio = AudioContentSerializer(read_only=True)

    class Meta:
        model = ProgramDay
        fields = [
            "id",
            "day_number",
            "title",
            "task_description",
            "reflection_prompt",
            "audio",
        ]


class BadHabitProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = BadHabitProgram
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "habit_type",
            "program_length_days",
            "has_medical_risk",
            "crisis_resource_url",
            "savings_unit",
            "savings_per_day",
            "savings_money_per_unit",
            "calories_per_unit",
            "is_active",
            "order",
            "created_at",
            "updated_at",
        ]


class BadHabitProgramDetailSerializer(BadHabitProgramSerializer):
    days = ProgramDaySerializer(many=True, read_only=True)

    class Meta(BadHabitProgramSerializer.Meta):
        fields = BadHabitProgramSerializer.Meta.fields + ["days"]


class UserEnrollmentSerializer(serializers.ModelSerializer):
    program = BadHabitProgramSerializer(read_only=True)
    current_day = serializers.SerializerMethodField()
    days_since_last_slip = serializers.SerializerMethodField()
    savings = serializers.SerializerMethodField()

    class Meta:
        model = UserEnrollment
        fields = [
            "id",
            "program",
            "status",
            "enrolled_at",
            "started_at",
            "completed_at",
            "last_slip_at",
            "slip_count",
            "replacement_habit_id",
            "triggers_captured",
            "current_day",
            "days_since_last_slip",
            "savings",
        ]

    def get_current_day(self, obj):
        today = date.today()
        day = (today - obj.started_at).days + 1
        return min(day, obj.program.program_length_days)

    def get_days_since_last_slip(self, obj):
        today = date.today()
        if obj.last_slip_at:
            return (today - obj.last_slip_at).days
        return (today - obj.started_at).days

    def get_savings(self, obj):
        program = obj.program
        today = date.today()
        days_clean = (today - obj.started_at).days
        units_saved = program.savings_per_day * days_clean
        money_saved = float(program.savings_money_per_unit) * units_saved
        calories_saved = program.calories_per_unit * units_saved
        return {
            "units_saved": round(units_saved, 2),
            "money_saved": round(money_saved, 2),
            "calories_saved": round(calories_saved, 2),
            "unit_label": program.savings_unit,
        }


class UserEnrollmentCreateSerializer(serializers.Serializer):
    program_slug = serializers.SlugField()
    replacement_habit_id = serializers.UUIDField(required=False, allow_null=True)


class DayCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DayCompletion
        fields = [
            "id",
            "enrollment",
            "day_number",
            "completed_at",
            "task_done",
            "reflection_response",
        ]
        read_only_fields = ["id", "enrollment", "day_number", "completed_at", "task_done"]


class UserTriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTrigger
        fields = ["id", "trigger_type", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class QuitReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuitReason
        fields = ["id", "text", "order", "created_at"]
        read_only_fields = ["id", "created_at"]


class UrgeSosSerializer(serializers.ModelSerializer):
    class Meta:
        model = UrgeSOS
        fields = [
            "id",
            "enrollment",
            "activated_at",
            "breathing_completed",
            "audio_played",
            "accountability_message_sent",
        ]
        read_only_fields = ["id", "enrollment", "activated_at"]


class PersonalMotivationSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = PersonalMotivation
        fields = ["id", "title", "media_type", "file", "file_url", "created_at"]
        read_only_fields = ["id", "created_at", "file_url"]
        extra_kwargs = {"file": {"write_only": True}}

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class AdminProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = BadHabitProgram
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "habit_type",
            "program_length_days",
            "has_medical_risk",
            "crisis_resource_url",
            "savings_unit",
            "savings_per_day",
            "savings_money_per_unit",
            "calories_per_unit",
            "is_active",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AdminProgramDaySerializer(serializers.ModelSerializer):
    audio_detail = AudioContentSerializer(source="audio", read_only=True)
    audio = serializers.PrimaryKeyRelatedField(
        queryset=AudioContent.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ProgramDay
        fields = [
            "id",
            "program",
            "day_number",
            "title",
            "task_description",
            "reflection_prompt",
            "audio",
            "audio_detail",
        ]
        read_only_fields = ["id", "program"]
