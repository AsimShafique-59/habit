from django.urls import path

from .views import (
    BatchSyncView,
    HabitArchiveView,
    HabitCompletionUndoView,
    HabitCompletionView,
    HabitDetailView,
    HabitListCreateView,
    HabitReminderView,
    HabitUnarchiveView,
    VacationDetailView,
    VacationView,
)

urlpatterns = [
    path("habits/", HabitListCreateView.as_view(), name="habits-list-create"),
    path("habits/completions/batch/", BatchSyncView.as_view(), name="habits-completions-batch"),
    path("habits/<uuid:habit_id>/", HabitDetailView.as_view(), name="habits-detail"),
    path("habits/<uuid:habit_id>/archive/", HabitArchiveView.as_view(), name="habits-archive"),
    path("habits/<uuid:habit_id>/unarchive/", HabitUnarchiveView.as_view(), name="habits-unarchive"),
    path("habits/<uuid:habit_id>/reminders/", HabitReminderView.as_view(), name="habits-reminders"),
    path("habits/<uuid:habit_id>/completions/", HabitCompletionView.as_view(), name="habits-completions"),
    path(
        "habits/<uuid:habit_id>/completions/<uuid:completion_id>/",
        HabitCompletionUndoView.as_view(),
        name="habits-completions-undo",
    ),
    path("auth/users/me/vacation/", VacationView.as_view(), name="vacation-list-create"),
    path("auth/users/me/vacation/<uuid:pk>/", VacationDetailView.as_view(), name="vacation-detail"),
]
