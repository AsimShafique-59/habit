"""Views for the analytics app."""
import logging
from datetime import date, timedelta

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from utils.response import ExceptionMixin, api_response

from .utils import (
    compute_weekly_report,
    get_completion_rate,
    get_consistency_score,
    get_day_of_week_breakdown,
    get_failure_patterns,
    get_habit_correlation_matrix,
    get_heatmap_data,
    get_identity_progress,
    get_missed_trends,
    get_momentum_index,
    get_monthly_performance,
    get_mood_habit_correlation,
    get_sleep_habit_correlation,
    get_streak_dashboard,
    get_time_investment,
    get_time_of_day_heatmap_real,
)
from .models import DailyAggregation, WeeklyReport
from .serializers import DailyAggregationSerializer, WeeklyReportSerializer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_DATE_PARAMS = [
    OpenApiParameter(name="from", description="Start date (YYYY-MM-DD)", required=False, type=str),
    OpenApiParameter(name="to", description="End date (YYYY-MM-DD)", required=False, type=str),
]


def _parse_date_range(request):
    """Parse ?from= and ?to= query params; default to last 30 days."""
    today = date.today()
    raw_from = request.query_params.get("from")
    raw_to = request.query_params.get("to")
    try:
        from_date = date.fromisoformat(raw_from) if raw_from else today - timedelta(days=29)
    except ValueError:
        from_date = today - timedelta(days=29)
    try:
        to_date = date.fromisoformat(raw_to) if raw_to else today
    except ValueError:
        to_date = today
    if from_date > to_date:
        from_date, to_date = to_date, from_date
    return from_date, to_date


# ---------------------------------------------------------------------------
# RP-001 – Completion rate
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-001 – Completion rate",
    description="Overall completion rate and per-habit breakdown for the given date range.",
    parameters=_DATE_PARAMS,
)
class CompletionRateView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from_date, to_date = _parse_date_range(request)
        data = get_completion_rate(request.user, from_date, to_date)
        return api_response(
            message="Completion rate retrieved.",
            data={**data, "from": from_date.isoformat(), "to": to_date.isoformat()},
        )


# ---------------------------------------------------------------------------
# RP-002 – Consistency heatmap
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-002 – Consistency heatmap",
    description="Per-day completion data for the last 365 days (no date filter).",
)
class HeatmapView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = get_heatmap_data(request.user, days=365)
        return api_response(message="Heatmap data retrieved.", data={"heatmap": data})


# ---------------------------------------------------------------------------
# RP-003 – Streak dashboard
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-003 – Streak dashboard",
    description="Current and longest streak for every active habit, plus at-risk flag.",
)
class StreakDashboardView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = get_streak_dashboard(request.user)
        return api_response(message="Streak dashboard retrieved.", data=data)


# ---------------------------------------------------------------------------
# RP-004 – Day-of-week breakdown
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-004 – Day-of-week breakdown",
    description="Average completion rate per weekday across the given date range.",
    parameters=_DATE_PARAMS,
)
class DayOfWeekBreakdownView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from_date, to_date = _parse_date_range(request)
        data = get_day_of_week_breakdown(request.user, from_date, to_date)
        return api_response(
            message="Day-of-week breakdown retrieved.",
            data={"breakdown": data, "from": from_date.isoformat(), "to": to_date.isoformat()},
        )


# ---------------------------------------------------------------------------
# RP-005 – Momentum index
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-005 – Momentum index",
    description="Average completion rate for fixed 7, 30, and 90-day windows (no date filter).",
)
class MomentumIndexView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = get_momentum_index(request.user)
        return api_response(message="Momentum index retrieved.", data=data)


# ---------------------------------------------------------------------------
# RP-006 – Mood × habit correlation
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-006 – Mood × habit correlation",
    description=(
        "Correlate daily mood score with per-habit completion. "
        "Requires at least 14 days of mood data."
    ),
    parameters=_DATE_PARAMS,
)
class MoodCorrelationView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from_date, to_date = _parse_date_range(request)
        data = get_mood_habit_correlation(request.user, from_date, to_date)
        return api_response(message="Mood-habit correlation retrieved.", data=data)


# ---------------------------------------------------------------------------
# RP-007 – Habit correlation matrix
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-007 – Habit co-completion matrix",
    description="Pairs of habits sorted by how often they are completed on the same day.",
    parameters=_DATE_PARAMS,
)
class HabitCorrelationMatrixView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from_date, to_date = _parse_date_range(request)
        data = get_habit_correlation_matrix(request.user, from_date, to_date)
        return api_response(message="Habit correlation matrix retrieved.", data={"matrix": data})


# ---------------------------------------------------------------------------
# RP-008 – Failure patterns
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-008 – Failure patterns",
    description="Missed completions grouped by day-of-week to surface weak spots.",
    parameters=_DATE_PARAMS,
)
class FailurePatternsView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from_date, to_date = _parse_date_range(request)
        data = get_failure_patterns(request.user, from_date, to_date)
        return api_response(message="Failure patterns retrieved.", data=data)


# ---------------------------------------------------------------------------
# RP-009 – Weekly reports list
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-009 – Weekly reports list",
    description="Stored WeeklyReport objects for the authenticated user, newest first.",
)
class WeeklyReportListView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reports = WeeklyReport.objects.filter(user=request.user).order_by("-week_start")
        serializer = WeeklyReportSerializer(reports, many=True)
        return api_response(
            message="Weekly reports retrieved.",
            data={"reports": serializer.data, "count": reports.count()},
        )


# ---------------------------------------------------------------------------
# RP-010 – Generate / refresh weekly report
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-010 – Generate/refresh weekly report",
    description=(
        "Compute the current week's report (Mon–Sun), upsert into DB, and return it. "
        "Safe to call multiple times; subsequent calls refresh the stored record."
    ),
)
class GenerateWeeklyReportView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        today = date.today()
        week_start = today - timedelta(days=today.weekday())   # Monday
        week_end = week_start + timedelta(days=6)              # Sunday

        fields = compute_weekly_report(request.user, week_start, week_end)

        report, created = WeeklyReport.objects.update_or_create(
            user=request.user,
            week_start=week_start,
            defaults={
                "week_end": week_end,
                **fields,
            },
        )

        serializer = WeeklyReportSerializer(report)
        message = "Weekly report generated." if created else "Weekly report refreshed."
        return api_response(message=message, data=serializer.data)


# ---------------------------------------------------------------------------
# RP-011 – Daily aggregation
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-011 – Daily aggregation",
    description=(
        "Returns DailyAggregation records for the date range. "
        "If a day has not been pre-aggregated, it is computed on-the-fly and stored."
    ),
    parameters=_DATE_PARAMS,
)
class DailyAggregationView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from reflection.models import MoodLog

        from_date, to_date = _parse_date_range(request)

        existing = {
            agg.date: agg
            for agg in DailyAggregation.objects.filter(
                user=request.user,
                date__range=(from_date, to_date),
            )
        }

        # Determine which days still need to be computed
        missing_dates = [
            d for d in _date_range_list(from_date, to_date)
            if d not in existing
        ]

        if missing_dates:
            from habits.models import Habit, HabitCompletion
            from .utils import _is_habit_scheduled

            habits = list(Habit.objects.filter(user=request.user, is_archived=False))
            completions = set(
                HabitCompletion.objects.filter(
                    user=request.user,
                    completion_date__range=(from_date, to_date),
                ).values_list("habit_id", "completion_date")
            )
            mood_by_date = {
                row["date"]: row["score"]
                for row in MoodLog.objects.filter(
                    user=request.user,
                    date__range=(from_date, to_date),
                ).values("date", "score")
            }

            for d in missing_dates:
                scheduled = [h for h in habits if _is_habit_scheduled(h, d)]
                total = len(scheduled)
                completed = sum(1 for h in scheduled if (h.id, d) in completions)
                rate = (completed / total) if total > 0 else 0.0
                mood = mood_by_date.get(d)

                agg, _ = DailyAggregation.objects.update_or_create(
                    user=request.user,
                    date=d,
                    defaults={
                        "total_habits": total,
                        "completed_habits": completed,
                        "completion_rate": rate,
                        "mood_score": mood,
                    },
                )
                existing[d] = agg

        sorted_aggs = [existing[d] for d in sorted(existing.keys())]
        serializer = DailyAggregationSerializer(sorted_aggs, many=True)
        return api_response(
            message="Daily aggregations retrieved.",
            data={
                "aggregations": serializer.data,
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
            },
        )


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def _date_range_list(from_date: date, to_date: date) -> list:
    result = []
    current = from_date
    while current <= to_date:
        result.append(current)
        current += timedelta(days=1)
    return result


# ---------------------------------------------------------------------------
# RP-004 – Missed-habit trends
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-004 – Missed-habit trends",
    description="Day-by-day miss count and total scheduled with trend direction.",
    parameters=_DATE_PARAMS,
)
class MissedTrendsView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from_date, to_date = _parse_date_range(request)
        data = get_missed_trends(request.user, from_date, to_date)
        return api_response(message="Missed trends retrieved.", data=data)


# ---------------------------------------------------------------------------
# RP-006 – Monthly performance
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-006 – Monthly performance",
    description="Completion breakdown for a given calendar month (YYYY-MM).",
    parameters=[
        OpenApiParameter(name="month", description="Month (YYYY-MM)", required=False, type=str),
    ],
)
class MonthlyPerformanceView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        raw = request.query_params.get("month")
        today = date.today()
        if raw:
            try:
                parts = raw.split("-")
                year, month = int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                year, month = today.year, today.month
        else:
            year, month = today.year, today.month
        data = get_monthly_performance(request.user, year, month)
        return api_response(message="Monthly performance retrieved.", data=data)


# ---------------------------------------------------------------------------
# RP-007 – Consistency score
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-007 – Consistency score (0-100)",
    description="Weighted completion score for the rolling 30-day window.",
)
class ConsistencyScoreView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = get_consistency_score(request.user)
        return api_response(message="Consistency score retrieved.", data=data)


# ---------------------------------------------------------------------------
# RP-010 – Time-of-day heatmap
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-010 – Time-of-day heatmap",
    description="24 × 7 grid of completion counts bucketed by local hour and weekday.",
    parameters=_DATE_PARAMS,
)
class TimeOfDayHeatmapView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from_date, to_date = _parse_date_range(request)
        data = get_time_of_day_heatmap_real(request.user, from_date, to_date)
        return api_response(
            message="Time-of-day heatmap retrieved.",
            data={"heatmap": data, "from": from_date.isoformat(), "to": to_date.isoformat()},
        )


# ---------------------------------------------------------------------------
# RP-016 – Sleep × habit correlation
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-016 – Sleep × habit correlation",
    description=(
        "Correlate imported sleep data with per-habit completion. "
        "Requires at least 14 days of sleep data via Integrations."
    ),
    parameters=_DATE_PARAMS,
)
class SleepCorrelationView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from_date, to_date = _parse_date_range(request)
        data = get_sleep_habit_correlation(request.user, from_date, to_date)
        if not data.get("available", True):
            return api_response(
                "Insufficient sleep data.",
                data=data,
                status_code=422,
            )
        return api_response(message="Sleep-habit correlation retrieved.", data=data)


# ---------------------------------------------------------------------------
# RP-017 – Identity progress
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-017 – Identity progress",
    description="Days the user behaved consistently with an identity tag.",
    parameters=[
        OpenApiParameter(name="tag", description="Identity tag to filter by", required=True, type=str),
        *_DATE_PARAMS,
    ],
)
class IdentityProgressView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from rest_framework import status as http_status
        tag = request.query_params.get("tag", "").strip()
        if not tag:
            return api_response("'tag' query parameter is required.", status_code=http_status.HTTP_400_BAD_REQUEST)
        from_date, to_date = _parse_date_range(request)
        data = get_identity_progress(request.user, tag, from_date, to_date)
        return api_response(message="Identity progress retrieved.", data=data)


# ---------------------------------------------------------------------------
# RP-018 – Time investment
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-018 – Time investment",
    description="Total minutes invested per category and per habit for the given range.",
    parameters=_DATE_PARAMS,
)
class TimeInvestmentView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from_date, to_date = _parse_date_range(request)
        data = get_time_investment(request.user, from_date, to_date)
        return api_response(message="Time investment retrieved.", data=data)


# ---------------------------------------------------------------------------
# RP-019 – Bad-habit savings counter
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-019 – Bad-habit savings counter",
    description="Money saved, calories avoided, hours reclaimed, and days clean for an enrollment.",
    parameters=[
        OpenApiParameter(
            name="enrollment_id",
            description="UUID of the program enrollment",
            required=True,
            type=str,
        ),
    ],
)
class SavingsCounterView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from rest_framework import status as http_status
        from motivation.models import UserEnrollment

        enrollment_id = request.query_params.get("enrollment_id", "").strip()
        if not enrollment_id:
            return api_response(
                "'enrollment_id' query parameter is required.",
                status_code=http_status.HTTP_400_BAD_REQUEST,
            )
        try:
            import uuid as _uuid
            enrollment = UserEnrollment.objects.get(
                id=_uuid.UUID(enrollment_id), user=request.user
            )
        except (UserEnrollment.DoesNotExist, ValueError):
            return api_response("Enrollment not found.", status_code=http_status.HTTP_404_NOT_FOUND)

        program = enrollment.program
        from datetime import date as _date
        today = _date.today()
        anchor = enrollment.last_slip_at or enrollment.started_at
        days_clean = max((today - anchor).days, 0)

        money_per_day = float(program.savings_money_per_unit or 0) * float(program.savings_per_day or 0)
        calories_per_day = float(program.calories_per_unit or 0) * float(program.savings_per_day or 0)

        data = {
            "enrollment_id": str(enrollment.id),
            "program_title": program.name,
            "days_clean": days_clean,
            "money_saved": round(money_per_day * days_clean, 2),
            "currency": "USD",
            "calories_avoided": round(calories_per_day * days_clean),
            "hours_reclaimed": 0,
        }
        return api_response(message="Savings counter retrieved.", data=data)


# ---------------------------------------------------------------------------
# RP-020 – Habit health timeline
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-020 – Habit health timeline",
    description="Achieved and upcoming health milestones for a bad-habit program enrollment.",
    parameters=[
        OpenApiParameter(name="enrollment_id", description="UUID of the program enrollment", required=True, type=str),
    ],
)
class HealthTimelineView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    # Static milestone data — replace with DB-backed milestones in future sprint
    _MILESTONES = [
        {"day": 1,   "description": "Decision made. Your body begins to recover."},
        {"day": 3,   "description": "Physical withdrawal symptoms typically peak."},
        {"day": 7,   "description": "One week clean. Circulation starts improving."},
        {"day": 14,  "description": "Two weeks. Energy levels noticeably higher."},
        {"day": 30,  "description": "One month. Lung function improves significantly."},
        {"day": 90,  "description": "Three months. Risk of relapse drops sharply."},
        {"day": 180, "description": "Six months. Major health markers normalize."},
        {"day": 365, "description": "One year. Celebrate — you've changed your life."},
    ]

    def get(self, request):
        from rest_framework import status as http_status
        from motivation.models import UserEnrollment
        import uuid as _uuid

        enrollment_id = request.query_params.get("enrollment_id", "").strip()
        if not enrollment_id:
            return api_response("'enrollment_id' query parameter is required.", status_code=http_status.HTTP_400_BAD_REQUEST)
        try:
            enrollment = UserEnrollment.objects.get(id=_uuid.UUID(enrollment_id), user=request.user)
        except (UserEnrollment.DoesNotExist, ValueError):
            return api_response("Enrollment not found.", status_code=http_status.HTTP_404_NOT_FOUND)

        from datetime import date as _date
        today = _date.today()
        anchor = enrollment.last_slip_at or enrollment.started_at
        days_clean = max((today - anchor).days, 0)
        milestones = []
        for m in self._MILESTONES:
            if days_clean >= m["day"]:
                status_label = "achieved"
            elif days_clean == m["day"] - 1:
                status_label = "current"
            else:
                status_label = "upcoming"
            milestones.append({
                "day": m["day"],
                "description": m["description"],
                "status": status_label,
            })

        return api_response(
            message="Health timeline retrieved.",
            data={"days_clean": days_clean, "milestones": milestones},
        )


# ---------------------------------------------------------------------------
# RP-022 – Report export (CSV)
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Analytics"],
    summary="RP-022 – Export report as CSV",
    description="Download completion rate data as a CSV file for the given date range.",
    parameters=[
        OpenApiParameter(name="report", description="Report type: completion_rate|daily", required=False, type=str),
        *_DATE_PARAMS,
    ],
)
class ReportExportView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import csv
        import io
        from django.http import HttpResponse

        report_type = request.query_params.get("report", "completion_rate")
        from_date, to_date = _parse_date_range(request)

        output = io.StringIO()
        writer = csv.writer(output)

        if report_type == "daily":
            writer.writerow(["date", "total_habits", "completed_habits", "completion_rate", "mood_score"])
            aggs = DailyAggregation.objects.filter(
                user=request.user,
                date__range=(from_date, to_date),
            ).order_by("date")
            for agg in aggs:
                writer.writerow([
                    agg.date.isoformat(),
                    agg.total_habits,
                    agg.completed_habits,
                    round(float(agg.completion_rate), 4),
                    agg.mood_score or "",
                ])
        else:
            # completion_rate per habit
            data = get_completion_rate(request.user, from_date, to_date)
            writer.writerow(["habit_id", "name", "rate", "completed", "scheduled"])
            for row in data["by_habit"]:
                writer.writerow([
                    row["habit_id"],
                    row.get("name", row.get("title", "")),
                    round(row["rate"], 4),
                    row["completed"],
                    row["scheduled"],
                ])

        filename = f"habit_report_{report_type}_{from_date}_{to_date}.csv"
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
