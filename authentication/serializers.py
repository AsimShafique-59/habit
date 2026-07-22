import re
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .utils import (
    normalize_locale,
    normalize_timezone,
    validate_email_unique_ci,
    validate_email_mx,
)

User = get_user_model()


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(write_only=True, max_length=128)
    name = serializers.CharField(min_length=1, max_length=80)
    locale = serializers.CharField(max_length=35, default="en-US", required=False)
    timezone = serializers.CharField(max_length=100, default="UTC", required=False)
    accepted_tos_version = serializers.CharField(max_length=20)

    def validate_email(self, value):
        value = value.strip().lower()
        try:
            validate_email_mx(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        try:
            validate_email_unique_ci(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        return value

    def validate_password(self, value):
        try:
            django_validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate_name(self, value):
        return value.strip()

    def validate_locale(self, value):
        return normalize_locale(value)

    def validate_timezone(self, value):
        return normalize_timezone(value)

    def validate_accepted_tos_version(self, value):
        current = getattr(settings, "CURRENT_TOS_VERSION", "1.0")
        if value != current:
            raise serializers.ValidationError(
                f"Accepted TOS version must be '{current}'."
            )
        return value

    def create(self, validated_data):
        email = validated_data["email"]
        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data["password"],
            name=validated_data["name"],
            locale=validated_data.get("locale", "en-US"),
            timezone=validated_data.get("timezone", "UTC"),
            accepted_tos_version=validated_data["accepted_tos_version"],
            email_verified=False,
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.strip().lower()


class AppleSignInSerializer(serializers.Serializer):
    identity_token = serializers.CharField()
    authorization_code = serializers.CharField()
    name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    locale = serializers.CharField(max_length=35, default="en-US", required=False)
    timezone = serializers.CharField(max_length=100, default="UTC", required=False)

    def validate_locale(self, value):
        return normalize_locale(value)

    def validate_timezone(self, value):
        return normalize_timezone(value)


class GoogleSignInSerializer(serializers.Serializer):
    id_token = serializers.CharField()
    locale = serializers.CharField(max_length=35, default="en-US", required=False)
    timezone = serializers.CharField(max_length=100, default="UTC", required=False)

    def validate_locale(self, value):
        return normalize_locale(value)

    def validate_timezone(self, value):
        return normalize_timezone(value)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetCompleteSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(max_length=128)

    def validate_new_password(self, value):
        try:
            django_validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id", "email", "name", "locale", "timezone",
            "email_verified", "subscription_tier",
            "identity_tags", "notification_quiet_hours",
            "theme_preference", "date_joined",
        )
        read_only_fields = ("id", "email", "email_verified", "subscription_tier", "date_joined")

    def validate_identity_tags(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("Maximum 10 identity tags allowed.")
        for tag in value:
            if not isinstance(tag, str) or not (1 <= len(tag) <= 40):
                raise serializers.ValidationError("Each tag must be a string of 1–40 characters.")
        return value

    def validate_notification_quiet_hours(self, value):
        if value is None:
            return value
        if not isinstance(value, dict):
            raise serializers.ValidationError("Must be an object with 'start' and 'end' times.")
        time_re = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
        if not time_re.match(value.get("start", "")):
            raise serializers.ValidationError("'start' must be in HH:MM (24h) format.")
        if not time_re.match(value.get("end", "")):
            raise serializers.ValidationError("'end' must be in HH:MM (24h) format.")
        return value

    def validate_theme_preference(self, value):
        if value not in ("light", "dark", "system"):
            raise serializers.ValidationError("Must be 'light', 'dark', or 'system'.")
        return value


class AccountDeleteSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    google_id_token = serializers.CharField(required=False, allow_blank=True)
    apple_identity_token = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'name', 'locale', 'timezone', 'email_verified', 'subscription_tier')
