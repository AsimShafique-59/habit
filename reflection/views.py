"""Views for the reflection app."""
import logging
from datetime import date, timedelta

from django.db.models import Avg, Count
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.views import APIView

from habits.models import Habit
from utils.response import ExceptionMixin, api_response

from .models import JournalEntry, JournalHabitTag, MoodLog, ReflectionPrompt
from .serializers import (
    JournalEntryCreateSerializer,
    JournalEntrySerializer,
    JournalEntryUpdateSerializer,
    MoodLogCreateSerializer,
    MoodLogSerializer,
    MoodSummarySerializer,
    ReflectionPromptCreateSerializer,
    ReflectionPromptSerializer,
    ReflectionPromptUpdateSerializer,
)

logger = logging.getLogger(__name__)


def _first_error(serializer) -> str:
    for field_errors in serializer.errors.values():
        if isinstance(field_errors, list) and field_errors:
            return str(field_errors[0])
        if isinstance(field_errors, dict):
            for nested in field_errors.values():
                if isinstance(nested, list) and nested:
                    return str(nested[0])
    return "Validation error."


def _parse_date_param(value, param_name):
    """Parse a date string; return (date, None) or (None, error_message)."""
    if value is None:
        return None, None
    parsed = parse_date(value)
    if parsed is None:
        return None, f"Invalid date format for '{param_name}'. Use YYYY-MM-DD."
    return parsed, None


# ---------------------------------------------------------------------------
# RF-001: Get today's reflection prompt
# GET /reflection/prompt/today/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Reflection"])
class TodayPromptView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="reflection_prompt_today",
        summary="Get today's reflection prompt (RF-001)",
        responses={200: ReflectionPromptSerializer},
    )
    def get(self, request):
        today = date.today()
        try:
            prompt = ReflectionPrompt.objects.get(date=today, is_active=True)
            return api_response("", {"prompt": ReflectionPromptSerializer(prompt).data})
        except ReflectionPrompt.DoesNotExist:
            return api_response("", {"prompt": None})


# ---------------------------------------------------------------------------
# RF-002 / RF-003: Log mood & get mood history
# POST /reflection/mood/   GET /reflection/mood/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Reflection"])
class MoodView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="mood_log",
        summary="Log today's mood (RF-002)",
        request=MoodLogCreateSerializer,
        responses={201: MoodLogSerializer},
    )
    def post(self, request):
        serializer = MoodLogCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(_first_error(serializer), status_code=status.HTTP_400_BAD_REQUEST)

        today = date.today()
        if MoodLog.objects.filter(user=request.user, date=today).exists():
            return api_response(
                "Mood already logged for today.",
                status_code=status.HTTP_409_CONFLICT,
            )

        data = serializer.validated_data
        mood = MoodLog(
            user=request.user,
            score=data["score"],
            note=data.get("note", ""),
            date=today,
        )
        mood.save()
        return api_response(
            "Mood logged.",
            MoodLogSerializer(mood).data,
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        operation_id="mood_history",
        summary="Get mood history (RF-003)",
        parameters=[
            OpenApiParameter("from", str, description="Start date YYYY-MM-DD"),
            OpenApiParameter("to", str, description="End date YYYY-MM-DD"),
        ],
        responses={200: MoodLogSerializer(many=True)},
    )
    def get(self, request):
        today = date.today()
        from_date_str = request.query_params.get("from")
        to_date_str = request.query_params.get("to")

        from_date, err = _parse_date_param(from_date_str, "from")
        if err:
            return api_response(err, status_code=status.HTTP_400_BAD_REQUEST)
        to_date, err = _parse_date_param(to_date_str, "to")
        if err:
            return api_response(err, status_code=status.HTTP_400_BAD_REQUEST)

        if from_date is None:
            from_date = today - timedelta(days=30)
        if to_date is None:
            to_date = today

        logs = MoodLog.objects.filter(
            user=request.user,
            date__gte=from_date,
            date__lte=to_date,
        ).order_by("-date")

        return api_response("", MoodLogSerializer(logs, many=True).data)


# ---------------------------------------------------------------------------
# RF-008: Mood summary
# GET /reflection/mood/summary/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Reflection"])
class MoodSummaryView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="mood_summary",
        summary="Get mood summary / analytics (RF-008)",
        responses={200: MoodSummarySerializer},
    )
    def get(self, request):
        logs = MoodLog.objects.filter(user=request.user)
        total = logs.count()

        if total == 0:
            summary = {
                "average_score": 0.0,
                "total_logs": 0,
                "by_score": {str(i): 0 for i in range(1, 6)},
                "streak_days": 0,
            }
            return api_response("", summary)

        avg = logs.aggregate(avg=Avg("score"))["avg"] or 0.0
        by_score_qs = logs.values("score").annotate(count=Count("id"))
        by_score = {str(i): 0 for i in range(1, 6)}
        for row in by_score_qs:
            by_score[str(row["score"])] = row["count"]

        # Calculate streak: consecutive days with a mood log up to today
        today = date.today()
        streak = 0
        check_date = today
        logged_dates = set(logs.values_list("date", flat=True))
        while check_date in logged_dates:
            streak += 1
            check_date -= timedelta(days=1)

        summary = {
            "average_score": round(avg, 2),
            "total_logs": total,
            "by_score": by_score,
            "streak_days": streak,
        }
        return api_response("", summary)


# ---------------------------------------------------------------------------
# RF-004 / RF-005: Create & list journal entries
# POST /reflection/journal/   GET /reflection/journal/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Reflection"])
class JournalListCreateView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="journal_list",
        summary="List journal entries (RF-005)",
        parameters=[
            OpenApiParameter("from", str, description="Start date YYYY-MM-DD"),
            OpenApiParameter("to", str, description="End date YYYY-MM-DD"),
            OpenApiParameter("habit_id", str, description="Filter by habit UUID"),
        ],
        responses={200: JournalEntrySerializer(many=True)},
    )
    def get(self, request):
        today = date.today()
        from_date_str = request.query_params.get("from")
        to_date_str = request.query_params.get("to")
        habit_id = request.query_params.get("habit_id")

        from_date, err = _parse_date_param(from_date_str, "from")
        if err:
            return api_response(err, status_code=status.HTTP_400_BAD_REQUEST)
        to_date, err = _parse_date_param(to_date_str, "to")
        if err:
            return api_response(err, status_code=status.HTTP_400_BAD_REQUEST)

        qs = JournalEntry.objects.filter(
            user=request.user,
            is_deleted=False,
        ).order_by("-entry_date")

        if from_date:
            qs = qs.filter(entry_date__gte=from_date)
        if to_date:
            qs = qs.filter(entry_date__lte=to_date)
        if habit_id:
            qs = qs.filter(habits__id=habit_id)

        return api_response("", JournalEntrySerializer(qs, many=True).data)

    @extend_schema(
        operation_id="journal_create",
        summary="Create a journal entry (RF-004)",
        request=JournalEntryCreateSerializer,
        responses={201: JournalEntrySerializer},
    )
    def post(self, request):
        serializer = JournalEntryCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(_first_error(serializer), status_code=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        prompt = None
        mood = None

        if data.get("prompt_id"):
            try:
                prompt = ReflectionPrompt.objects.get(id=data["prompt_id"])
            except ReflectionPrompt.DoesNotExist:
                return api_response("Prompt not found.", status_code=status.HTTP_400_BAD_REQUEST)

        if data.get("mood_id"):
            try:
                mood = MoodLog.objects.get(id=data["mood_id"], user=request.user)
            except MoodLog.DoesNotExist:
                return api_response("Mood log not found.", status_code=status.HTTP_400_BAD_REQUEST)

        entry = JournalEntry.objects.create(
            user=request.user,
            prompt=prompt,
            mood=mood,
            text=data["text"],
            entry_date=data.get("entry_date") or date.today(),
        )

        habit_ids = data.get("habit_ids", [])
        if habit_ids:
            habits = Habit.objects.filter(id__in=habit_ids, user=request.user)
            for habit in habits:
                JournalHabitTag.objects.get_or_create(journal_entry=entry, habit=habit)

        entry.refresh_from_db()
        return api_response(
            "Journal entry created.",
            JournalEntrySerializer(entry).data,
            status_code=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# RF-006: Get / update / delete a journal entry
# GET /reflection/journal/<uuid>/
# PATCH /reflection/journal/<uuid>/
# DELETE /reflection/journal/<uuid>/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Reflection"])
class JournalDetailView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def _get_entry(self, user, pk):
        try:
            return JournalEntry.objects.get(id=pk, user=user, is_deleted=False)
        except JournalEntry.DoesNotExist:
            return None

    @extend_schema(
        operation_id="journal_get",
        summary="Get a journal entry (RF-006)",
        responses={200: JournalEntrySerializer},
    )
    def get(self, request, pk):
        entry = self._get_entry(request.user, pk)
        if entry is None:
            return api_response("Journal entry not found.", status_code=status.HTTP_404_NOT_FOUND)
        return api_response("", JournalEntrySerializer(entry).data)

    @extend_schema(
        operation_id="journal_update",
        summary="Update a journal entry (RF-006)",
        request=JournalEntryUpdateSerializer,
        responses={200: JournalEntrySerializer},
    )
    def patch(self, request, pk):
        entry = self._get_entry(request.user, pk)
        if entry is None:
            return api_response("Journal entry not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = JournalEntryUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(_first_error(serializer), status_code=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        if "text" in data:
            entry.text = data["text"]

        if "habit_ids" in data:
            # Replace all habit tags
            JournalHabitTag.objects.filter(journal_entry=entry).delete()
            habits = Habit.objects.filter(id__in=data["habit_ids"], user=request.user)
            for habit in habits:
                JournalHabitTag.objects.create(journal_entry=entry, habit=habit)

        entry.save()
        entry.refresh_from_db()
        return api_response("Journal entry updated.", JournalEntrySerializer(entry).data)

    @extend_schema(
        operation_id="journal_delete",
        summary="Soft-delete a journal entry (RF-006)",
        responses={200: None},
    )
    def delete(self, request, pk):
        entry = self._get_entry(request.user, pk)
        if entry is None:
            return api_response("Journal entry not found.", status_code=status.HTTP_404_NOT_FOUND)
        entry.is_deleted = True
        entry.save(update_fields=["is_deleted", "updated_at"])
        return api_response("Journal entry deleted.")


# ---------------------------------------------------------------------------
# RF-007: Admin — manage reflection prompts
# GET  /reflection/manage/prompts/
# POST /reflection/manage/prompts/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Reflection Admin"])
class AdminPromptListCreateView(ExceptionMixin, APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        operation_id="admin_prompts_list",
        summary="List all reflection prompts (RF-007)",
        responses={200: ReflectionPromptSerializer(many=True)},
    )
    def get(self, request):
        prompts = ReflectionPrompt.objects.all()
        return api_response("", ReflectionPromptSerializer(prompts, many=True).data)

    @extend_schema(
        operation_id="admin_prompts_create",
        summary="Create a reflection prompt (RF-007)",
        request=ReflectionPromptCreateSerializer,
        responses={201: ReflectionPromptSerializer},
    )
    def post(self, request):
        serializer = ReflectionPromptCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(_first_error(serializer), status_code=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        if ReflectionPrompt.objects.filter(date=data["date"]).exists():
            return api_response(
                "A prompt for this date already exists.",
                status_code=status.HTTP_409_CONFLICT,
            )
        prompt = ReflectionPrompt.objects.create(**data)
        return api_response(
            "Prompt created.",
            ReflectionPromptSerializer(prompt).data,
            status_code=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# RF-007: Admin — update / delete a single prompt
# PATCH /reflection/manage/prompts/<uuid>/
# DELETE /reflection/manage/prompts/<uuid>/
# ---------------------------------------------------------------------------

@extend_schema(tags=["Reflection Admin"])
class AdminPromptDetailView(ExceptionMixin, APIView):
    permission_classes = [IsAdminUser]

    def _get_prompt(self, pk):
        try:
            return ReflectionPrompt.objects.get(id=pk)
        except ReflectionPrompt.DoesNotExist:
            return None

    @extend_schema(
        operation_id="admin_prompts_update",
        summary="Update a reflection prompt (RF-007)",
        request=ReflectionPromptUpdateSerializer,
        responses={200: ReflectionPromptSerializer},
    )
    def patch(self, request, pk):
        prompt = self._get_prompt(pk)
        if prompt is None:
            return api_response("Prompt not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = ReflectionPromptUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(_first_error(serializer), status_code=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        # Guard against duplicate date
        new_date = data.get("date")
        if new_date and new_date != prompt.date:
            if ReflectionPrompt.objects.filter(date=new_date).exclude(id=pk).exists():
                return api_response(
                    "A prompt for this date already exists.",
                    status_code=status.HTTP_409_CONFLICT,
                )

        for field, value in data.items():
            setattr(prompt, field, value)
        prompt.save()
        return api_response("Prompt updated.", ReflectionPromptSerializer(prompt).data)

    @extend_schema(
        operation_id="admin_prompts_delete",
        summary="Hard-delete a reflection prompt (RF-007)",
        responses={200: None},
    )
    def delete(self, request, pk):
        prompt = self._get_prompt(pk)
        if prompt is None:
            return api_response("Prompt not found.", status_code=status.HTTP_404_NOT_FOUND)
        prompt.delete()
        return api_response("Prompt deleted.")
