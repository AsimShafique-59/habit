from django.contrib import admin

from .models import JournalEntry, MoodLog, ReflectionPrompt


@admin.register(ReflectionPrompt)
class ReflectionPromptAdmin(admin.ModelAdmin):
    list_display = ("text", "date", "is_active")
    list_filter = ("is_active",)
    search_fields = ("text",)


@admin.register(MoodLog)
class MoodLogAdmin(admin.ModelAdmin):
    list_display = ("user", "score", "emoji_label", "date")
    list_filter = ("score",)
    search_fields = ("user__email",)


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "entry_date", "is_deleted")
    list_filter = ("is_deleted",)
    search_fields = ("user__email",)
