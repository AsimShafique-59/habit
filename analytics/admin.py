"""Admin configuration for the analytics app."""
from django.contrib import admin

from .models import DailyAggregation, WeeklyReport


@admin.register(DailyAggregation)
class DailyAggregationAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "total_habits", "completed_habits", "completion_rate", "mood_score")
    list_filter = ("date",)
    search_fields = ("user__email",)
    ordering = ("-date",)
    date_hierarchy = "date"


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ("user", "week_start", "week_end", "completion_rate", "best_day", "worst_day", "mood_average", "generated_at")
    list_filter = ("week_start",)
    search_fields = ("user__email",)
    ordering = ("-week_start",)
    date_hierarchy = "week_start"
    readonly_fields = ("generated_at",)

