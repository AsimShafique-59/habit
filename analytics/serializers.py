"""Serializers for the analytics app."""
from rest_framework import serializers

from .models import DailyAggregation, WeeklyReport


class DailyAggregationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyAggregation
        fields = [
            "id",
            "date",
            "total_habits",
            "completed_habits",
            "completion_rate",
            "mood_score",
            "created_at",
            "updated_at",
        ]


class WeeklyReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyReport
        fields = [
            "id",
            "week_start",
            "week_end",
            "completion_rate",
            "best_day",
            "worst_day",
            "mood_average",
            "narrative",
            "generated_at",
        ]
