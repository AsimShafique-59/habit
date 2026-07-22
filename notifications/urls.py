from django.urls import path
from .views import (
    DeviceTokenView,
    NotificationListView,
    NotificationReadView,
    NotificationMarkAllReadView,
)

urlpatterns = [
    path("notifications/device-token/", DeviceTokenView.as_view(), name="notifications-device-token"),
    path("notifications/", NotificationListView.as_view(), name="notifications-list"),
    path("notifications/mark-all-read/", NotificationMarkAllReadView.as_view(), name="notifications-mark-all-read"),
    path("notifications/<uuid:pk>/read/", NotificationReadView.as_view(), name="notifications-read"),
]
