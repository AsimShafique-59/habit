"""Views for the habits app."""
import logging
import zoneinfo
from datetime import date, datetime, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.response import ExceptionMixin, api_response

from .models import Habit, HabitCompletion, VacationPeriod
from .serializers import (
    BatchCompletionItemSerializer,
    HabitCompletionSerializer,
    HabitCreateSerializer,
    HabitSerializer,
    VacationPeriodSerializer,
)
from .utils import recalculate_streak

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_tz(user) -> zoneinfo.ZoneInfo:
    tz_str = getattr(user, "timezone", "UTC") or "UTC"
    try:
        return zoneinfo.ZoneInfo(tz_str)
    except Exception:
        return zoneinfo.ZoneInfo("UTC")


def _today_for_user(user) -> date:
    return datetime.now(_get_user_tz(user)).date()


def _first_error(serializer) -> str:
    """Return the first human-readable validation error from a serializer."""
    for field_errors in serializer.errors.values():
        if isinstance(field_errors, list) and field_errors:
            return str(field_errors[0])
        if isinstance(field_errors, dict):
            for nested in field_errors.values():
                if isinstance(nested, list) and nested:
                    return str(nested[0])
    return "Validation error."


def _get_owned_habit(user, habit_id):
    """Return the habit owned by user or None if not found."""
    try:
        return Habit.objects.get(id=habit_id, user=user)
    except Habit.DoesNotExist:
        return None


# ---------------------------------------------------------------------------
# HM-001 / HM-002 — Create & List habits  POST/GET /habits/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Habits"])
class HabitListCreateView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="habits_list", summary="List habits (HM-002)")
    def get(self, request):
        status_param = request.query_params.get("status", "active")
        category = request.query_params.get("category")
        is_quit_habit = request.query_params.get("is_quit_habit")
        sort = request.query_params.get("sort", "created_at_desc")

        try:
            limit = min(int(request.query_params.get("limit", 50)), 100)
            cursor = int(request.query_params.get("cursor", 0))
        except (ValueError, TypeError):
            return api_response(
                "Invalid limit or cursor parameter.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        qs = Habit.objects.filter(user=request.user)

        if status_param == "active":
            qs = qs.filter(is_archived=False)
        elif status_param == "archived":
            qs = qs.filter(is_archived=True)
        # else: "all" — no filter

        if category:
            qs = qs.filter(category=category)

        if is_quit_habit is not None:
            qs = qs.filter(is_quit_habit=is_quit_habit.lower() in ("true", "1"))

        sort_map = {
            "created_at_desc": "-created_at",
            "title_asc": "title",
            "streak_desc": "-current_streak",
        }
        qs = qs.order_by(sort_map.get(sort, "-created_at"))

        total = qs.count()
        items = qs[cursor : cursor + limit]
        next_cursor = (cursor + limit) if (cursor + limit) < total else None

        return api_response(
            "",
            {
                "items": HabitSerializer(items, many=True).data,
                "next_cursor": str(next_cursor) if next_cursor is not None else None,
                "total": total,
            },
        )

    @extend_schema(operation_id="habits_create", summary="Create habit (HM-001)")
    def post(self, request):
        serializer = HabitCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(_first_error(serializer), status_code=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Free-tier limit: max 5 active habits.
        if request.user.subscription_tier == "free":
            active_count = Habit.objects.filter(user=request.user, is_archived=False).count()
            if active_count >= 5:
                return api_response(
                    "Habit limit reached for free tier.",
                    data={"error_code": "TIER_LIMIT_REACHED"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        # Validate anchor_habit_id.
        anchor_habit_id = data.pop("anchor_habit_id", None)
        anchor_habit = None
        if anchor_habit_id:
            try:
                anchor_habit = Habit.objects.get(id=anchor_habit_id, user=request.user)
            except Habit.DoesNotExist:
                return api_response(
                    "anchor_habit_id not found or not owned by user.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if anchor_habit.is_archived:
                return api_response(
                    "anchor_habit_id refers to an archived habit.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        habit = Habit.objects.create(
            user=request.user,
            anchor_habit=anchor_habit,
            **data,
        )
        return api_response(
            "Habit created.", HabitSerializer(habit).data, status_code=status.HTTP_201_CREATED
        )


# ---------------------------------------------------------------------------
# HM-003 / HM-004 / HM-006 — Get, Update, Hard-delete  /habits/<uuid>/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Habits"])
class HabitDetailView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="habits_get", summary="Get habit detail (HM-003)")
    def get(self, request, habit_id):
        habit = _get_owned_habit(request.user, habit_id)
        if habit is None:
            return api_response("Habit not found.", status_code=status.HTTP_404_NOT_FOUND)

        thirty_ago = date.today() - timedelta(days=30)
        completions = list(
            HabitCompletion.objects.filter(habit=habit, completion_date__gte=thirty_ago)
            .values("completion_date", "quantity", "completed_at")
            .order_by("-completion_date")
        )

        payload = HabitSerializer(habit).data
        payload["completions_last_30_days"] = completions
        return api_response("", payload)

    @extend_schema(operation_id="habits_update", summary="Update habit (HM-004)")
    def patch(self, request, habit_id):
        habit = _get_owned_habit(request.user, habit_id)
        if habit is None:
            return api_response("Habit not found.", status_code=status.HTTP_404_NOT_FOUND)

        # Optimistic locking via If-Match header containing updated_at ISO string.
        if_match = request.headers.get("If-Match", "").strip("\"'")
        if if_match:
            client_dt = parse_datetime(if_match)
            if client_dt is None:
                return api_response(
                    "Invalid If-Match header value.", status_code=status.HTTP_400_BAD_REQUEST
                )
            from django.utils import timezone as tz_util

            if not tz_util.is_aware(client_dt):
                client_dt = tz_util.make_aware(client_dt)
            if abs((habit.updated_at - client_dt).total_seconds()) > 1.0:
                return api_response(
                    "Conflict: habit was modified by another request.",
                    status_code=status.HTTP_409_CONFLICT,
                )

        # is_quit_habit is immutable after creation.
        mutable_data = {k: v for k, v in request.data.items() if k != "is_quit_habit"}

        serializer = HabitCreateSerializer(data=mutable_data, partial=True)
        if not serializer.is_valid():
            return api_response(_first_error(serializer), status_code=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        anchor_habit_id = data.pop("anchor_habit_id", None)

        # Only update anchor_habit if the key was explicitly sent.
        if "anchor_habit_id" in request.data:
            if anchor_habit_id is None:
                habit.anchor_habit = None
            else:
                if str(anchor_habit_id) == str(habit.id):
                    return api_response(
                        "A habit cannot anchor itself.", status_code=status.HTTP_400_BAD_REQUEST
                    )
                try:
                    anchor = Habit.objects.get(id=anchor_habit_id, user=request.user)
                except Habit.DoesNotExist:
                    return api_response(
                        "anchor_habit_id not found or not owned by user.",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
                if anchor.is_archived:
                    return api_response(
                        "anchor_habit_id refers to an archived habit.",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
                habit.anchor_habit = anchor

        for field, value in data.items():
            setattr(habit, field, value)
        habit.save()

        return api_response("Habit updated.", HabitSerializer(habit).data)

    @extend_schema(operation_id="habits_delete", summary="Hard-delete habit (HM-006)")
    def delete(self, request, habit_id):
        if request.query_params.get("confirm") != "true":
            return api_response(
                "Pass ?confirm=true to confirm hard deletion.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        habit = _get_owned_habit(request.user, habit_id)
        if habit is None:
            return api_response("Habit not found.", status_code=status.HTTP_404_NOT_FOUND)

        # Unanchor any habits that referenced this one.
        Habit.objects.filter(anchor_habit=habit).update(anchor_habit=None)

        habit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# HM-005 — Archive / Unarchive
# ---------------------------------------------------------------------------

@extend_schema(tags=["Habits"])
class HabitArchiveView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="habits_archive", summary="Archive habit (HM-005)")
    def post(self, request, habit_id):
        habit = _get_owned_habit(request.user, habit_id)
        if habit is None:
            return api_response("Habit not found.", status_code=status.HTTP_404_NOT_FOUND)

        habit.is_archived = True
        habit.archived_at = timezone.now()
        habit.save(update_fields=["is_archived", "archived_at", "updated_at"])
        return api_response("Habit archived.", HabitSerializer(habit).data)


@extend_schema(tags=["Habits"])
class HabitUnarchiveView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="habits_unarchive", summary="Unarchive habit (HM-005)")
    def post(self, request, habit_id):
        habit = _get_owned_habit(request.user, habit_id)
        if habit is None:
            return api_response("Habit not found.", status_code=status.HTTP_404_NOT_FOUND)

        habit.is_archived = False
        habit.archived_at = None
        habit.save(update_fields=["is_archived", "archived_at", "updated_at"])
        return api_response("Habit unarchived.", HabitSerializer(habit).data)


# ---------------------------------------------------------------------------
# HM-007 — Mark complete  POST /habits/<uuid>/completions/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Habits"])
class HabitCompletionView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="habits_completions_create", summary="Mark habit complete (HM-007)"
    )
    def post(self, request, habit_id):
        habit = _get_owned_habit(request.user, habit_id)
        if habit is None:
            return api_response("Habit not found.", status_code=status.HTTP_404_NOT_FOUND)

        if habit.is_archived:
            return api_response(
                "Cannot log a completion for an archived habit.",
                status_code=status.HTTP_409_CONFLICT,
            )

        # --- Parse & validate inputs ---
        completion_date_raw = request.data.get("completion_date")
        quantity_raw = request.data.get("quantity", 1)
        completed_at_raw = request.data.get("completed_at")
        source = request.data.get("source", "manual")

        if source not in dict(HabitCompletion.SOURCE_CHOICES):
            return api_response("Invalid source value.", status_code=status.HTTP_400_BAD_REQUEST)

        try:
            completion_date = date.fromisoformat(str(completion_date_raw))
        except (ValueError, TypeError):
            return api_response(
                "Invalid completion_date. Use YYYY-MM-DD.", status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = float(quantity_raw)
        except (ValueError, TypeError):
            return api_response("Invalid quantity.", status_code=status.HTTP_400_BAD_REQUEST)

        if completed_at_raw:
            completed_at = parse_datetime(str(completed_at_raw))
            if completed_at is None:
                return api_response(
                    "Invalid completed_at format.", status_code=status.HTTP_400_BAD_REQUEST
                )
            from django.utils import timezone as tz_util

            if not tz_util.is_aware(completed_at):
                completed_at = tz_util.make_aware(completed_at)
        else:
            completed_at = timezone.now()

        # Date-range check using user's timezone.
        today = _today_for_user(request.user)
        if completion_date > today:
            return api_response(
                "completion_date cannot be in the future.", status_code=status.HTTP_400_BAD_REQUEST
            )
        if (today - completion_date).days > 7:
            return api_response(
                "completion_date cannot be more than 7 days in the past.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Quantity cap.
        if habit.quantity_target is not None and quantity > float(habit.quantity_target) * 2:
            return api_response(
                f"quantity exceeds twice the habit's target ({habit.quantity_target}).",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Same-day idempotency: update with max(existing, new) quantity.
        try:
            existing = HabitCompletion.objects.get(habit=habit, completion_date=completion_date)
            new_qty = max(float(existing.quantity), quantity)
            existing.quantity = new_qty
            existing.completed_at = completed_at
            existing.save(update_fields=["quantity", "completed_at"])
            completion = existing
        except HabitCompletion.DoesNotExist:
            completion = HabitCompletion.objects.create(
                habit=habit,
                user=request.user,
                completion_date=completion_date,
                quantity=quantity,
                completed_at=completed_at,
                source=source,
            )

        streak_result = recalculate_streak(habit, request.user)

        is_complete = habit.quantity_target is None or float(completion.quantity) >= float(
            habit.quantity_target
        )

        return api_response(
            "Completion recorded.",
            {
                "completion_id": str(completion.id),
                "habit_id": str(habit.id),
                "completion_date": str(completion.completion_date),
                "quantity": str(completion.quantity),
                "is_complete": is_complete,
                "current_streak": streak_result["current_streak"],
                "longest_streak": streak_result["longest_streak"],
                "streak_freeze_used": streak_result["streak_freeze_used"],
            },
            status_code=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# HM-008 — Undo completion  DELETE /habits/<uuid>/completions/<uuid>/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Habits"])
class HabitCompletionUndoView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="habits_completions_undo", summary="Undo completion (HM-008)")
    def delete(self, request, habit_id, completion_id):
        habit = _get_owned_habit(request.user, habit_id)
        if habit is None:
            return api_response("Habit not found.", status_code=status.HTTP_404_NOT_FOUND)

        try:
            completion = HabitCompletion.objects.get(id=completion_id, habit=habit)
        except HabitCompletion.DoesNotExist:
            return api_response("Completion not found.", status_code=status.HTTP_404_NOT_FOUND)

        today = _today_for_user(request.user)
        if completion.completion_date != today:
            return api_response(
                "Only today's completions can be undone.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        completion.delete()
        recalculate_streak(habit, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# HM-009 — Batch sync  POST /habits/completions/batch/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Habits"])
class BatchSyncView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="habits_completions_batch", summary="Batch sync completions (HM-009)"
    )
    def post(self, request):
        completions_data = request.data.get("completions", [])
        if not isinstance(completions_data, list):
            return api_response(
                "'completions' must be a list.", status_code=status.HTTP_400_BAD_REQUEST
            )

        succeeded = []
        failed = []

        for item in completions_data:
            client_id = item.get("client_id")

            serializer = BatchCompletionItemSerializer(data=item)
            if not serializer.is_valid():
                failed.append(
                    {
                        "client_id": client_id,
                        "error_code": "VALIDATION_ERROR",
                        "message": _first_error(serializer),
                    }
                )
                continue

            data = serializer.validated_data

            try:
                habit = Habit.objects.get(id=data["habit_id"], user=request.user)
            except Habit.DoesNotExist:
                failed.append(
                    {"client_id": client_id, "error_code": "NOT_FOUND", "message": "Habit not found."}
                )
                continue

            if habit.is_archived:
                failed.append(
                    {"client_id": client_id, "error_code": "ARCHIVED", "message": "Habit is archived."}
                )
                continue

            try:
                existing = HabitCompletion.objects.get(
                    habit=habit, completion_date=data["completion_date"]
                )
                new_qty = max(float(existing.quantity), float(data["quantity"]))
                existing.quantity = new_qty
                existing.save(update_fields=["quantity"])
                completion = existing
            except HabitCompletion.DoesNotExist:
                completion = HabitCompletion.objects.create(
                    habit=habit,
                    user=request.user,
                    completion_date=data["completion_date"],
                    quantity=data["quantity"],
                    completed_at=data["completed_at"],
                    source=data.get("source", "manual"),
                    client_id=data.get("client_id"),
                )

            recalculate_streak(habit, request.user)

            succeeded.append({"client_id": client_id, "completion_id": str(completion.id)})

        return api_response("Batch sync complete.", {"succeeded": succeeded, "failed": failed})


# ---------------------------------------------------------------------------
# NT-002 — Reminder CRUD  PUT /habits/{habit_id}/reminders/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Habits"])
class HabitReminderView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="habits_reminders_update",
        summary="Set reminder times for a habit (NT-002)",
        description="Replace the habit's reminder_times list. Max 3 entries in HH:MM format.",
    )
    def put(self, request, habit_id):
        import re
        habit = _get_owned_habit(request.user, habit_id)
        if habit is None:
            return api_response("Habit not found.", status_code=status.HTTP_404_NOT_FOUND)

        reminder_times = request.data.get("reminder_times")
        if not isinstance(reminder_times, list):
            return api_response(
                "'reminder_times' must be a list.", status_code=status.HTTP_400_BAD_REQUEST
            )
        if len(reminder_times) > 3:
            return api_response(
                "Maximum 3 reminder times allowed.", status_code=status.HTTP_400_BAD_REQUEST
            )
        for t in reminder_times:
            if not re.match(r"^\d{2}:\d{2}$", str(t)):
                return api_response(
                    f"Invalid reminder time '{t}'. Use HH:MM format.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        habit.reminder_times = reminder_times
        habit.save(update_fields=["reminder_times", "updated_at"])
        return api_response(
            "Reminder times updated.",
            data={"habit_id": str(habit.id), "reminder_times": habit.reminder_times},
        )


# ---------------------------------------------------------------------------
# HM-012 — Vacation mode
# ---------------------------------------------------------------------------

@extend_schema(tags=["Habits"])
class VacationView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="vacation_create", summary="Create vacation period (HM-012)")
    def post(self, request):
        start_raw = request.data.get("start_date")
        end_raw = request.data.get("end_date")

        try:
            start_date = date.fromisoformat(str(start_raw))
            end_date = date.fromisoformat(str(end_raw))
        except (ValueError, TypeError):
            return api_response(
                "Invalid date format. Use YYYY-MM-DD.", status_code=status.HTTP_400_BAD_REQUEST
            )

        if end_date < start_date:
            return api_response(
                "end_date must be on or after start_date.", status_code=status.HTTP_400_BAD_REQUEST
            )

        if (end_date - start_date).days > 29:
            return api_response(
                "Vacation period cannot exceed 30 days.", status_code=status.HTTP_400_BAD_REQUEST
            )

        today = date.today()
        overlap = VacationPeriod.objects.filter(user=request.user, end_date__gte=today).exists()
        if overlap:
            return api_response(
                "An active or future vacation period already exists.",
                status_code=status.HTTP_409_CONFLICT,
            )

        vacation = VacationPeriod.objects.create(
            user=request.user, start_date=start_date, end_date=end_date
        )
        return api_response(
            "Vacation period created.",
            VacationPeriodSerializer(vacation).data,
            status_code=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Habits"])
class VacationDetailView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="vacation_delete", summary="Cancel vacation period (HM-012)")
    def delete(self, request, pk):
        try:
            vacation = VacationPeriod.objects.get(id=pk, user=request.user)
        except VacationPeriod.DoesNotExist:
            return api_response("Vacation period not found.", status_code=status.HTTP_404_NOT_FOUND)

        vacation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
