"""URL patterns for the analytics app."""
from django.urls import path

from .views import (
    CompletionRateView,
    ConsistencyScoreView,
    DailyAggregationView,
    DayOfWeekBreakdownView,
    FailurePatternsView,
    GenerateWeeklyReportView,
    HabitCorrelationMatrixView,
    HealthTimelineView,
    HeatmapView,
    IdentityProgressView,
    MissedTrendsView,
    MomentumIndexView,
    MonthlyPerformanceView,
    MoodCorrelationView,
    ReportExportView,
    SavingsCounterView,
    SleepCorrelationView,
    StreakDashboardView,
    TimeInvestmentView,
    TimeOfDayHeatmapView,
    WeeklyReportListView,
)

urlpatterns = [
    path("analytics/reports/completion-rate/", CompletionRateView.as_view(), name="analytics-completion-rate"),
    path("analytics/reports/missed-trends/", MissedTrendsView.as_view(), name="analytics-missed-trends"),
    path("analytics/reports/heatmap/", HeatmapView.as_view(), name="analytics-heatmap"),
    path("analytics/reports/streaks/", StreakDashboardView.as_view(), name="analytics-streaks"),
    path("analytics/reports/day-of-week/", DayOfWeekBreakdownView.as_view(), name="analytics-day-of-week"),
    path("analytics/reports/consistency-score/", ConsistencyScoreView.as_view(), name="analytics-consistency-score"),
    path("analytics/reports/momentum/", MomentumIndexView.as_view(), name="analytics-momentum"),
    path("analytics/reports/monthly/", MonthlyPerformanceView.as_view(), name="analytics-monthly"),
    path("analytics/reports/mood-correlation/", MoodCorrelationView.as_view(), name="analytics-mood-correlation"),
    path("analytics/reports/sleep-correlation/", SleepCorrelationView.as_view(), name="analytics-sleep-correlation"),
    path("analytics/reports/habit-correlation/", HabitCorrelationMatrixView.as_view(), name="analytics-habit-correlation"),
    path("analytics/reports/failure-patterns/", FailurePatternsView.as_view(), name="analytics-failure-patterns"),
    path("analytics/reports/time-of-day/", TimeOfDayHeatmapView.as_view(), name="analytics-time-of-day"),
    path("analytics/reports/identity/", IdentityProgressView.as_view(), name="analytics-identity"),
    path("analytics/reports/time-investment/", TimeInvestmentView.as_view(), name="analytics-time-investment"),
    path("analytics/reports/savings/", SavingsCounterView.as_view(), name="analytics-savings"),
    path("analytics/reports/health-timeline/", HealthTimelineView.as_view(), name="analytics-health-timeline"),
    path("analytics/reports/export/", ReportExportView.as_view(), name="analytics-export"),
    # weekly/generate/ MUST be before weekly/ to avoid routing conflict
    path("analytics/reports/weekly/generate/", GenerateWeeklyReportView.as_view(), name="analytics-weekly-generate"),
    path("analytics/reports/weekly/", WeeklyReportListView.as_view(), name="analytics-weekly"),
    path("analytics/reports/daily/", DailyAggregationView.as_view(), name="analytics-daily"),
]

