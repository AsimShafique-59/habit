"""
Habits tests — requirement-driven per SRS.
Each test class references the requirement ID it validates.
"""
from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import User
from habits.models import Habit, HabitCompletion


def make_user(email="habit_user@example.com", subscription_tier="free"):
    return User.objects.create_user(
        email=email, username=email, password="Pass1234!",
        name="Habit User", subscription_tier=subscription_tier,
    )


def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


def make_habit(user, title="Morning Run", frequency_type="daily", **kw):
    return Habit.objects.create(
        user=user,
        title=title,
        category="Fitness",
        frequency_type=frequency_type,
        frequency_days=[1, 2, 3, 4, 5],
        difficulty="small",
        **kw,
    )


def complete_today(client, habit):
    return client.post(f"/habits/{habit.id}/completions/", {
        "completion_date": date.today().isoformat(),
        "quantity": 1,
        "completed_at": timezone.now().isoformat(),
        "source": "manual",
    }, format="json")



# ============================================================================
# HM-001 — Create habit
# ============================================================================

class HM001HabitCreateTest(TestCase):
    """
    SRS HM-001:
    - 201 on valid create; response includes habit_id, current_streak=0
    - Free tier with ≥ 5 active habits → 403 TIER_LIMIT_REACHED
    - Invalid category → 400
    - Invalid color_hex → 400
    - is_quit_habit can be set on create
    - title max 80 chars
    - Unauthenticated → 401
    """
    url = "/habits/"

    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)

    def _create(self, **kw):
        payload = {
            "title": "Test Habit",
            "category": "Health",
            "frequency_type": "daily",
            "difficulty": "tiny",
        }
        payload.update(kw)
        return self.client.post(self.url, payload, format="json")

    def test_valid_create_returns_201(self):
        resp = self._create()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data["data"]
        self.assertIn("habit_id", data)
        self.assertEqual(data["current_streak"], 0)
        self.assertEqual(data["longest_streak"], 0)

    def test_all_valid_categories(self):
        """HM-001: 8 allowed categories."""
        for i, cat in enumerate(["Health", "Fitness", "Mindfulness", "Productivity",
                                  "Learning", "Finance", "Relationships", "Other"]):
            resp = self._create(title=f"Habit {i}", category=cat)
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED, msg=f"Category {cat} failed")

    def test_invalid_category_rejected(self):
        """HM-001: invalid category → 400."""
        resp = self._create(category="InvalidCat")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_color_hex(self):
        resp = self._create(color_hex="#FF5733")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_invalid_color_hex_rejected(self):
        """HM-001: invalid color_hex → 400."""
        for bad in ("red", "FF5733", "#GGGGGG", "#1234"):
            resp = self._create(color_hex=bad)
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST,
                             msg=f"Should reject color_hex={bad!r}")

    def test_is_quit_habit_on_create(self):
        """HM-001: is_quit_habit can be set at creation."""
        resp = self._create(is_quit_habit=True)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["data"]["is_quit_habit"])

    def test_title_too_long_rejected(self):
        """HM-001: title max 80 chars."""
        resp = self._create(title="x" * 81)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_free_tier_limit_reached(self):
        """HM-001: free tier → 403 TIER_LIMIT_REACHED after 5 active habits."""
        for i in range(5):
            make_habit(self.user, title=f"Habit {i}")
        resp = self._create(title="Sixth Habit")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(resp.data["data"]["error_code"], "TIER_LIMIT_REACHED")

    def test_premium_user_not_limited(self):
        """HM-001: premium tier not limited at 5 habits."""
        premium_user = make_user("premium@example.com", subscription_tier="premium")
        premium_client = auth_client(premium_user)
        for i in range(5):
            make_habit(premium_user, title=f"Habit {i}")
        resp = premium_client.post(self.url, {
            "title": "Sixth Habit",
            "category": "Health",
            "frequency_type": "daily",
            "difficulty": "tiny",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_unauthenticated_returns_401(self):
        resp = APIClient().post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ============================================================================
# HM-002 — List habits
# ============================================================================

class HM002HabitListTest(TestCase):
    """
    SRS HM-002:
    - Returns items + next_cursor + total
    - status=active (default), archived, all
    - category filter
    - is_quit_habit filter
    """
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.active = make_habit(self.user, title="Active")
        self.archived = make_habit(self.user, title="Archived")
        self.archived.is_archived = True
        self.archived.save()
        self.quit = make_habit(self.user, title="Quit Habit", is_quit_habit=True)

    def test_default_returns_active_only(self):
        resp = self.client.get("/habits/")
        titles = [h["title"] for h in resp.data["data"]["items"]]
        self.assertIn("Active", titles)
        self.assertNotIn("Archived", titles)

    def test_status_archived_filter(self):
        resp = self.client.get("/habits/?status=archived")
        titles = [h["title"] for h in resp.data["data"]["items"]]
        self.assertIn("Archived", titles)
        self.assertNotIn("Active", titles)

    def test_status_all_returns_both(self):
        resp = self.client.get("/habits/?status=all")
        titles = [h["title"] for h in resp.data["data"]["items"]]
        self.assertIn("Active", titles)
        self.assertIn("Archived", titles)

    def test_is_quit_habit_filter(self):
        resp = self.client.get("/habits/?is_quit_habit=true")
        for h in resp.data["data"]["items"]:
            self.assertTrue(h["is_quit_habit"])

    def test_response_contains_pagination_fields(self):
        resp = self.client.get("/habits/")
        self.assertIn("items", resp.data["data"])
        self.assertIn("total", resp.data["data"])


# ============================================================================
# HM-003 — Get habit by ID
# ============================================================================

class HM003HabitDetailTest(TestCase):
    """
    SRS HM-003:
    - Returns habit + completions_last_30_days
    - Other user's habit → 404 (not 403, prevents enumeration)
    """
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.habit = make_habit(self.user)

    def test_get_own_habit_returns_200(self):
        resp = self.client.get(f"/habits/{self.habit.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_response_includes_completions_last_30_days(self):
        """HM-003: completions_last_30_days key must be present."""
        resp = self.client.get(f"/habits/{self.habit.id}/")
        self.assertIn("completions_last_30_days", resp.data["data"])

    def test_other_user_habit_returns_404_not_403(self):
        """HM-003: prevents enumeration — 404 not 403."""
        other = make_user("other@example.com")
        resp = auth_client(other).get(f"/habits/{self.habit.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ============================================================================
# HM-004 — Update habit / is_quit_habit immutability
# ============================================================================

class HM004HabitUpdateTest(TestCase):
    """
    SRS HM-004:
    - All fields patchable except is_quit_habit (immutable)
    - is_quit_habit changes silently ignored or rejected
    """
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.habit = make_habit(self.user)
        self.quit_habit = make_habit(self.user, title="Quit", is_quit_habit=True)

    def test_patch_title(self):
        resp = self.client.patch(f"/habits/{self.habit.id}/", {"title": "Updated"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.habit.refresh_from_db()
        self.assertEqual(self.habit.title, "Updated")

    def test_is_quit_habit_immutable_after_creation(self):
        """HM-004: is_quit_habit cannot be changed after creation."""
        resp = self.client.patch(
            f"/habits/{self.quit_habit.id}/",
            {"is_quit_habit": False},
            format="json",
        )
        # Either ignored (200) or rejected (400) — but NOT changed
        self.quit_habit.refresh_from_db()
        self.assertTrue(self.quit_habit.is_quit_habit)

    def test_is_quit_habit_stays_false(self):
        """HM-004: non-quit habit cannot become quit after creation."""
        resp = self.client.patch(
            f"/habits/{self.habit.id}/",
            {"is_quit_habit": True},
            format="json",
        )
        self.habit.refresh_from_db()
        self.assertFalse(self.habit.is_quit_habit)


# ============================================================================
# HM-005 — Archive / Unarchive
# ============================================================================

class HM005ArchiveTest(TestCase):
    """
    SRS HM-005:
    - Archive: sets is_archived=True
    - Unarchive: sets is_archived=False
    - Completing archived habit → 409
    - Completions preserved after archive
    """
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.habit = make_habit(self.user)

    def test_archive_habit(self):
        resp = self.client.post(f"/habits/{self.habit.id}/archive/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.habit.refresh_from_db()
        self.assertTrue(self.habit.is_archived)

    def test_unarchive_habit(self):
        self.habit.is_archived = True
        self.habit.save()
        resp = self.client.post(f"/habits/{self.habit.id}/unarchive/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.habit.refresh_from_db()
        self.assertFalse(self.habit.is_archived)

    def test_completing_archived_habit_returns_409(self):
        """HM-005: attempt to complete archived habit → 409."""
        self.habit.is_archived = True
        self.habit.save()
        resp = complete_today(self.client, self.habit)
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)


# ============================================================================
# HM-006 — Hard delete habit
# ============================================================================

class HM006HabitDeleteTest(TestCase):
    """
    SRS HM-006:
    - DELETE /habits/{id}/?confirm=true → 204
    - Without ?confirm=true → rejected (not 204)
    """
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.habit = make_habit(self.user)

    def test_delete_without_confirm_rejected(self):
        """HM-006: must pass ?confirm=true."""
        resp = self.client.delete(f"/habits/{self.habit.id}/")
        self.assertNotEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_with_confirm_succeeds(self):
        resp = self.client.delete(f"/habits/{self.habit.id}/?confirm=true")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Habit.objects.filter(id=self.habit.id).exists())


# ============================================================================
# HM-007 — Mark habit complete
# ============================================================================

class HM007HabitCompleteTest(TestCase):
    """
    SRS HM-007:
    - 200/201 for valid same-day completion
    - Future date → rejected
    - Date > 7 days ago → rejected
    - Re-submit same date with higher quantity → replaced (max quantity)
    - Response includes current_streak, longest_streak, is_complete
    """
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.habit = make_habit(self.user)

    def _complete(self, date_str, quantity=1):
        return self.client.post(f"/habits/{self.habit.id}/completions/", {
            "completion_date": date_str,
            "quantity": quantity,
            "completed_at": timezone.now().isoformat(),
            "source": "manual",
        }, format="json")

    def test_complete_today_returns_streak_info(self):
        resp = self._complete(date.today().isoformat())
        self.assertIn(resp.status_code, [200, 201])
        data = resp.data["data"]
        self.assertIn("current_streak", data)
        self.assertIn("longest_streak", data)
        self.assertIn("is_complete", data)

    def test_future_date_rejected(self):
        """HM-007: future dates not allowed."""
        future = (date.today() + timedelta(days=1)).isoformat()
        resp = self._complete(future)
        self.assertNotEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_date_more_than_7_days_ago_rejected(self):
        """HM-007: max 7 days in the past."""
        old = (date.today() - timedelta(days=8)).isoformat()
        resp = self._complete(old)
        self.assertNotEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_7_days_ago_allowed(self):
        """HM-007: exactly 7 days ago is allowed."""
        d = (date.today() - timedelta(days=7)).isoformat()
        resp = self._complete(d)
        self.assertIn(resp.status_code, [200, 201])

    def test_resubmit_higher_quantity_replaces(self):
        """HM-007: idempotent per (habit, date); higher quantity wins."""
        today = date.today().isoformat()
        self._complete(today, quantity=2)
        resp = self._complete(today, quantity=5)
        self.assertIn(resp.status_code, [200, 201])
        # quantity should be updated to the higher value
        comp = HabitCompletion.objects.get(habit=self.habit, completion_date=today)
        self.assertEqual(comp.quantity, 5)


# ============================================================================
# HM-008 — Undo completion
# ============================================================================

class HM008HabitUndoTest(TestCase):
    """
    SRS HM-008:
    - Delete today's completion → 204
    - Delete yesterday's completion → 403
    """
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.habit = make_habit(self.user)

    def test_undo_todays_completion(self):
        resp = complete_today(self.client, self.habit)
        comp_id = resp.data["data"]["completion_id"]
        del_resp = self.client.delete(f"/habits/{self.habit.id}/completions/{comp_id}/")
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_undo_yesterday_returns_403(self):
        """HM-008: only today's completions can be undone."""
        yesterday = date.today() - timedelta(days=1)
        comp = HabitCompletion.objects.create(
            habit=self.habit,
            completion_date=yesterday,
            quantity=1,
            source="manual",
        )
        resp = self.client.delete(f"/habits/{self.habit.id}/completions/{comp.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ============================================================================
# HM-009 — Batch sync
# ============================================================================

class HM009BatchSyncTest(TestCase):
    """
    SRS HM-009:
    - Partial success supported
    - Response has 'succeeded' and 'failed' keys
    - Each item has client_id
    - Invalid habit_id → failed entry with error_code
    """
    url = "/habits/completions/batch/"

    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.habit = make_habit(self.user)

    def test_batch_all_valid(self):
        resp = self.client.post(self.url, {"completions": [
            {
                "habit_id": str(self.habit.id),
                "completion_date": date.today().isoformat(),
                "quantity": 1,
                "completed_at": timezone.now().isoformat(),
                "client_id": "c1",
                "source": "manual",
            }
        ]}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertIn("succeeded", data)
        self.assertIn("failed", data)
        self.assertEqual(len(data["succeeded"]), 1)

    def test_batch_partial_success(self):
        """HM-009: mix of valid and invalid → partial success."""
        import uuid
        resp = self.client.post(self.url, {"completions": [
            {
                "habit_id": str(self.habit.id),
                "completion_date": date.today().isoformat(),
                "quantity": 1,
                "completed_at": timezone.now().isoformat(),
                "client_id": "ok1",
                "source": "manual",
            },
            {
                "habit_id": str(uuid.uuid4()),  # nonexistent
                "completion_date": date.today().isoformat(),
                "quantity": 1,
                "completed_at": timezone.now().isoformat(),
                "client_id": "bad1",
                "source": "manual",
            },
        ]}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        self.assertEqual(len(data["succeeded"]), 1)
        self.assertEqual(len(data["failed"]), 1)
        self.assertEqual(data["failed"][0]["client_id"], "bad1")

    def test_batch_requires_completions_list(self):
        resp = self.client.post(self.url, {"completions": "not-a-list"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================================
# NT-002 — Reminder CRUD
# ============================================================================

class NT002HabitReminderTest(TestCase):
    """
    SRS NT-002:
    - PUT replaces existing atomically
    - Max 3 per habit → 400
    - Invalid format (not HH:MM) → 400
    - Empty list clears reminders → 200
    - Other user → 404
    """
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.habit = make_habit(self.user)

    def _put(self, times):
        return self.client.put(
            f"/habits/{self.habit.id}/reminders/",
            {"reminder_times": times},
            format="json",
        )

    def test_set_valid_reminders(self):
        resp = self._put(["07:00", "20:00"])
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.habit.refresh_from_db()
        self.assertEqual(self.habit.reminder_times, ["07:00", "20:00"])

    def test_max_3_reminders(self):
        resp = self._put(["07:00", "08:00", "09:00"])
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_more_than_3_rejected(self):
        """NT-002: max 3 per habit."""
        resp = self._put(["07:00", "08:00", "09:00", "10:00"])
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_format_rejected(self):
        """NT-002: must be HH:MM format."""
        for bad in ["7am", "7:00am", "25:00", "07:60"]:
            resp = self._put([bad])
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST,
                             msg=f"Should reject time format: {bad!r}")

    def test_clear_reminders(self):
        """NT-002: empty list clears all reminders."""
        self.habit.reminder_times = ["07:00"]
        self.habit.save()
        resp = self._put([])
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.habit.refresh_from_db()
        self.assertEqual(self.habit.reminder_times, [])

    def test_other_user_returns_404(self):
        other = make_user("other2@example.com")
        resp = auth_client(other).put(
            f"/habits/{self.habit.id}/reminders/",
            {"reminder_times": ["08:00"]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

