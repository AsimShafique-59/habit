from django.urls import path
from .views import (
    PlanListView,
    MySubscriptionView,
    AppleVerifyView,
    GoogleVerifyView,
    CancelSubscriptionView,
    AppleWebhookView,
    GoogleWebhookView,
    AdminPlanListCreateView,
    AdminPlanUpdateDeleteView,
    AdminGrantSubscriptionView,
    AdminUserSubscriptionDetailView,
)

urlpatterns = [
    # ── User endpoints ────────────────────────────────────────────────────────
    path("subscriptions/plans/", PlanListView.as_view(), name="sub_plans_list"),
    path("subscriptions/me/", MySubscriptionView.as_view(), name="sub_me_get"),
    path("subscriptions/apple/verify/", AppleVerifyView.as_view(), name="sub_apple_verify"),
    path("subscriptions/google/verify/", GoogleVerifyView.as_view(), name="sub_google_verify"),
    path("subscriptions/cancel/", CancelSubscriptionView.as_view(), name="sub_cancel"),

    # ── Webhook endpoints (no JWT auth) ───────────────────────────────────────
    path("subscriptions/webhooks/apple/", AppleWebhookView.as_view(), name="sub_webhook_apple"),
    path("subscriptions/webhooks/google/", GoogleWebhookView.as_view(), name="sub_webhook_google"),

    # ── Admin endpoints ───────────────────────────────────────────────────────
    path(
        "subscriptions/manage/plans/",
        AdminPlanListCreateView.as_view(),
        name="admin_sub_plans_list_create",
    ),
    path(
        "subscriptions/manage/plans/<uuid:pk>/",
        AdminPlanUpdateDeleteView.as_view(),
        name="admin_sub_plans_update_delete",
    ),
    path(
        "subscriptions/manage/users/<uuid:user_id>/grant/",
        AdminGrantSubscriptionView.as_view(),
        name="admin_sub_grant",
    ),
    path(
        "subscriptions/manage/users/<uuid:user_id>/",
        AdminUserSubscriptionDetailView.as_view(),
        name="admin_sub_user_detail",
    ),
]

