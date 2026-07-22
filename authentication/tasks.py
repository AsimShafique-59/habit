"""Celery tasks for the authentication app."""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _export_habits(user):
    """Return habits data. Expanded when HM-001+ is built."""
    try:
        return list(
            user.habits.filter(deleted_at__isnull=True).values(
                "id", "title", "category", "frequency_type", "created_at", "archived_at"
            )
        )
    except Exception:
        return []


def _export_completions(user):
    """Return habit completions. Expanded when HM-007+ is built."""
    try:
        return list(
            user.habit_completions.values(
                "id", "habit_id", "completion_date", "quantity", "completed_at"
            ).order_by("-completion_date")[:5000]
        )
    except Exception:
        return []


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def export_user_data_task(self, export_id):
    """
    Compile all user data into JSON and store it in the DataExport record.
    The download URL points to a simple API endpoint that serves the data.
    """
    from .models import DataExport

    try:
        export = DataExport.objects.select_related("user").get(id=export_id)
    except DataExport.DoesNotExist:
        logger.error("export_user_data_task: export %s not found", export_id)
        return

    export.status = DataExport.Status.PROCESSING
    export.save(update_fields=["status"])

    try:
        user = export.user
        data = {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "locale": user.locale,
                "timezone": user.timezone,
                "date_joined": user.date_joined.isoformat(),
                "subscription_tier": user.subscription_tier,
                "identity_tags": user.identity_tags,
                "theme_preference": user.theme_preference,
                "accepted_tos_version": user.accepted_tos_version,
            },
            "audit_logs": list(
                user.audit_logs.values("action", "ip_address", "created_at")
                .order_by("-created_at")[:500]
            ),
            # Populated when Habit Management module is built (HM-001+)
            "habits": _export_habits(user),
            "habit_completions": _export_completions(user),
            # Populated when Reflection module is built
            "journal_entries": [],
            "mood_logs": [],
            # Populated when Integrations module is built
            "program_enrollments": [],
        }

        ttl_hours = getattr(settings, "DATA_EXPORT_TTL_HOURS", 24)
        base_url = settings.FRONTEND_BASE_URL.rstrip("/")

        export.status = DataExport.Status.READY
        export.export_data = data
        export.download_url = f"{base_url}/auth/users/me/export/{export_id}/download/"
        export.expires_at = timezone.now() + timedelta(hours=ttl_hours)
        export.save(update_fields=["status", "export_data", "download_url", "expires_at"])

        logger.info("export_user_data_task: ready — export=%s user=%s", export_id, user.email)

    except Exception as exc:
        logger.exception("export_user_data_task: failed for export %s", export_id)
        export.status = DataExport.Status.FAILED
        export.save(update_fields=["status"])
        raise self.retry(exc=exc)
