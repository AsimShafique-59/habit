from django.urls import path

from .views import (
    AdminPromptDetailView,
    AdminPromptListCreateView,
    JournalDetailView,
    JournalListCreateView,
    MoodSummaryView,
    MoodView,
    TodayPromptView,
)

urlpatterns = [
    path("reflection/prompt/today/", TodayPromptView.as_view(), name="reflection-prompt-today"),
    # mood/summary/ MUST come before mood/ to avoid routing conflict
    path("reflection/mood/summary/", MoodSummaryView.as_view(), name="reflection-mood-summary"),
    path("reflection/mood/", MoodView.as_view(), name="reflection-mood"),
    path("reflection/journal/", JournalListCreateView.as_view(), name="reflection-journal"),
    path("reflection/journal/<uuid:pk>/", JournalDetailView.as_view(), name="reflection-journal-detail"),
    path("reflection/manage/prompts/", AdminPromptListCreateView.as_view(), name="reflection-admin-prompts"),
    path("reflection/manage/prompts/<uuid:pk>/", AdminPromptDetailView.as_view(), name="reflection-admin-prompt-detail"),
]
