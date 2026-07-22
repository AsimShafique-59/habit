"""Serializers for the integrations app."""
from rest_framework import serializers

from .models import CalendarBlock, HealthDataPoint, IntegrationConsent, WidgetSnapshot


class IntegrationConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationConsent
        fields = [
            "id",
            "integration_type",
            "is_enabled",
            "granted_at",
            "revoked_at",
            "data_categories",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "granted_at", "revoked_at"]


class IntegrationConsentUpdateSerializer(serializers.Serializer):
    is_enabled = serializers.BooleanField()
    data_categories = serializers.ListField(
        child=serializers.CharField(max_length=50),
        default=list,
    )


class HealthDataPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthDataPoint
        fields = ["id", "source", "metric", "value", "recorded_date", "recorded_at"]
        read_only_fields = ["id", "recorded_at"]


class _HealthDataItemSerializer(serializers.Serializer):
    metric = serializers.ChoiceField(choices=HealthDataPoint.METRIC_CHOICES)
    value = serializers.FloatField()
    recorded_date = serializers.DateField()


class HealthSyncSerializer(serializers.Serializer):
    source = serializers.ChoiceField(choices=HealthDataPoint.SOURCE_CHOICES)
    data = _HealthDataItemSerializer(many=True)

    def validate_data(self, value):
        if not value:
            raise serializers.ValidationError("data list must not be empty.")
        return value


class CalendarBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarBlock
        fields = ["id", "source", "start_time", "end_time", "created_at"]
        read_only_fields = ["id", "created_at"]


class _CalendarBlockItemSerializer(serializers.Serializer):
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()

    def validate(self, attrs):
        if attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError("end_time must be after start_time.")
        return attrs


class CalendarSyncSerializer(serializers.Serializer):
    source = serializers.ChoiceField(choices=CalendarBlock.SOURCE_CHOICES)
    blocks = _CalendarBlockItemSerializer(many=True)

    def validate_blocks(self, value):
        if not value:
            raise serializers.ValidationError("blocks list must not be empty.")
        return value


class WidgetSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = WidgetSnapshot
        fields = ["id", "habits_today", "streak_count", "momentum_index_7d", "updated_at"]
        read_only_fields = ["id", "updated_at"]
