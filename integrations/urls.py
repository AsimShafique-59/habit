"""URL configuration for the integrations app."""
from django.urls import path

from .views import (
    CalendarSyncView,
    ConsentView,
    HealthDataView,
    HealthSyncView,
    IntegrationListView,
    NotificationSuppressionView,
    WidgetRefreshView,
    WidgetSnapshotView,
)

urlpatterns = [
    # Specific paths MUST come before the generic <str:integration_type> path
    path("integrations/health/sync/", HealthSyncView.as_view()),
    path("integrations/health/", HealthDataView.as_view()),
    path("integrations/calendar/sync/", CalendarSyncView.as_view()),
    path("integrations/calendar/suppress-now/", NotificationSuppressionView.as_view()),
    path("integrations/widget/snapshot/", WidgetSnapshotView.as_view()),
    path("integrations/widget/refresh/", WidgetRefreshView.as_view()),
    # Generic paths
    path("integrations/", IntegrationListView.as_view()),
    path("integrations/<str:integration_type>/consent/", ConsentView.as_view()),
]
