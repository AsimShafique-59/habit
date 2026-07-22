from django.contrib import admin
from .models import AudioContent, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "is_active", "created_at")
    list_editable = ("order", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "created_at")


@admin.register(AudioContent)
class AudioContentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "duration_seconds", "is_published", "published_at", "created_at")
    list_filter = ("category", "is_published")
    search_fields = ("title", "description")
    list_editable = ("is_published",)
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("id", "title", "description", "category")}),
        ("Media", {"fields": ("audio_file", "thumbnail", "duration_seconds")}),
        ("Publishing", {"fields": ("is_published", "published_at", "tags")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
