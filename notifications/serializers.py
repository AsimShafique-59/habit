from rest_framework import serializers
from .models import DeviceToken, Notification


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ("id", "token", "platform", "is_active", "created_at")
        read_only_fields = ("id", "is_active", "created_at")

    def validate_platform(self, value):
        if value not in ("ios", "android"):
            raise serializers.ValidationError("platform must be 'ios' or 'android'.")
        return value


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "title", "body", "notification_type", "data", "is_read", "read_at", "created_at")
        read_only_fields = fields
