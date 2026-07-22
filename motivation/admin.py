from django.contrib import admin

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


class ProgramDayInline(admin.TabularInline):
    model = ProgramDay
    extra = 1
    fields = ["day_number", "title", "task_description", "reflection_prompt", "audio"]
    autocomplete_fields = []


@admin.register(BadHabitProgram)
class BadHabitProgramAdmin(admin.ModelAdmin):
    list_display = [
        "name", "slug", "habit_type", "program_length_days",
        "has_medical_risk", "is_active", "order",
    ]
    list_filter = ["is_active", "has_medical_risk", "habit_type"]
    search_fields = ["name", "slug", "habit_type"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProgramDayInline]
    ordering = ["order", "name"]


@admin.register(ProgramDay)
class ProgramDayAdmin(admin.ModelAdmin):
    list_display = ["program", "day_number", "title"]
    list_filter = ["program"]
    search_fields = ["title", "program__name"]
    ordering = ["program", "day_number"]


@admin.register(UserEnrollment)
class UserEnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        "user", "program", "status", "started_at",
        "slip_count", "triggers_captured", "enrolled_at",
    ]
    list_filter = ["status", "program", "triggers_captured"]
    search_fields = ["user__email", "program__name"]
    readonly_fields = ["enrolled_at"]
    ordering = ["-enrolled_at"]


@admin.register(UserTrigger)
class UserTriggerAdmin(admin.ModelAdmin):
    list_display = ["enrollment", "trigger_type", "created_at"]
    list_filter = ["trigger_type"]
    search_fields = ["enrollment__user__email", "description"]
    ordering = ["-created_at"]


@admin.register(DayCompletion)
class DayCompletionAdmin(admin.ModelAdmin):
    list_display = ["enrollment", "day_number", "task_done", "completed_at"]
    list_filter = ["task_done"]
    search_fields = ["enrollment__user__email"]
    ordering = ["-completed_at"]


@admin.register(PersonalMotivation)
class PersonalMotivationAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "media_type", "enrollment", "created_at"]
    list_filter = ["media_type"]
    search_fields = ["user__email", "title"]
    ordering = ["-created_at"]


@admin.register(QuitReason)
class QuitReasonAdmin(admin.ModelAdmin):
    list_display = ["enrollment", "text", "order", "created_at"]
    search_fields = ["enrollment__user__email", "text"]
    ordering = ["enrollment", "order"]


@admin.register(UrgeSOS)
class UrgeSosAdmin(admin.ModelAdmin):
    list_display = [
        "enrollment", "activated_at",
        "breathing_completed", "audio_played", "accountability_message_sent",
    ]
    list_filter = ["breathing_completed", "audio_played", "accountability_message_sent"]
    search_fields = ["enrollment__user__email"]
    ordering = ["-activated_at"]

