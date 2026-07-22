from django.contrib import admin

from .models import Habit, HabitCompletion, StreakEvent, VacationPeriod


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "frequency_type", "is_archived", "current_streak", "created_at")
    list_filter = ("category", "frequency_type", "difficulty", "is_archived", "is_quit_habit")
    search_fields = ("title", "user__email")
    raw_id_fields = ("user", "anchor_habit")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(HabitCompletion)
class HabitCompletionAdmin(admin.ModelAdmin):
    list_display = ("habit", "user", "completion_date", "quantity", "source", "streak_freeze_used")
    list_filter = ("source", "streak_freeze_used")
    search_fields = ("habit__title", "user__email")
    raw_id_fields = ("habit", "user")
    readonly_fields = ("id",)


@admin.register(VacationPeriod)
class VacationPeriodAdmin(admin.ModelAdmin):
    list_display = ("user", "start_date", "end_date", "created_at")
    search_fields = ("user__email",)
    raw_id_fields = ("user",)
    readonly_fields = ("id", "created_at")


@admin.register(StreakEvent)
class StreakEventAdmin(admin.ModelAdmin):
    list_display = ("habit", "user", "event_type", "event_date", "streak_value", "created_at")
    list_filter = ("event_type",)
    search_fields = ("habit__title", "user__email")
    raw_id_fields = ("habit", "user")
    readonly_fields = ("id", "created_at")
