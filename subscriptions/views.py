import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.views import APIView

from utils.response import ExceptionMixin, api_response

from .models import SubscriptionEvent, SubscriptionPlan, UserSubscription
from .utils import verify_apple_receipt, verify_google_purchase
from .serializers import (
    AdminGrantSerializer,
    AppleReceiptSerializer,
    GooglePurchaseSerializer,
    SubscriptionPlanAdminSerializer,
    SubscriptionPlanSerializer,
    UserSubscriptionSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_event(user, subscription, event_type, from_tier="", to_tier="",
               provider="", provider_event_id="", metadata=None):
    """Create a SubscriptionEvent audit record."""
    SubscriptionEvent.objects.create(
        user=user,
        subscription=subscription,
        event_type=event_type,
        from_tier=from_tier,
        to_tier=to_tier,
        provider=provider,
        provider_event_id=provider_event_id,
        metadata=metadata or {},
    )


def _get_or_create_subscription(user):
    """Return (subscription, created) for a user, defaulting to free/pending."""
    sub, created = UserSubscription.objects.get_or_create(
        user=user,
        defaults={
            "tier": "free",
            "provider": "manual",
            "status": "pending",
        },
    )
    return sub, created


# ---------------------------------------------------------------------------
# User views
# ---------------------------------------------------------------------------

@extend_schema(tags=["Subscriptions"])
class PlanListView(ExceptionMixin, APIView):
    """List active subscription plans — public endpoint."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="List active subscription plans",
        operation_id="sub_plans_list",
        responses={200: SubscriptionPlanSerializer(many=True)},
    )
    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True)
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return api_response("Subscription plans retrieved.", data=serializer.data)


@extend_schema(tags=["Subscriptions"])
class MySubscriptionView(ExceptionMixin, APIView):
    """Get the current user's subscription (creates a free one if none exists)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get current user subscription",
        operation_id="sub_me_get",
        responses={200: UserSubscriptionSerializer},
    )
    def get(self, request):
        sub, _ = _get_or_create_subscription(request.user)
        serializer = UserSubscriptionSerializer(sub)
        return api_response("Subscription retrieved.", data=serializer.data)


@extend_schema(tags=["Subscriptions"])
class AppleVerifyView(ExceptionMixin, APIView):
    """Verify an Apple IAP receipt and activate the matching plan."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Verify Apple IAP receipt",
        operation_id="sub_apple_verify",
        request=AppleReceiptSerializer,
        responses={200: UserSubscriptionSerializer},
    )
    def post(self, request):
        serializer = AppleReceiptSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                "Invalid input.", data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST
            )

        receipt_data = serializer.validated_data["receipt_data"]
        product_id = serializer.validated_data["product_id"]

        result = verify_apple_receipt(receipt_data, product_id)
        if not result.get("valid"):
            return api_response(
                "Apple receipt verification failed.", status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            plan = SubscriptionPlan.objects.get(apple_product_id=product_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return api_response(
                "No active plan found for this product.", status_code=status.HTTP_404_NOT_FOUND
            )

        sub, _ = _get_or_create_subscription(request.user)
        old_tier = sub.tier

        sub.plan = plan
        sub.tier = plan.tier
        sub.provider = "apple"
        sub.provider_subscription_id = result.get("subscription_id", "")
        sub.provider_receipt = receipt_data
        sub.status = "active"
        sub.started_at = sub.started_at or timezone.now()
        sub.expires_at = result.get("expires_at")
        sub.auto_renew = True
        sub.cancelled_at = None
        sub.save()

        request.user.subscription_tier = plan.tier
        request.user.save(update_fields=["subscription_tier"])

        event_type = "upgraded" if old_tier != plan.tier else "subscribed"
        _log_event(
            user=request.user,
            subscription=sub,
            event_type=event_type,
            from_tier=old_tier,
            to_tier=plan.tier,
            provider="apple",
            provider_event_id=result.get("subscription_id", ""),
            metadata={"product_id": product_id},
        )

        return api_response("Subscription activated.", data=UserSubscriptionSerializer(sub).data)


@extend_schema(tags=["Subscriptions"])
class GoogleVerifyView(ExceptionMixin, APIView):
    """Verify a Google Play purchase and activate the matching plan."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Verify Google Play purchase",
        operation_id="sub_google_verify",
        request=GooglePurchaseSerializer,
        responses={200: UserSubscriptionSerializer},
    )
    def post(self, request):
        serializer = GooglePurchaseSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                "Invalid input.", data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST
            )

        purchase_token = serializer.validated_data["purchase_token"]
        product_id = serializer.validated_data["product_id"]

        result = verify_google_purchase(purchase_token, product_id)
        if not result.get("valid"):
            return api_response(
                "Google purchase verification failed.", status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            plan = SubscriptionPlan.objects.get(google_product_id=product_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return api_response(
                "No active plan found for this product.", status_code=status.HTTP_404_NOT_FOUND
            )

        sub, _ = _get_or_create_subscription(request.user)
        old_tier = sub.tier

        sub.plan = plan
        sub.tier = plan.tier
        sub.provider = "google"
        sub.provider_subscription_id = result.get("subscription_id", "")
        sub.provider_receipt = purchase_token
        sub.status = "active"
        sub.started_at = sub.started_at or timezone.now()
        sub.expires_at = result.get("expires_at")
        sub.auto_renew = True
        sub.cancelled_at = None
        sub.save()

        request.user.subscription_tier = plan.tier
        request.user.save(update_fields=["subscription_tier"])

        event_type = "upgraded" if old_tier != plan.tier else "subscribed"
        _log_event(
            user=request.user,
            subscription=sub,
            event_type=event_type,
            from_tier=old_tier,
            to_tier=plan.tier,
            provider="google",
            provider_event_id=result.get("subscription_id", ""),
            metadata={"product_id": product_id},
        )

        return api_response("Subscription activated.", data=UserSubscriptionSerializer(sub).data)


@extend_schema(tags=["Subscriptions"])
class CancelSubscriptionView(ExceptionMixin, APIView):
    """Cancel the current user's subscription."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Cancel subscription",
        operation_id="sub_cancel",
        responses={200: UserSubscriptionSerializer},
    )
    def post(self, request):
        sub, created = _get_or_create_subscription(request.user)
        if created or sub.status in ("cancelled", "pending"):
            return api_response(
                "No active subscription to cancel.", status_code=status.HTTP_400_BAD_REQUEST
            )

        old_tier = sub.tier
        sub.auto_renew = False
        sub.status = "cancelled"
        sub.cancelled_at = timezone.now()
        sub.save()

        request.user.subscription_tier = "free"
        request.user.save(update_fields=["subscription_tier"])

        _log_event(
            user=request.user,
            subscription=sub,
            event_type="cancelled",
            from_tier=old_tier,
            to_tier="free",
            provider=sub.provider,
        )

        return api_response("Subscription cancelled.", data=UserSubscriptionSerializer(sub).data)


# ---------------------------------------------------------------------------
# Webhook views (no JWT — secret header validation)
# ---------------------------------------------------------------------------

@extend_schema(tags=["Subscriptions"])
class AppleWebhookView(ExceptionMixin, APIView):
    """Receive Apple App Store Server Notifications."""

    permission_classes = [AllowAny]
    authentication_classes = []  # skip JWT parsing entirely

    @extend_schema(
        summary="Apple App Store webhook",
        operation_id="sub_webhook_apple",
        responses={200: None},
    )
    def post(self, request):
        import datetime

        secret = getattr(settings, "APPLE_WEBHOOK_SECRET", "")
        if secret and request.headers.get("X-Apple-Webhook-Secret") != secret:
            return api_response("Forbidden.", status_code=status.HTTP_403_FORBIDDEN)

        notification_type = request.data.get("notification_type") or request.data.get(
            "notificationType", ""
        )
        provider_subscription_id = (
            request.data.get("original_transaction_id")
            or request.data.get("transactionId", "")
        )

        logger.info("Apple webhook received: %s / %s", notification_type, provider_subscription_id)

        if not provider_subscription_id:
            return api_response("OK")

        try:
            sub = UserSubscription.objects.select_related("user").get(
                provider_subscription_id=provider_subscription_id
            )
        except UserSubscription.DoesNotExist:
            return api_response("OK")

        old_tier = sub.tier

        if notification_type in ("DID_RENEW", "INTERACTIVE_RENEWAL"):
            sub.status = "active"
            sub.expires_at = timezone.now() + datetime.timedelta(days=30)
            sub.save(update_fields=["status", "expires_at", "updated_at"])
            _log_event(sub.user, sub, "renewed", old_tier, sub.tier, provider="apple",
                       provider_event_id=notification_type)

        elif notification_type in ("CANCEL", "REFUND"):
            sub.status = "cancelled"
            sub.cancelled_at = timezone.now()
            sub.auto_renew = False
            sub.save(update_fields=["status", "cancelled_at", "auto_renew", "updated_at"])
            sub.user.subscription_tier = "free"
            sub.user.save(update_fields=["subscription_tier"])
            event = "cancelled" if notification_type == "CANCEL" else "refunded"
            _log_event(sub.user, sub, event, old_tier, "free", provider="apple",
                       provider_event_id=notification_type)

        elif notification_type in ("DID_FAIL_TO_RENEW", "EXPIRED"):
            sub.status = "expired"
            sub.save(update_fields=["status", "updated_at"])
            sub.user.subscription_tier = "free"
            sub.user.save(update_fields=["subscription_tier"])
            _log_event(sub.user, sub, "expired", old_tier, "free", provider="apple",
                       provider_event_id=notification_type)

        return api_response("OK")


@extend_schema(tags=["Subscriptions"])
class GoogleWebhookView(ExceptionMixin, APIView):
    """Receive Google Play Real-Time Developer Notifications."""

    permission_classes = [AllowAny]
    authentication_classes = []  # skip JWT parsing entirely

    @extend_schema(
        summary="Google Play webhook",
        operation_id="sub_webhook_google",
        responses={200: None},
    )
    def post(self, request):
        import datetime

        secret = getattr(settings, "GOOGLE_WEBHOOK_SECRET", "")
        if secret and request.headers.get("X-Google-Webhook-Secret") != secret:
            return api_response("Forbidden.", status_code=status.HTTP_403_FORBIDDEN)

        # Google RTDN wraps data in a Pub/Sub message envelope
        message = request.data.get("message", {})
        subscription_notification = message.get("subscriptionNotification", {})
        notification_type = subscription_notification.get("notificationType")
        purchase_token = subscription_notification.get("purchaseToken", "")

        logger.info("Google webhook received: type=%s", notification_type)

        if not purchase_token:
            return api_response("OK")

        try:
            sub = UserSubscription.objects.select_related("user").get(
                provider_receipt=purchase_token
            )
        except UserSubscription.DoesNotExist:
            return api_response("OK")

        old_tier = sub.tier

        # Google notification types:
        # 1=SUBSCRIPTION_RECOVERED, 2=SUBSCRIPTION_RENEWED, 3=SUBSCRIPTION_CANCELED,
        # 4=SUBSCRIPTION_PURCHASED, 12=SUBSCRIPTION_EXPIRED, 13=SUBSCRIPTION_ON_HOLD
        if notification_type in (1, 2, 4):
            sub.status = "active"
            sub.expires_at = timezone.now() + datetime.timedelta(days=30)
            sub.save(update_fields=["status", "expires_at", "updated_at"])
            _log_event(sub.user, sub, "renewed", old_tier, sub.tier, provider="google",
                       provider_event_id=str(notification_type))

        elif notification_type == 3:
            sub.status = "cancelled"
            sub.cancelled_at = timezone.now()
            sub.auto_renew = False
            sub.save(update_fields=["status", "cancelled_at", "auto_renew", "updated_at"])
            sub.user.subscription_tier = "free"
            sub.user.save(update_fields=["subscription_tier"])
            _log_event(sub.user, sub, "cancelled", old_tier, "free", provider="google",
                       provider_event_id=str(notification_type))

        elif notification_type in (12, 13):
            sub.status = "expired"
            sub.save(update_fields=["status", "updated_at"])
            sub.user.subscription_tier = "free"
            sub.user.save(update_fields=["subscription_tier"])
            _log_event(sub.user, sub, "expired", old_tier, "free", provider="google",
                       provider_event_id=str(notification_type))

        return api_response("OK")


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------

@extend_schema(tags=["Subscriptions (Admin)"])
class AdminPlanListCreateView(ExceptionMixin, APIView):
    """Admin: list all plans or create a new plan."""

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="List all subscription plans (admin)",
        operation_id="admin_sub_plans_list",
        responses={200: SubscriptionPlanAdminSerializer(many=True)},
    )
    def get(self, request):
        plans = SubscriptionPlan.objects.all()
        serializer = SubscriptionPlanAdminSerializer(plans, many=True)
        return api_response("Plans retrieved.", data=serializer.data)

    @extend_schema(
        summary="Create subscription plan (admin)",
        operation_id="admin_sub_plans_create",
        request=SubscriptionPlanAdminSerializer,
        responses={201: SubscriptionPlanAdminSerializer},
    )
    def post(self, request):
        serializer = SubscriptionPlanAdminSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                "Invalid data.", data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST
            )
        plan = serializer.save()
        return api_response(
            "Plan created.",
            data=SubscriptionPlanAdminSerializer(plan).data,
            status_code=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Subscriptions (Admin)"])
class AdminPlanUpdateDeleteView(ExceptionMixin, APIView):
    """Admin: update or soft-delete a specific plan."""

    permission_classes = [IsAdminUser]

    def _get_plan(self, pk):
        try:
            return SubscriptionPlan.objects.get(pk=pk)
        except SubscriptionPlan.DoesNotExist:
            return None

    @extend_schema(
        summary="Update subscription plan (admin)",
        operation_id="admin_sub_plans_update",
        request=SubscriptionPlanAdminSerializer,
        responses={200: SubscriptionPlanAdminSerializer},
    )
    def patch(self, request, pk):
        plan = self._get_plan(pk)
        if not plan:
            return api_response("Plan not found.", status_code=status.HTTP_404_NOT_FOUND)
        serializer = SubscriptionPlanAdminSerializer(plan, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(
                "Invalid data.", data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST
            )
        plan = serializer.save()
        return api_response("Plan updated.", data=SubscriptionPlanAdminSerializer(plan).data)

    @extend_schema(
        summary="Soft-delete subscription plan (admin)",
        operation_id="admin_sub_plans_delete",
        responses={200: None},
    )
    def delete(self, request, pk):
        plan = self._get_plan(pk)
        if not plan:
            return api_response("Plan not found.", status_code=status.HTTP_404_NOT_FOUND)
        plan.is_active = False
        plan.save(update_fields=["is_active", "updated_at"])
        return api_response("Plan deactivated.")


@extend_schema(tags=["Subscriptions (Admin)"])
class AdminGrantSubscriptionView(ExceptionMixin, APIView):
    """Admin: manually grant a tier to a specific user."""

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Manually grant subscription tier (admin)",
        operation_id="admin_sub_grant",
        request=AdminGrantSerializer,
        responses={200: UserSubscriptionSerializer},
    )
    def post(self, request, user_id):
        import datetime

        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return api_response("User not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = AdminGrantSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                "Invalid data.", data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST
            )

        tier = serializer.validated_data["tier"]
        duration_days = serializer.validated_data["duration_days"]
        note = serializer.validated_data.get("note", "")

        sub, _ = _get_or_create_subscription(target_user)
        old_tier = sub.tier

        sub.tier = tier
        sub.provider = "manual"
        sub.status = "active"
        sub.started_at = timezone.now()
        sub.expires_at = timezone.now() + datetime.timedelta(days=duration_days)
        sub.auto_renew = False
        sub.cancelled_at = None
        sub.save()

        target_user.subscription_tier = tier
        target_user.save(update_fields=["subscription_tier"])

        _log_event(
            user=target_user,
            subscription=sub,
            event_type="manual_grant",
            from_tier=old_tier,
            to_tier=tier,
            provider="manual",
            metadata={
                "granted_by": str(request.user.id),
                "duration_days": duration_days,
                "note": note,
            },
        )

        return api_response(
            "Subscription granted.", data=UserSubscriptionSerializer(sub).data
        )


@extend_schema(tags=["Subscriptions (Admin)"])
class AdminUserSubscriptionDetailView(ExceptionMixin, APIView):
    """Admin: view a specific user's subscription details."""

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Get user subscription detail (admin)",
        operation_id="admin_sub_user_detail",
        responses={200: UserSubscriptionSerializer},
    )
    def get(self, request, user_id):
        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return api_response("User not found.", status_code=status.HTTP_404_NOT_FOUND)

        sub, _ = _get_or_create_subscription(target_user)
        return api_response(
            "Subscription retrieved.", data=UserSubscriptionSerializer(sub).data
        )

