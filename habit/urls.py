from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Apps
    path("", include("authentication.urls")),
    path("", include("habits.urls")),
    path("", include("ai.urls")),
    path("", include("analytics.urls")),
    path("", include("notifications.urls")),
    path("", include("motivation.urls")),
    path("", include("insights.urls")),
    path("", include("reflection.urls")),
    path("", include("subscriptions.urls")),
    path("", include("integrations.urls")),

    # Docs
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

