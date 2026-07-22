
import secrets
import uuid
from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255)
    username = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=80, blank=True)
    locale = models.CharField(max_length=35, default="en-US")
    timezone = models.CharField(max_length=100, default="UTC")
    email_verified = models.BooleanField(default=False)
    subscription_tier = models.CharField(
        max_length=20,
        choices=[("free", "Free"), ("premium", "Premium")],
        default="free",
    )
    identity_tags = models.JSONField(default=list, blank=True)
    notification_quiet_hours = models.JSONField(null=True, blank=True)
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Per-category notification toggles. Keys: habit_reminders, streak_risk, "
            "comeback, weekly_review, program_daily, marketing. Values: bool."
        ),
    )
    theme_preference = models.CharField(
        max_length=10,
        choices=[("light", "Light"), ("dark", "Dark"), ("system", "System")],
        default="system",
    )
    accepted_tos_version = models.CharField(max_length=20, blank=True)
    apple_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    google_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["deleted_at", "is_active"])


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_tokens")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed = models.BooleanField(default=False)

    class Meta:
        db_table = "email_verification_tokens"

    @classmethod
    def create_for_user(cls, user):
        from django.conf import settings
        ttl = getattr(settings, "EMAIL_VERIFICATION_TTL_HOURS", 24)
        # Invalidate old tokens
        cls.objects.filter(user=user, consumed=False).update(consumed=True)
        return cls.objects.create(
            user=user,
            token=secrets.token_urlsafe(48),
            expires_at=timezone.now() + timedelta(hours=ttl),
        )

    @property
    def is_valid(self):
        return not self.consumed and self.expires_at > timezone.now()


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed = models.BooleanField(default=False)

    class Meta:
        db_table = "password_reset_tokens"

    @classmethod
    def create_for_user(cls, user):
        from django.conf import settings
        ttl = getattr(settings, "PASSWORD_RESET_TTL_HOURS", 1)
        cls.objects.filter(user=user, consumed=False).update(consumed=True)
        return cls.objects.create(
            user=user,
            token=secrets.token_urlsafe(48),
            expires_at=timezone.now() + timedelta(hours=ttl),
        )

    @property
    def is_valid(self):
        return not self.consumed and self.expires_at > timezone.now()


class DeleteCancelToken(models.Model):
    """One-time token sent by email to let a user cancel their account deletion."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="delete_cancel_tokens")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed = models.BooleanField(default=False)

    class Meta:
        db_table = "delete_cancel_tokens"

    @classmethod
    def create_for_user(cls, user):
        # 30-day grace period
        cls.objects.filter(user=user, consumed=False).update(consumed=True)
        return cls.objects.create(
            user=user,
            token=secrets.token_urlsafe(48),
            expires_at=timezone.now() + timedelta(days=30),
        )

    @property
    def is_valid(self):
        return not self.consumed and self.expires_at > timezone.now()


class DataExport(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exports")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    export_data = models.JSONField(null=True, blank=True)   # stores compiled export JSON
    download_url = models.TextField(null=True, blank=True)  # full URL to download endpoint
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "data_exports"


class AuditLog(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    action = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
