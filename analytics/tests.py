"""Tests for the analytics app — all report endpoints."""
from datetime import date, timedelta

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import User
from habits.models import Habit, HabitCompletion
from reflection.models import MoodLog


def make_user(email="analytics@example.com"):
    return User.objects.create_user(email=email, username=email, password="Pass1234!", name="Analytics User")


def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


def make_habit(user, title="Run", difficulty="small"):
    return Habit.objects.create(
        user=user, title=title, category="Fitness",
        frequency_type="daily", frequency_days=[], difficulty=difficulty,
    )


def complete_habit(user, habit, days_back=0):
    d = date.today() - timedelta(days=days_back)
    from django.utils import timezone
    obj, _ = HabitCompletion.objects.get_or_create(
        habit=habit,
        user=user,
        completion_date=d,
        defaults={"completed_at": timezone.now(), "quantity": 1, "source": "manual"},
    )
    return obj


# ---------------------------------------------------------------------------
# Helper: base analytics test
# ---------------------------------------------------------------------------

class BaseAnalyticsTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.habit = make_habit(self.user)
        for i in range(10):
            complete_habit(self.user, self.habit, days_back=i)


# ---------------------------------------------------------------------------
# RP-003 – Completion Rate
# ---------------------------------------------------------------------------

class CompletionRateTest(BaseAnalyticsTest):
    def test_returns_200(self):
        resp = self.client.get("/analytics/reports/completion-rate/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        # key may be overall_completion_rate or overall_rate
        self.assertTrue(
            "overall_completion_rate" in data or "overall_rate" in data
        )

    def test_custom_range(self):
        frm = (date.today() - timedelta(days=7)).isoformat()
        to = date.today().isoformat()
        resp = self.client.get(f"/analytics/reports/completion-rate/?from={frm}&to={to}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# RP-004 – Missed Trends
# ---------------------------------------------------------------------------

class MissedTrendsTest(BaseAnalyticsTest):
    def test_returns_200(self):
        resp = self.client.get("/analytics/reports/missed-trends/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertIn("trend_direction", data)
        self.assertIn("data", data)
        self.assertIn(data["trend_direction"], ["improving", "stable", "declining"])


# ---------------------------------------------------------------------------
# RP-005 – Heatmap
# ---------------------------------------------------------------------------

class HeatmapTest(BaseAnalyticsTest):
    def test_returns_365_items(self):
        resp = self.client.get("/analytics/reports/heatmap/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]["heatmap"]), 365)


# ---------------------------------------------------------------------------
# RP-006 – Monthly Performance
# ---------------------------------------------------------------------------

class MonthlyPerformanceTest(BaseAnalyticsTest):
    def test_returns_200_current_month(self):
        resp = self.client.get("/analytics/reports/monthly/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertIn("completion_rate", data)
        self.assertIn("year", data)
        self.assertIn("month", data)

    def test_specific_month(self):
        resp = self.client.get("/analytics/reports/monthly/?month=2026-01")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# RP-007 – Consistency Score
# ---------------------------------------------------------------------------

class ConsistencyScoreTest(BaseAnalyticsTest):
    def test_returns_0_to_100(self):
        resp = self.client.get("/analytics/reports/consistency-score/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        score = resp.data["data"]["score"]
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


# ---------------------------------------------------------------------------
# RP-009 – Streak Dashboard
# ---------------------------------------------------------------------------

class StreakDashboardTest(BaseAnalyticsTest):
    def test_returns_200(self):
        resp = self.client.get("/analytics/reports/streaks/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# RP-010 – Time-of-day heatmap
# ---------------------------------------------------------------------------

class TimeOfDayHeatmapTest(BaseAnalyticsTest):
    def test_returns_168_cells(self):
        resp = self.client.get("/analytics/reports/time-of-day/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        cells = resp.data["data"]["heatmap"]
        self.assertEqual(len(cells), 168)  # 24 hours × 7 days


# ---------------------------------------------------------------------------
# RP-011 – Day of Week
# ---------------------------------------------------------------------------

class DayOfWeekTest(BaseAnalyticsTest):
    def test_returns_200(self):
        resp = self.client.get("/analytics/reports/day-of-week/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# RP-012 – Momentum
# ---------------------------------------------------------------------------

class MomentumTest(BaseAnalyticsTest):
    def test_returns_three_windows(self):
        resp = self.client.get("/analytics/reports/momentum/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertIn("score_7d", data)
        self.assertIn("score_30d", data)
        self.assertIn("score_90d", data)


# ---------------------------------------------------------------------------
# RP-013 – Mood Correlation (insufficient data path)
# ---------------------------------------------------------------------------

class MoodCorrelationTest(BaseAnalyticsTest):
    def test_insufficient_mood_data(self):
        resp = self.client.get("/analytics/reports/mood-correlation/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # No mood data → available=False
        self.assertFalse(resp.data["data"]["available"])

    def test_sufficient_mood_data(self):
        today = date.today()
        for i in range(15):
            MoodLog.objects.create(
                user=self.user,
                date=today - timedelta(days=i),
                score=3,
            )
        resp = self.client.get("/analytics/reports/mood-correlation/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["data"]["available"])


# ---------------------------------------------------------------------------
# RP-014 – Failure Patterns
# ---------------------------------------------------------------------------

class FailurePatternsTest(BaseAnalyticsTest):
    def test_returns_7_days(self):
        resp = self.client.get("/analytics/reports/failure-patterns/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        patterns = resp.data["data"]["patterns"]
        self.assertEqual(len(patterns), 7)


# ---------------------------------------------------------------------------
# RP-015 – Habit Correlation Matrix
# ---------------------------------------------------------------------------

class HabitCorrelationMatrixTest(BaseAnalyticsTest):
    def test_requires_two_habits(self):
        resp = self.client.get("/analytics/reports/habit-correlation/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Single habit → empty matrix
        self.assertEqual(resp.data["data"]["matrix"], [])

    def test_two_habits_produces_pair(self):
        h2 = make_habit(self.user, title="Meditate")
        for i in range(5):
            complete_habit(self.user, h2, days_back=i)
        resp = self.client.get("/analytics/reports/habit-correlation/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(len(resp.data["data"]["matrix"]), 0)


# ---------------------------------------------------------------------------
# RP-016 – Sleep Correlation (insufficient data path)
# ---------------------------------------------------------------------------

class SleepCorrelationTest(BaseAnalyticsTest):
    def test_insufficient_sleep_data_returns_422(self):
        resp = self.client.get("/analytics/reports/sleep-correlation/")
        self.assertEqual(resp.status_code, 422)
        self.assertFalse(resp.data["data"]["available"])


# ---------------------------------------------------------------------------
# RP-017 – Identity Progress
# ---------------------------------------------------------------------------

class IdentityProgressTest(BaseAnalyticsTest):
    def test_missing_tag_param(self):
        resp = self.client.get("/analytics/reports/identity/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tag_with_no_tagged_habits(self):
        resp = self.client.get("/analytics/reports/identity/?tag=runner")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["identity_days"], 0)

    def test_tag_with_tagged_habits(self):
        self.habit.identity_tags = ["runner"]
        self.habit.save()
        resp = self.client.get("/analytics/reports/identity/?tag=runner")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(resp.data["data"]["identity_days"], 0)


# ---------------------------------------------------------------------------
# RP-018 – Time Investment
# ---------------------------------------------------------------------------

class TimeInvestmentTest(BaseAnalyticsTest):
    def test_returns_200(self):
        resp = self.client.get("/analytics/reports/time-investment/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertIn("total_minutes", data)
        self.assertIn("by_category", data)
        self.assertIn("by_habit", data)


# ---------------------------------------------------------------------------
# RP-019 – Savings Counter
# ---------------------------------------------------------------------------

class SavingsCounterTest(TestCase):
    def setUp(self):
        self.user = make_user("savings@example.com")
        self.client = auth_client(self.user)

    def test_missing_enrollment_id(self):
        resp = self.client.get("/analytics/reports/savings/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_enrollment_id(self):
        resp = self.client.get("/analytics/reports/savings/?enrollment_id=not-a-uuid")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_valid_enrollment(self):
        from motivation.models import BadHabitProgram, UserEnrollment
        prog = BadHabitProgram.objects.create(
            name="Quit Smoking",
            slug="quit-smoking",
            description="Test",
            habit_type="smoking",
            program_length_days=30,
            savings_per_day=10,
            savings_money_per_unit=5,
            calories_per_unit=50,
        )
        enrollment = UserEnrollment.objects.create(user=self.user, program=prog)
        resp = self.client.get(f"/analytics/reports/savings/?enrollment_id={enrollment.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertIn("days_clean", data)
        self.assertIn("money_saved", data)
        self.assertIn("calories_avoided", data)


# ---------------------------------------------------------------------------
# RP-020 – Health Timeline
# ---------------------------------------------------------------------------

class HealthTimelineTest(TestCase):
    def setUp(self):
        self.user = make_user("timeline@example.com")
        self.client = auth_client(self.user)

    def test_missing_enrollment_id(self):
        resp = self.client.get("/analytics/reports/health-timeline/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_enrollment_returns_milestones(self):
        from motivation.models import BadHabitProgram, UserEnrollment
        prog = BadHabitProgram.objects.create(
            name="Quit Alcohol",
            slug="quit-alcohol",
            description="Test",
            habit_type="alcohol",
            program_length_days=90,
        )
        enrollment = UserEnrollment.objects.create(user=self.user, program=prog)
        resp = self.client.get(f"/analytics/reports/health-timeline/?enrollment_id={enrollment.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertIn("days_clean", data)
        self.assertIn("milestones", data)
        self.assertGreater(len(data["milestones"]), 0)


# ---------------------------------------------------------------------------
# RP-022 – Report Export (CSV)
# ---------------------------------------------------------------------------

class ReportExportTest(BaseAnalyticsTest):
    def test_completion_rate_csv(self):
        resp = self.client.get("/analytics/reports/export/?report=completion_rate")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn("habit_id", resp.content.decode())

    def test_daily_csv(self):
        resp = self.client.get("/analytics/reports/export/?report=daily")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "text/csv")


# ---------------------------------------------------------------------------
# Weekly report
# ---------------------------------------------------------------------------

class WeeklyReportTest(BaseAnalyticsTest):
    def test_generate_and_list(self):
        resp = self.client.post("/analytics/reports/weekly/generate/")
        self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        resp2 = self.client.get("/analytics/reports/weekly/")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertGreater(resp2.data["data"]["count"], 0)
