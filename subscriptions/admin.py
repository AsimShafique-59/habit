from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription, SubscriptionEvent


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        "name", "slug", "tier", "price_usd", "duration_days",
        "is_active", "is_featured", "order", "created_at",
    ]
    list_filter = ["tier", "is_active", "is_featured"]
    search_fields = ["name", "slug", "apple_product_id", "google_product_id"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["order", "price_usd"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "user", "tier", "provider", "status", "started_at", "expires_at",
        "auto_renew", "created_at",
    ]
    list_filter = ["tier", "provider", "status", "auto_renew"]
    search_fields = ["user__email", "user__username", "provider_subscription_id"]
    raw_id_fields = ["user", "plan"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(SubscriptionEvent)
class SubscriptionEventAdmin(admin.ModelAdmin):
    list_display = [
        "user", "event_type", "from_tier", "to_tier", "provider",
        "provider_event_id", "created_at",
    ]
    list_filter = ["event_type", "provider"]
    search_fields = ["user__email", "user__username", "provider_event_id"]
    raw_id_fields = ["user", "subscription"]
    readonly_fields = ["id", "created_at"]
    ordering = ["-created_at"]

