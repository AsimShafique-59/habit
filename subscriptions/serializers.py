from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Read serializer for user-facing plan listing."""

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "slug",
            "tier",
            "description",
            "price_usd",
            "duration_days",
            "apple_product_id",
            "google_product_id",
            "features",
            "is_featured",
        ]


class SubscriptionPlanAdminSerializer(serializers.ModelSerializer):
    """Full read/write serializer for admin plan management."""

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "slug",
            "tier",
            "description",
            "price_usd",
            "duration_days",
            "apple_product_id",
            "google_product_id",
            "features",
            "is_active",
            "is_featured",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Read serializer for a user's subscription."""

    plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = UserSubscription
        fields = [
            "id",
            "plan",
            "tier",
            "provider",
            "status",
            "started_at",
            "expires_at",
            "auto_renew",
            "cancelled_at",
        ]


class AppleReceiptSerializer(serializers.Serializer):
    """Input serializer for Apple IAP receipt verification."""

    receipt_data = serializers.CharField(help_text="Base64-encoded receipt from StoreKit.")
    product_id = serializers.CharField(help_text="Apple StoreKit product ID.")


class GooglePurchaseSerializer(serializers.Serializer):
    """Input serializer for Google Play purchase verification."""

    purchase_token = serializers.CharField(help_text="Purchase token from Google Play Billing.")
    product_id = serializers.CharField(help_text="Google Play product ID.")


class AdminGrantSerializer(serializers.Serializer):
    """Input serializer for admin manual grant endpoint."""

    tier = serializers.ChoiceField(choices=["free", "premium"], default="premium")
    duration_days = serializers.IntegerField(min_value=1, default=30)
    note = serializers.CharField(required=False, allow_blank=True, default="")
