"""Tests for the insights app — DI-001 through DI-006."""
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import User
from insights.models import AudioContent, Category


def make_user(email="insights@example.com", tier="free"):
    return User.objects.create_user(
        email=email, username=email, password="Pass1234!", name="Insight User",
        subscription_tier=tier,
    )


def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


def make_category():
    return Category.objects.create(name="Mindset", slug="mindset", is_active=True)


def make_audio(category, published=True):
    import tempfile, os
    from django.core.files.base import ContentFile
    audio = AudioContent(
        title="Test Audio",
        category=category,
        duration_seconds=60,
        is_published=published,
    )
    audio.audio_file.save("test.mp3", ContentFile(b"ID3\x00"), save=False)
    audio.save()
    return audio


# ---------------------------------------------------------------------------
# DI-001 / DI-002 – Category list & audio list
# ---------------------------------------------------------------------------

class InsightListTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.category = make_category()
        self.audio = make_audio(self.category)

    def test_category_list(self):
        resp = self.client.get("/insights/categories/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data["data"]), 1)

    def test_audio_list_only_published(self):
        make_audio(self.category, published=False)
        resp = self.client.get("/insights/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for item in resp.data["data"]:
            self.assertTrue(item["is_published"])

    def test_audio_detail(self):
        resp = self.client.get(f"/insights/{self.audio.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["title"], "Test Audio")

    def test_unpublished_detail_404(self):
        unpublished = make_audio(self.category, published=False)
        resp = self.client.get(f"/insights/{unpublished.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# DI-004 – Save
# ---------------------------------------------------------------------------

class InsightSaveTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.category = make_category()
        self.audio = make_audio(self.category)

    def test_save_insight(self):
        resp = self.client.post(f"/insights/{self.audio.id}/save/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["data"]["is_saved"])

    def test_unsave_insight(self):
        self.client.post(f"/insights/{self.audio.id}/save/")
        resp = self.client.delete(f"/insights/{self.audio.id}/save/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["data"]["is_saved"])

    def test_save_nonexistent_404(self):
        import uuid
        resp = self.client.post(f"/insights/{uuid.uuid4()}/save/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_blocked(self):
        resp = APIClient().post(f"/insights/{self.audio.id}/save/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# DI-004 – Favourite
# ---------------------------------------------------------------------------

class InsightFavoriteTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.category = make_category()
        self.audio = make_audio(self.category)

    def test_favorite(self):
        resp = self.client.post(f"/insights/{self.audio.id}/favorite/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["data"]["is_favorited"])

    def test_unfavorite(self):
        self.client.post(f"/insights/{self.audio.id}/favorite/")
        resp = self.client.delete(f"/insights/{self.audio.id}/favorite/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["data"]["is_favorited"])


# ---------------------------------------------------------------------------
# DI-004 – Note
# ---------------------------------------------------------------------------

class InsightNoteTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.category = make_category()
        self.audio = make_audio(self.category)

    def test_add_note(self):
        resp = self.client.put(
            f"/insights/{self.audio.id}/note/",
            {"note": "This was really helpful!"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["note"], "This was really helpful!")

    def test_update_note(self):
        self.client.put(f"/insights/{self.audio.id}/note/", {"note": "First"}, format="json")
        resp = self.client.put(f"/insights/{self.audio.id}/note/", {"note": "Updated"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["note"], "Updated")

    def test_non_string_note_rejected(self):
        resp = self.client.put(
            f"/insights/{self.audio.id}/note/",
            {"note": 12345},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_idempotent_save_and_note(self):
        """Saving and adding a note are independent and don't overwrite each other."""
        self.client.post(f"/insights/{self.audio.id}/save/")
        self.client.put(f"/insights/{self.audio.id}/note/", {"note": "My note"}, format="json")
        from insights.models import UserInsightInteraction
        interaction = UserInsightInteraction.objects.get(user=self.user, audio_content=self.audio)
        self.assertTrue(interaction.is_saved)
        self.assertEqual(interaction.note, "My note")


# ---------------------------------------------------------------------------
# DI-006 – Download (premium-gated)
# ---------------------------------------------------------------------------

class InsightDownloadTest(TestCase):
    def setUp(self):
        self.category = make_category()
        self.audio = make_audio(self.category)

    def test_free_user_blocked(self):
        user = make_user("free@example.com", tier="free")
        client = auth_client(user)
        resp = client.post(f"/insights/{self.audio.id}/download/")
        self.assertEqual(resp.status_code, status.HTTP_402_PAYMENT_REQUIRED)

    def test_premium_user_gets_url(self):
        user = make_user("premium@example.com", tier="premium")
        client = auth_client(user)
        resp = client.post(f"/insights/{self.audio.id}/download/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("download_url", resp.data["data"])

    def test_nonexistent_returns_404(self):
        import uuid
        user = make_user("premium2@example.com", tier="premium")
        client = auth_client(user)
        resp = client.post(f"/insights/{uuid.uuid4()}/download/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
