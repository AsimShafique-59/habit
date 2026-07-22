"""Views for the integrations app."""
import logging
from datetime import date, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from utils.response import ExceptionMixin, api_response

from .models import CalendarBlock, HealthDataPoint, IntegrationConsent, WidgetSnapshot
from .serializers import (
    CalendarBlockSerializer,
    CalendarSyncSerializer,
    HealthDataPointSerializer,
    HealthSyncSerializer,
    IntegrationConsentSerializer,
    IntegrationConsentUpdateSerializer,
    WidgetSnapshotSerializer,
)

logger = logging.getLogger(__name__)

# All valid integration types
_ALL_INTEGRATION_TYPES = [
    "apple_health",
    "google_fit",
    "apple_calendar",
    "google_calendar",
]

# Map integration source → calendar consent key
_HEALTH_SOURCES = {"apple_health", "google_fit"}
_CALENDAR_SOURCES = {"apple_calendar", "google_calendar"}


def _compute_widget_snapshot(user):
    """Compute widget data for the given user and return a WidgetSnapshot (unsaved)."""
    from habits.models import Habit, HabitCompletion

    today = date.today()
    seven_days_ago = today - timedelta(days=6)

    # Today's habits and completions
    habits_qs = Habit.objects.filter(user=user, is_archived=False)
    completed_today = set(
        HabitCompletion.objects.filter(user=user, completion_date=today)
        .values_list("habit_id", flat=True)
    )
    habits_today = [
        {
            "habit_id": str(h.id),
            "name": h.title,
            "completed": h.id in completed_today,
        }
        for h in habits_qs
    ]

    # Best active streak across user's habits
    streak_count = max(
        (h.current_streak for h in habits_qs),
        default=0,
    )

    # 7-day momentum: completions in last 7 days / (habits × 7)
    total_habits = habits_qs.count()
    if total_habits > 0:
        completions_7d = HabitCompletion.objects.filter(
            user=user,
            completion_date__gte=seven_days_ago,
            completion_date__lte=today,
        ).count()
        momentum_index_7d = round(completions_7d / (total_habits * 7), 4)
    else:
        momentum_index_7d = 0.0

    snapshot, _ = WidgetSnapshot.objects.update_or_create(
        user=user,
        defaults={
            "habits_today": habits_today,
            "streak_count": streak_count,
            "momentum_index_7d": momentum_index_7d,
        },
    )
    return snapshot


# ---------------------------------------------------------------------------
# IN-001: List integrations & consent status
# GET /integrations/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Integrations"])
class IntegrationListView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List integrations and consent status",
        operation_id="integrations_list",
        responses={200: IntegrationConsentSerializer(many=True)},
    )
    def get(self, request):
        consents = {
            c.integration_type: c
            for c in IntegrationConsent.objects.filter(user=request.user)
        }
        result = []
        for itype in _ALL_INTEGRATION_TYPES:
            if itype in consents:
                result.append(IntegrationConsentSerializer(consents[itype]).data)
            else:
                result.append({
                    "id": None,
                    "integration_type": itype,
                    "is_enabled": False,
                    "granted_at": None,
                    "revoked_at": None,
                    "data_categories": [],
                    "created_at": None,
                    "updated_at": None,
                })
        return api_response("Integrations retrieved.", data={"integrations": result})


# ---------------------------------------------------------------------------
# IN-002: Grant/update consent
# POST /integrations/<integration_type>/consent/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Integrations"])
class ConsentView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Grant or update integration consent",
        operation_id="integrations_consent_update",
        request=IntegrationConsentUpdateSerializer,
        responses={200: IntegrationConsentSerializer},
    )
    def post(self, request, integration_type):
        if integration_type not in _ALL_INTEGRATION_TYPES:
            return api_response(
                f"Invalid integration_type '{integration_type}'. "
                f"Valid options: {', '.join(_ALL_INTEGRATION_TYPES)}.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer = IntegrationConsentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        now = timezone.now()
        defaults = {
            "is_enabled": vd["is_enabled"],
            "data_categories": vd["data_categories"],
        }
        if vd["is_enabled"]:
            defaults["granted_at"] = now
            defaults["revoked_at"] = None
        else:
            defaults["revoked_at"] = now

        consent, created = IntegrationConsent.objects.update_or_create(
            user=request.user,
            integration_type=integration_type,
            defaults=defaults,
        )
        logger.info(
            "Integration consent %s: user=%s type=%s enabled=%s",
            "created" if created else "updated",
            request.user.id,
            integration_type,
            vd["is_enabled"],
        )
        return api_response(
            "Consent updated.",
            data=IntegrationConsentSerializer(consent).data,
        )


# ---------------------------------------------------------------------------
# IN-003: Sync health data (batch)
# POST /integrations/health/sync/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Integrations"])
class HealthSyncView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Sync health data from mobile",
        operation_id="integrations_health_sync",
        request=HealthSyncSerializer,
        responses={200: None},
    )
    def post(self, request):
        serializer = HealthSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        source = vd["source"]

        # Validate consent
        try:
            consent = IntegrationConsent.objects.get(
                user=request.user, integration_type=source
            )
        except IntegrationConsent.DoesNotExist:
            return api_response(
                f"No consent record found for '{source}'. Please grant consent first.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if not consent.is_enabled:
            return api_response(
                f"Consent for '{source}' is disabled.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        synced = 0
        for item in vd["data"]:
            HealthDataPoint.objects.update_or_create(
                user=request.user,
                source=source,
                metric=item["metric"],
                recorded_date=item["recorded_date"],
                defaults={"value": item["value"]},
            )
            synced += 1

        logger.info("Health sync: user=%s source=%s synced=%d", request.user.id, source, synced)
        return api_response("Health data synced.", data={"synced": synced, "skipped": 0})


# ---------------------------------------------------------------------------
# IN-004: Get health data
# GET /integrations/health/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Integrations"])
class HealthDataView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get health data points",
        operation_id="integrations_health_list",
        parameters=[
            OpenApiParameter("metric", str, description="Filter by metric (e.g. steps)"),
            OpenApiParameter("from", str, description="Start date YYYY-MM-DD"),
            OpenApiParameter("to", str, description="End date YYYY-MM-DD"),
        ],
        responses={200: HealthDataPointSerializer(many=True)},
    )
    def get(self, request):
        qs = HealthDataPoint.objects.filter(user=request.user)

        metric = request.query_params.get("metric")
        if metric:
            qs = qs.filter(metric=metric)

        from_date_str = request.query_params.get("from")
        to_date_str = request.query_params.get("to")

        if from_date_str:
            from_date = parse_date(from_date_str)
            if from_date is None:
                return api_response("Invalid 'from' date. Use YYYY-MM-DD.", status_code=status.HTTP_400_BAD_REQUEST)
            qs = qs.filter(recorded_date__gte=from_date)

        if to_date_str:
            to_date = parse_date(to_date_str)
            if to_date is None:
                return api_response("Invalid 'to' date. Use YYYY-MM-DD.", status_code=status.HTTP_400_BAD_REQUEST)
            qs = qs.filter(recorded_date__lte=to_date)

        serializer = HealthDataPointSerializer(qs, many=True)
        return api_response("Health data retrieved.", data={"items": serializer.data})


# ---------------------------------------------------------------------------
# IN-005: Sync calendar blocks
# POST /integrations/calendar/sync/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Integrations"])
class CalendarSyncView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Sync calendar busy blocks from mobile",
        operation_id="integrations_calendar_sync",
        request=CalendarSyncSerializer,
        responses={200: None},
    )
    def post(self, request):
        serializer = CalendarSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        source = vd["source"]

        # Validate consent
        try:
            consent = IntegrationConsent.objects.get(
                user=request.user, integration_type=source
            )
        except IntegrationConsent.DoesNotExist:
            return api_response(
                f"No consent record found for '{source}'. Please grant consent first.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if not consent.is_enabled:
            return api_response(
                f"Consent for '{source}' is disabled.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Replace all existing blocks for this source
        CalendarBlock.objects.filter(user=request.user, source=source).delete()
        blocks = [
            CalendarBlock(
                user=request.user,
                source=source,
                start_time=b["start_time"],
                end_time=b["end_time"],
            )
            for b in vd["blocks"]
        ]
        CalendarBlock.objects.bulk_create(blocks)

        synced = len(blocks)
        logger.info("Calendar sync: user=%s source=%s synced=%d", request.user.id, source, synced)
        return api_response("Calendar blocks synced.", data={"synced": synced})


# ---------------------------------------------------------------------------
# IN-006: Check notification suppression
# GET /integrations/calendar/suppress-now/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Integrations"])
class NotificationSuppressionView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Check if notifications should be suppressed right now",
        operation_id="integrations_calendar_suppress_now",
        responses={200: None},
    )
    def get(self, request):
        now = timezone.now()
        block = CalendarBlock.objects.filter(
            user=request.user,
            start_time__lte=now,
            end_time__gt=now,
        ).first()

        if block:
            return api_response(
                "Notification suppression active.",
                data={"suppressed": True, "reason": "calendar_block"},
            )
        return api_response(
            "No suppression active.",
            data={"suppressed": False, "reason": None},
        )


# ---------------------------------------------------------------------------
# IN-007: Widget snapshot
# GET /integrations/widget/snapshot/
# POST /integrations/widget/refresh/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Integrations"])
class WidgetSnapshotView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get widget snapshot",
        operation_id="integrations_widget_snapshot",
        responses={200: WidgetSnapshotSerializer},
    )
    def get(self, request):
        try:
            snapshot = WidgetSnapshot.objects.get(user=request.user)
        except WidgetSnapshot.DoesNotExist:
            snapshot = _compute_widget_snapshot(request.user)

        return api_response(
            "Widget snapshot retrieved.",
            data=WidgetSnapshotSerializer(snapshot).data,
        )


@extend_schema(tags=["Integrations"])
class WidgetRefreshView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Recompute and save widget snapshot",
        operation_id="integrations_widget_refresh",
        responses={200: WidgetSnapshotSerializer},
    )
    def post(self, request):
        snapshot = _compute_widget_snapshot(request.user)
        logger.info("Widget snapshot refreshed: user=%s", request.user.id)
        return api_response(
            "Widget snapshot refreshed.",
            data=WidgetSnapshotSerializer(snapshot).data,
        )
