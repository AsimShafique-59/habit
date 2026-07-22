"""
Authentication tests — requirement-driven per SRS.
Each test class references the requirement ID it validates.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import User, PasswordResetToken, DataExport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(email="test@example.com", password="Pass1234!", subscription_tier="free", **kw):
    return User.objects.create_user(
        email=email, username=email, password=password,
        name=kw.pop("name", "Test User"), subscription_tier=subscription_tier, **kw
    )


def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


# ============================================================================
# AUTH-001 — Email/password sign-up
# ============================================================================

class AUTH001SignupTest(TestCase):
    """
    SRS AUTH-001:
    - 201 with tokens on valid signup
    - 409 EMAIL_TAKEN on duplicate
    - password min 8 chars, must contain upper+lower+digit
    - name 1-80 chars
    - accepted_tos_version required
    """
    url = "/auth/signup/"

    def _post(self, **kw):
        payload = {
            "email": "new@example.com",
            "password": "ValidPass1!",
            "name": "Alice",
            "locale": "en-US",
            "timezone": "UTC",
            "accepted_tos_version": "1.0",
        }
        payload.update(kw)
        return APIClient().post(self.url, payload, format="json")

    def test_valid_signup_returns_201_with_tokens(self):
        """AUTH-001: successful signup → 201, tokens present."""
        resp = self._post()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data["data"]
        self.assertIn("tokens", data)
        self.assertIn("access", data["tokens"])
        self.assertIn("refresh", data["tokens"])

    def test_user_created_in_db(self):
        self._post()
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_duplicate_email_returns_409(self):
        """AUTH-001: duplicate email → 409 EMAIL_TAKEN."""
        make_user("dup@example.com")
        resp = self._post(email="dup@example.com")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_duplicate_email_case_insensitive(self):
        """AUTH-001: email uniqueness is case-insensitive."""
        make_user("Case@example.com")
        resp = self._post(email="case@example.com")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_password_too_short_rejected(self):
        """AUTH-001: password min 8 chars."""
        resp = self._post(password="Ab1!")
        self.assertNotEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_password_no_digit_rejected(self):
        """AUTH-001: password must contain digit."""
        resp = self._post(password="NoDigitPass!")
        self.assertNotEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_password_no_uppercase_rejected(self):
        """AUTH-001: password must contain uppercase."""
        resp = self._post(password="nouppercase1!")
        self.assertNotEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_missing_tos_version_rejected(self):
        """AUTH-001: accepted_tos_version is required."""
        resp = self._post(accepted_tos_version="")
        self.assertNotEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_name_too_long_rejected(self):
        """AUTH-001: name max 80 chars."""
        resp = self._post(name="x" * 81)
        self.assertNotEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_email_verified_false_on_signup(self):
        """AUTH-001: email_verified=false immediately after signup."""
        resp = self._post()
        self.assertFalse(resp.data["data"]["email_verified"])


# ============================================================================
# AUTH-004 — Email/password login
# ============================================================================

class AUTH004LoginTest(TestCase):
    """
    SRS AUTH-004:
    - 200 + tokens on valid credentials
    - 401 on wrong password (INVALID_CREDENTIALS; never disclose email existence)
    - 403 on soft-deleted account (ACCOUNT_DEACTIVATED)
    """
    url = "/auth/login/"

    def setUp(self):
        self.user = make_user("login@example.com", "Pass1234!")

    def _login(self, email="login@example.com", password="Pass1234!"):
        return APIClient().post(self.url, {"email": email, "password": password}, format="json")

    def test_valid_credentials_return_200_and_tokens(self):
        resp = self._login()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", resp.data["data"])
        self.assertIn("access", resp.data["data"]["tokens"])

    def test_wrong_password_returns_401(self):
        """AUTH-004: INVALID_CREDENTIALS on wrong password."""
        resp = self._login(password="WrongPass1!")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_email_returns_401_not_404(self):
        """AUTH-004: never disclose whether email exists."""
        resp = self._login(email="ghost@example.com", password="Pass1234!")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_soft_deleted_account_returns_403(self):
        """AUTH-004: deleted account → 403 ACCOUNT_DEACTIVATED."""
        self.user.soft_delete()
        resp = self._login()
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ============================================================================
# AUTH-005 — Token refresh
# ============================================================================

class AUTH005TokenRefreshTest(TestCase):
    """
    SRS AUTH-005:
    - Valid refresh → new token pair
    - Expired/invalid refresh → 401
    """
    url = "/auth/token/refresh/"

    def setUp(self):
        self.user = make_user()

    def test_valid_refresh_returns_new_tokens(self):
        refresh = RefreshToken.for_user(self.user)
        resp = APIClient().post(self.url, {"refresh": str(refresh)}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data["data"])

    def test_invalid_refresh_token_returns_401(self):
        resp = APIClient().post(self.url, {"refresh": "not.a.valid.token"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_refresh_token_rejected(self):
        resp = APIClient().post(self.url, {}, format="json")
        self.assertNotEqual(resp.status_code, status.HTTP_200_OK)


# ============================================================================
# AUTH-007 — Email verification
# ============================================================================

class AUTH007EmailVerificationTest(TestCase):
    """
    SRS AUTH-007:
    - Valid token verifies account; already-verified is idempotent
    - Invalid/expired token → error
    """
    def setUp(self):
        self.user = make_user("verify@example.com")
        from authentication.models import EmailVerificationToken
        self.token_obj = EmailVerificationToken.objects.create(
            user=self.user,
            token="validtoken123",
        )

    def test_valid_token_verifies_email(self):
        resp = APIClient().get("/auth/verify-email/?token=validtoken123")
        self.assertIn(resp.status_code, [200, 302])
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

    def test_invalid_token_rejected(self):
        resp = APIClient().get("/auth/verify-email/?token=badtoken")
        self.assertNotEqual(resp.status_code, 200)

    def test_already_verified_is_idempotent(self):
        """AUTH-007: already verified → still success (idempotent)."""
        self.user.email_verified = True
        self.user.save()
        resp = APIClient().get("/auth/verify-email/?token=validtoken123")
        self.assertIn(resp.status_code, [200, 302])


# ============================================================================
# AUTH-008 — Password reset
# ============================================================================

class AUTH008PasswordResetTest(TestCase):
    """
    SRS AUTH-008:
    - Request always 204 (never disclose email existence)
    - Complete with valid token changes password
    - Invalid token rejected
    """
    def setUp(self):
        self.user = make_user("reset@example.com", "OldPass1!")

    def test_request_always_returns_204(self):
        """AUTH-008: never disclose whether email exists."""
        for email in ("reset@example.com", "ghost@example.com"):
            resp = APIClient().post("/auth/password-reset/request/", {"email": email}, format="json")
            self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_complete_with_valid_token(self):
        token_obj = PasswordResetToken.objects.create(user=self.user, token="resettoken123")
        resp = APIClient().post("/auth/password-reset/complete/", {
            "token": "resettoken123",
            "new_password": "NewPass9!",
        }, format="json")
        self.assertIn(resp.status_code, [200, 204])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass9!"))

    def test_complete_with_invalid_token_rejected(self):
        resp = APIClient().post("/auth/password-reset/complete/", {
            "token": "nonexistent",
            "new_password": "NewPass9!",
        }, format="json")
        self.assertNotEqual(resp.status_code, status.HTTP_200_OK)


# ============================================================================
# AUTH-009 — Get / update user profile
# ============================================================================

class AUTH009UserProfileTest(TestCase):
    """
    SRS AUTH-009:
    - GET returns user_id, email, subscription_tier (read-only)
    - PATCH updates editable fields
    - identity_tags: max 10 items, each 1-40 chars
    - theme_preference: light|dark|system only
    - notification_quiet_hours: {start: HH:MM, end: HH:MM}
    - Read-only fields (email) cannot be changed
    """
    url = "/auth/users/me/"

    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)

    def test_get_returns_required_fields(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        for field in ("email", "subscription_tier", "email_verified"):
            self.assertIn(field, data)

    def test_patch_name(self):
        resp = self.client.patch(self.url, {"name": "New Name"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "New Name")

    def test_patch_valid_theme_preference(self):
        """AUTH-009: theme_preference must be light|dark|system."""
        for val in ("light", "dark", "system"):
            resp = self.client.patch(self.url, {"theme_preference": val}, format="json")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_patch_invalid_theme_preference_rejected(self):
        resp = self.client.patch(self.url, {"theme_preference": "rainbow"}, format="json")
        self.assertNotEqual(resp.status_code, status.HTTP_200_OK)

    def test_patch_valid_quiet_hours(self):
        resp = self.client.patch(self.url, {
            "notification_quiet_hours": {"start": "22:00", "end": "07:00"}
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_identity_tags_max_10(self):
        """AUTH-009: identity_tags max 10."""
        resp = self.client.patch(self.url, {
            "identity_tags": [f"tag{i}" for i in range(11)]
        }, format="json")
        self.assertNotEqual(resp.status_code, status.HTTP_200_OK)

    def test_identity_tags_each_max_40_chars(self):
        """AUTH-009: each identity_tag max 40 chars."""
        resp = self.client.patch(self.url, {
            "identity_tags": ["x" * 41]
        }, format="json")
        self.assertNotEqual(resp.status_code, status.HTTP_200_OK)

    def test_identity_tags_valid(self):
        resp = self.client.patch(self.url, {
            "identity_tags": ["runner", "reader"]
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_unauthenticated_returns_401(self):
        resp = APIClient().get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ============================================================================
# AUTH-010 — Account deletion (GDPR)
# ============================================================================

class AUTH010AccountDeletionTest(TestCase):
    """
    SRS AUTH-010:
    - POST /users/me/delete → soft delete (deleted_at set)
    - Soft-deleted user cannot login (403 ACCOUNT_DEACTIVATED)
    """
    def setUp(self):
        self.user = make_user("delete@example.com", "Pass1234!")
        self.client = auth_client(self.user)

    def test_delete_sets_deleted_at(self):
        resp = self.client.post("/auth/users/me/delete/", {"password": "Pass1234!"}, format="json")
        self.assertIn(resp.status_code, [200, 204])
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.deleted_at)

    def test_deleted_user_cannot_login(self):
        self.user.soft_delete()
        resp = APIClient().post("/auth/login/", {
            "email": "delete@example.com", "password": "Pass1234!"
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ============================================================================
# AUTH-011 — Data export (GDPR portability)
# ============================================================================

class AUTH011DataExportTest(TestCase):
    """
    SRS AUTH-011:
    - POST → 202 with export_id
    - GET with export_id → status in pending|processing|ready|failed
    """
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)

    def test_request_export_returns_202(self):
        resp = self.client.post("/auth/users/me/export/")
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("export_id", resp.data["data"])

    def test_get_export_status(self):
        post_resp = self.client.post("/auth/users/me/export/")
        export_id = post_resp.data["data"]["export_id"]
        resp = self.client.get(f"/auth/users/me/export/{export_id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(resp.data["data"]["status"], ["pending", "processing", "ready", "failed"])


# ============================================================================
# NT-009 — Notification preferences
# ============================================================================

class NT009NotificationPreferencesTest(TestCase):
    """
    SRS NT-009:
    - GET returns all 6 categories: habit_reminders, streak_risk, comeback,
      weekly_review, program_daily, marketing
    - PUT updates individual categories (bool only)
    - Unknown key → 400; non-bool → 400
    - Unauthenticated → 401
    """
    url = "/auth/users/me/notification-preferences/"
    CATEGORIES = ["habit_reminders", "streak_risk", "comeback", "weekly_review", "program_daily", "marketing"]

    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)

    def test_get_returns_all_six_categories(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for cat in self.CATEGORIES:
            self.assertIn(cat, resp.data["data"], msg=f"Missing category: {cat}")

    def test_defaults_are_all_true(self):
        resp = self.client.get(self.url)
        for cat in self.CATEGORIES:
            self.assertTrue(resp.data["data"][cat], msg=f"{cat} default should be True")

    def test_put_disables_single_category(self):
        resp = self.client.put(self.url, {"marketing": False}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["data"]["marketing"])
        # others untouched
        self.assertTrue(resp.data["data"]["habit_reminders"])

    def test_put_all_categories_at_once(self):
        payload = {cat: False for cat in self.CATEGORIES}
        resp = self.client.put(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for cat in self.CATEGORIES:
            self.assertFalse(resp.data["data"][cat])

    def test_unknown_category_key_returns_400(self):
        resp = self.client.put(self.url, {"push_ads": True}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_boolean_value_returns_400(self):
        for bad in ("yes", 1, None, []):
            resp = self.client.put(self.url, {"marketing": bad}, format="json")
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST,
                             msg=f"Should reject non-bool value: {bad!r}")

    def test_unauthenticated_returns_401(self):
        resp = APIClient().get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
