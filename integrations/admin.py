"""Admin configuration for the integrations app."""
from django.contrib import admin

from .models import CalendarBlock, HealthDataPoint, IntegrationConsent, WidgetSnapshot


@admin.register(IntegrationConsent)
class IntegrationConsentAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "integration_type", "is_enabled", "granted_at", "revoked_at", "updated_at"]
    list_filter = ["integration_type", "is_enabled"]
    search_fields = ["user__email"]
    ordering = ["user", "integration_type"]


@admin.register(HealthDataPoint)
class HealthDataPointAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "source", "metric", "value", "recorded_date", "recorded_at"]
    list_filter = ["source", "metric"]
    search_fields = ["user__email"]
    ordering = ["-recorded_date"]


@admin.register(CalendarBlock)
class CalendarBlockAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "source", "start_time", "end_time", "created_at"]
    list_filter = ["source"]
    search_fields = ["user__email"]
    ordering = ["start_time"]


@admin.register(WidgetSnapshot)
class WidgetSnapshotAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "streak_count", "momentum_index_7d", "updated_at"]
    search_fields = ["user__email"]
    ordering = ["-updated_at"]
