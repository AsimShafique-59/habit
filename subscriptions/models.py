import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

TIER_CHOICES = [("free", "Free"), ("premium", "Premium")]

PROVIDER_CHOICES = [
    ("apple", "Apple"),
    ("google", "Google"),
    ("manual", "Manual"),
]

STATUS_CHOICES = [
    ("active", "Active"),
    ("expired", "Expired"),
    ("cancelled", "Cancelled"),
    ("pending", "Pending"),
]

EVENT_TYPE_CHOICES = [
    ("subscribed", "Subscribed"),
    ("renewed", "Renewed"),
    ("cancelled", "Cancelled"),
    ("expired", "Expired"),
    ("upgraded", "Upgraded"),
    ("downgraded", "Downgraded"),
    ("refunded", "Refunded"),
    ("manual_grant", "Manual Grant"),
]


class SubscriptionPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default="free")
    description = models.TextField(blank=True)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration_days = models.PositiveIntegerField(default=30)
    apple_product_id = models.CharField(max_length=120, blank=True)
    google_product_id = models.CharField(max_length=120, blank=True)
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscription_plans"
        ordering = ["order", "price_usd"]

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(
        SubscriptionPlan,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subscriptions",
    )
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default="free")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default="manual")
    provider_subscription_id = models.CharField(max_length=255, blank=True)
    provider_receipt = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_subscriptions"

    def __str__(self):
        return f"{self.user} — {self.tier} ({self.status})"


class SubscriptionEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscription_events")
    subscription = models.ForeignKey(
        UserSubscription,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    from_tier = models.CharField(max_length=20, blank=True)
    to_tier = models.CharField(max_length=20, blank=True)
    provider = models.CharField(max_length=20, blank=True)
    provider_event_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "subscription_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.event_type} at {self.created_at}"
