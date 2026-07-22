from django.urls import path
from .views import (
    CategoryListView,
    CategoryAudioListView,
    AudioContentListView,
    AudioContentDetailView,
    AdminCategoryListView,
    AdminCategoryDetailView,
    AdminAudioContentListView,
    AdminAudioContentDetailView,
    InsightSaveView,
    InsightFavoriteView,
    InsightNoteView,
    InsightDownloadView,
)

urlpatterns = [
    # User endpoints
    path("insights/categories/", CategoryListView.as_view(), name="insights-categories"),
    path("insights/categories/<slug:slug>/audios/", CategoryAudioListView.as_view(), name="insights-category-audios"),
    path("insights/", AudioContentListView.as_view(), name="insights-list"),
    path("insights/<uuid:pk>/", AudioContentDetailView.as_view(), name="insights-detail"),

    # DI-004 — Save / Favourite / Note
    path("insights/<uuid:pk>/save/", InsightSaveView.as_view(), name="insights-save"),
    path("insights/<uuid:pk>/favorite/", InsightFavoriteView.as_view(), name="insights-favorite"),
    path("insights/<uuid:pk>/note/", InsightNoteView.as_view(), name="insights-note"),

    # DI-006 — Offline download (premium)
    path("insights/<uuid:pk>/download/", InsightDownloadView.as_view(), name="insights-download"),

    # Admin: categories
    path("insights/manage/categories/", AdminCategoryListView.as_view(), name="admin-categories-list"),
    path("insights/manage/categories/<uuid:pk>/", AdminCategoryDetailView.as_view(), name="admin-categories-detail"),

    # Admin: audio
    path("insights/manage/", AdminAudioContentListView.as_view(), name="admin-insights-list"),
    path("insights/manage/<uuid:pk>/", AdminAudioContentDetailView.as_view(), name="admin-insights-detail"),
]
