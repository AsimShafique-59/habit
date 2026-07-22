"""Views for the motivation (bad-habit removal) app."""
import logging
from datetime import date

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.views import APIView

from utils.response import ExceptionMixin, api_response

from .models import (
    BadHabitProgram,
    DayCompletion,
    PersonalMotivation,
    ProgramDay,
    QuitReason,
    UrgeSOS,
    UserEnrollment,
    UserTrigger,
)
from .serializers import (
    AdminProgramDaySerializer,
    AdminProgramSerializer,
    BadHabitProgramDetailSerializer,
    BadHabitProgramSerializer,
    DayCompletionSerializer,
    PersonalMotivationSerializer,
    QuitReasonSerializer,
    UrgeSosSerializer,
    UserEnrollmentCreateSerializer,
    UserEnrollmentSerializer,
    UserTriggerSerializer,
)

logger = logging.getLogger(__name__)


# ─── BH-001: Program library (public) ────────────────────────────────────────

@extend_schema(tags=["Motivation"])
class ProgramListView(ExceptionMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="List active bad-habit programs",
        operation_id="motivation_programs_list",
        responses={200: BadHabitProgramSerializer(many=True)},
    )
    def get(self, request):
        qs = BadHabitProgram.objects.filter(is_active=True)
        return api_response("Programs retrieved.", data=BadHabitProgramSerializer(qs, many=True).data)


# ─── BH-002: Program detail (public) ─────────────────────────────────────────

@extend_schema(tags=["Motivation"])
class ProgramDetailView(ExceptionMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get program detail with days",
        operation_id="motivation_program_detail",
        responses={200: BadHabitProgramDetailSerializer},
    )
    def get(self, request, slug):
        try:
            program = BadHabitProgram.objects.prefetch_related("days__audio").get(
                slug=slug, is_active=True
            )
        except BadHabitProgram.DoesNotExist:
            return api_response("Program not found.", status_code=status.HTTP_404_NOT_FOUND)
        return api_response(
            "Program retrieved.",
            data=BadHabitProgramDetailSerializer(program, context={"request": request}).data,
        )


# ─── BH-003: Enroll in program ────────────────────────────────────────────────

@extend_schema(tags=["Motivation"])
class EnrollView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Enroll in a bad-habit program",
        operation_id="motivation_enroll",
        request=UserEnrollmentCreateSerializer,
        responses={201: UserEnrollmentSerializer},
    )
    def post(self, request):
        serializer = UserEnrollmentCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return api_response(
                "Validation error.",
                data=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        slug = serializer.validated_data["program_slug"]
        try:
            program = BadHabitProgram.objects.get(slug=slug, is_active=True)
        except BadHabitProgram.DoesNotExist:
            return api_response("Program not found.", status_code=status.HTTP_404_NOT_FOUND)

        existing = UserEnrollment.objects.filter(
            user=request.user, program=program, status=UserEnrollment.STATUS_ENROLLED
        ).first()
        if existing:
            return api_response(
                "You are already enrolled in this program.",
                status_code=status.HTTP_409_CONFLICT,
            )

        enrollment = UserEnrollment.objects.create(
            user=request.user,
            program=program,
            replacement_habit_id=serializer.validated_data.get("replacement_habit_id"),
        )

        data = UserEnrollmentSerializer(enrollment, context={"request": request}).data
        if program.has_medical_risk:
            data["disclaimer"] = (
                "This program involves a habit with potential medical risk. "
                "Please consult a healthcare professional before starting."
            )
            data["crisis_resource_url"] = program.crisis_resource_url

        return api_response("Enrolled successfully.", data=data, status_code=status.HTTP_201_CREATED)


# ─── BH-004: My enrollments ───────────────────────────────────────────────────

@extend_schema(tags=["Motivation"])
class EnrollmentListView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List my enrollments with computed progress fields",
        operation_id="motivation_enrollments_list",
        responses={200: UserEnrollmentSerializer(many=True)},
    )
    def get(self, request):
        qs = UserEnrollment.objects.filter(user=request.user).select_related("program")
        return api_response(
            "Enrollments retrieved.",
            data=UserEnrollmentSerializer(qs, many=True, context={"request": request}).data,
        )


# ─── BH-005: Today's program day ─────────────────────────────────────────────

@extend_schema(tags=["Motivation"])
class TodayDayView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get today's program day content",
        operation_id="motivation_today_day",
        responses={200: AdminProgramDaySerializer},
    )
    def get(self, request, pk):
        enrollment = self._get_enrollment(pk, request.user)
        if not enrollment:
            return api_response("Enrollment not found.", status_code=status.HTTP_404_NOT_FOUND)

        today = date.today()
        current_day = (today - enrollment.started_at).days + 1
        current_day = min(current_day, enrollment.program.program_length_days)

        try:
            program_day = ProgramDay.objects.select_related("audio").get(
                program=enrollment.program, day_number=current_day
            )
        except ProgramDay.DoesNotExist:
            return api_response(
                "No content available for today.", status_code=status.HTTP_404_NOT_FOUND
            )

        return api_response(
            "Today's content retrieved.",
            data=AdminProgramDaySerializer(program_day, context={"request": request}).data,
        )

    @staticmethod
    def _get_enrollment(pk, user):
        try:
            return UserEnrollment.objects.select_related("program").get(pk=pk, user=user)
        except UserEnrollment.DoesNotExist:
            return None


# ─── BH-006: Complete a day ───────────────────────────────────────────────────

@extend_schema(tags=["Motivation"])
class CompleteDayView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mark today's program day as complete",
        operation_id="motivation_complete_day",
        request=DayCompletionSerializer,
        responses={201: DayCompletionSerializer},
    )
    def post(self, request, pk):
        enrollment = self._get_enrollment(pk, request.user)
        if not enrollment:
            return api_response("Enrollment not found.", status_code=status.HTTP_404_NOT_FOUND)

        today = date.today()
        current_day = (today - enrollment.started_at).days + 1
        current_day = min(current_day, enrollment.program.program_length_days)

        if DayCompletion.objects.filter(enrollment=enrollment, day_number=current_day).exists():
            return api_response(
                "Today's day has already been completed.", status_code=status.HTTP_409_CONFLICT
            )

        reflection = request.data.get("reflection_response", "")
        completion = DayCompletion.objects.create(
            enrollment=enrollment,
            day_number=current_day,
            reflection_response=reflection,
        )

        # Auto-complete enrollment when last day is done
        if current_day >= enrollment.program.program_length_days:
            enrollment.status = UserEnrollment.STATUS_COMPLETED
            enrollment.completed_at = timezone.now()
            enrollment.save(update_fields=["status", "completed_at"])

        return api_response(
            "Day completed!",
            data=DayCompletionSerializer(completion).data,
            status_code=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _get_enrollment(pk, user):
        try:
            return UserEnrollment.objects.select_related("program").get(pk=pk, user=user)
        except UserEnrollment.DoesNotExist:
            return None


# ─── BH-007: Log a slip/relapse ──────────────────────────────────────────────

@extend_schema(tags=["Motivation"])
class SlipView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Log a relapse/slip without resetting progress",
        operation_id="motivation_log_slip",
        responses={200: None},
    )
    def post(self, request, pk):
        try:
            enrollment = UserEnrollment.objects.get(pk=pk, user=request.user)
        except UserEnrollment.DoesNotExist:
            return api_response("Enrollment not found.", status_code=status.HTTP_404_NOT_FOUND)

        enrollment.last_slip_at = date.today()
        enrollment.slip_count += 1
        enrollment.save(update_fields=["last_slip_at", "slip_count"])

        return api_response(
            "Slip logged. Every stumble is a step on the path — keep going!",
            data={
                "days_since_last_slip": 0,
                "slip_count": enrollment.slip_count,
                "encouragement": (
                    "A slip is not a failure. Acknowledge it, learn from it, and continue "
                    "your journey. You still have everything you've built so far."
                ),
            },
        )


# ─── BH-008: Capture triggers ─────────────────────────────────────────────────

@extend_schema(tags=["Motivation"])
class TriggerView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Capture habit triggers for an enrollment",
        operation_id="motivation_capture_triggers",
        request=UserTriggerSerializer(many=True),
        responses={201: UserTriggerSerializer(many=True)},
    )
    def post(self, request, pk):
        try:
            enrollment = UserEnrollment.objects.get(pk=pk, user=request.user)
        except UserEnrollment.DoesNotExist:
            return api_response("Enrollment not found.", status_code=status.HTTP_404_NOT_FOUND)

        triggers_data = request.data.get("triggers", [])
        if not isinstance(triggers_data, list):
            return api_response(
                "Triggers must be a list.", status_code=status.HTTP_400_BAD_REQUEST
            )

        created = []
        for item in triggers_data:
            serializer = UserTriggerSerializer(data=item)
            if not serializer.is_valid():
                return api_response(
                    "Validation error.",
                    data=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            created.append(serializer.save(enrollment=enrollment))

        enrollment.triggers_captured = True
        enrollment.save(update_fields=["triggers_captured"])

        return api_response(
            "Triggers captured.",
            data=UserTriggerSerializer(created, many=True).data,
            status_code=status.HTTP_201_CREATED,
        )


# ─── BH-009: Urge SOS — activate ─────────────────────────────────────────────

@extend_schema(tags=["Motivation"])
class SOSActivateView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Activate urge SOS for an enrollment",
        operation_id="motivation_sos_activate",
        responses={201: UrgeSosSerializer},
    )
    def post(self, request, pk):
        try:
            enrollment = UserEnrollment.objects.select_related("program").get(
                pk=pk, user=request.user
            )
        except UserEnrollment.DoesNotExist:
            return api_response("Enrollment not found.", status_code=status.HTTP_404_NOT_FOUND)

        sos = UrgeSOS.objects.create(enrollment=enrollment)

        # Try to get urge-surfing audio from today's program day
        today = date.today()
        current_day = (today - enrollment.started_at).days + 1
        current_day = min(current_day, enrollment.program.program_length_days)
        audio_url = None
        try:
            program_day = ProgramDay.objects.select_related("audio").get(
                program=enrollment.program, day_number=current_day
            )
            if program_day.audio and program_day.audio.audio_file:
                audio_url = request.build_absolute_uri(program_day.audio.audio_file.url)
        except ProgramDay.DoesNotExist:
            pass

        quit_reasons = QuitReason.objects.filter(enrollment=enrollment)

        return api_response(
            "SOS activated. You can do this!",
            data={
                "sos_id": str(sos.id),
                "quit_reasons": QuitReasonSerializer(quit_reasons, many=True).data,
                "urge_surfing_audio_url": audio_url,
                "breathing_exercise": {
                    "duration_seconds": 60,
                    "pattern": "4-7-8",
                    "instructions": (
                        "Inhale for 4 seconds, hold for 7 seconds, exhale for 8 seconds. "
                        "Repeat until the urge passes."
                    ),
                },
            },
            status_code=status.HTTP_201_CREATED,
        )


# ─── BH-010: Urge SOS — update completion ────────────────────────────────────

@extend_schema(tags=["Motivation"])
class SOSUpdateView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Update SOS completion flags",
        operation_id="motivation_sos_update",
        request=UrgeSosSerializer,
        responses={200: UrgeSosSerializer},
    )
    def patch(self, request, pk):
        try:
            sos = UrgeSOS.objects.select_related("enrollment").get(pk=pk)
        except UrgeSOS.DoesNotExist:
            return api_response("SOS record not found.", status_code=status.HTTP_404_NOT_FOUND)

        if sos.enrollment.user_id != request.user.pk:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = UrgeSosSerializer(sos, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(
                "Validation error.",
                data=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return api_response("SOS updated.", data=serializer.data)


# ─── BH-011: Personal quit reasons ───────────────────────────────────────────

@extend_schema(tags=["Motivation"])
class QuitReasonListCreateView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List quit reasons for an enrollment",
        operation_id="motivation_quit_reasons_list",
        responses={200: QuitReasonSerializer(many=True)},
    )
    def get(self, request, pk):
        enrollment = self._get_enrollment(pk, request.user)
        if not enrollment:
            return api_response("Enrollment not found.", status_code=status.HTTP_404_NOT_FOUND)
        reasons = QuitReason.objects.filter(enrollment=enrollment)
        return api_response("Quit reasons retrieved.", data=QuitReasonSerializer(reasons, many=True).data)

    @extend_schema(
        summary="Add a quit reason",
        operation_id="motivation_quit_reasons_create",
        request=QuitReasonSerializer,
        responses={201: QuitReasonSerializer},
    )
    def post(self, request, pk):
        enrollment = self._get_enrollment(pk, request.user)
        if not enrollment:
            return api_response("Enrollment not found.", status_code=status.HTTP_404_NOT_FOUND)
        serializer = QuitReasonSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                "Validation error.",
                data=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        reason = serializer.save(enrollment=enrollment)
        return api_response(
            "Quit reason added.",
            data=QuitReasonSerializer(reason).data,
            status_code=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _get_enrollment(pk, user):
        try:
            return UserEnrollment.objects.get(pk=pk, user=user)
        except UserEnrollment.DoesNotExist:
            return None


@extend_schema(tags=["Motivation"])
class QuitReasonDeleteView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Delete a quit reason",
        operation_id="motivation_quit_reason_delete",
        responses={200: None},
    )
    def delete(self, request, pk):
        try:
            reason = QuitReason.objects.select_related("enrollment").get(pk=pk)
        except QuitReason.DoesNotExist:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)
        if reason.enrollment.user_id != request.user.pk:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)
        reason.delete()
        return api_response("Quit reason deleted.")


# ─── BH-012: Personal motivations (upload) ───────────────────────────────────

@extend_schema(tags=["Motivation"])
class PersonalMediaListCreateView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
    MAX_IMAGE_BYTES = 5 * 1024 * 1024   # 5 MB

    @extend_schema(
        summary="List personal motivation media for an enrollment",
        operation_id="motivation_personal_media_list",
        responses={200: PersonalMotivationSerializer(many=True)},
    )
    def get(self, request, pk):
        enrollment = self._get_enrollment(pk, request.user)
        if not enrollment:
            return api_response("Enrollment not found.", status_code=status.HTTP_404_NOT_FOUND)
        media = PersonalMotivation.objects.filter(enrollment=enrollment)
        return api_response(
            "Personal media retrieved.",
            data=PersonalMotivationSerializer(media, many=True, context={"request": request}).data,
        )

    @extend_schema(
        summary="Upload personal motivation media",
        operation_id="motivation_personal_media_upload",
        request=PersonalMotivationSerializer,
        responses={201: PersonalMotivationSerializer},
    )
    def post(self, request, pk):
        enrollment = self._get_enrollment(pk, request.user)
        if not enrollment:
            return api_response("Enrollment not found.", status_code=status.HTTP_404_NOT_FOUND)

        media_type = request.data.get("media_type")
        uploaded_file = request.FILES.get("file")

        if uploaded_file:
            if media_type == PersonalMotivation.MEDIA_AUDIO and uploaded_file.size > self.MAX_AUDIO_BYTES:
                return api_response(
                    "Audio file must be ≤ 10 MB.", status_code=status.HTTP_400_BAD_REQUEST
                )
            if media_type == PersonalMotivation.MEDIA_IMAGE and uploaded_file.size > self.MAX_IMAGE_BYTES:
                return api_response(
                    "Image file must be ≤ 5 MB.", status_code=status.HTTP_400_BAD_REQUEST
                )

        serializer = PersonalMotivationSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return api_response(
                "Validation error.",
                data=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        obj = serializer.save(user=request.user, enrollment=enrollment)
        return api_response(
            "Media uploaded.",
            data=PersonalMotivationSerializer(obj, context={"request": request}).data,
            status_code=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _get_enrollment(pk, user):
        try:
            return UserEnrollment.objects.get(pk=pk, user=user)
        except UserEnrollment.DoesNotExist:
            return None


# ─── BH-013: Admin — manage programs ─────────────────────────────────────────

@extend_schema(tags=["Motivation Admin"])
class AdminProgramListCreateView(ExceptionMixin, APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="[Admin] List all programs",
        operation_id="admin_motivation_programs_list",
        responses={200: AdminProgramSerializer(many=True)},
    )
    def get(self, request):
        qs = BadHabitProgram.objects.all()
        return api_response("Programs retrieved.", data=AdminProgramSerializer(qs, many=True).data)

    @extend_schema(
        summary="[Admin] Create a program",
        operation_id="admin_motivation_programs_create",
        request=AdminProgramSerializer,
        responses={201: AdminProgramSerializer},
    )
    def post(self, request):
        serializer = AdminProgramSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                "Validation error.",
                data=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        program = serializer.save()
        return api_response(
            "Program created.",
            data=AdminProgramSerializer(program).data,
            status_code=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Motivation Admin"])
class AdminProgramDetailView(ExceptionMixin, APIView):
    permission_classes = [IsAdminUser]

    def _get_obj(self, slug):
        try:
            return BadHabitProgram.objects.get(slug=slug)
        except BadHabitProgram.DoesNotExist:
            return None

    @extend_schema(
        summary="[Admin] Update a program",
        operation_id="admin_motivation_programs_update",
        request=AdminProgramSerializer,
        responses={200: AdminProgramSerializer},
    )
    def patch(self, request, slug):
        program = self._get_obj(slug)
        if not program:
            return api_response("Program not found.", status_code=status.HTTP_404_NOT_FOUND)
        serializer = AdminProgramSerializer(program, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(
                "Validation error.",
                data=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        program = serializer.save()
        return api_response("Program updated.", data=AdminProgramSerializer(program).data)

    @extend_schema(
        summary="[Admin] Delete a program",
        operation_id="admin_motivation_programs_delete",
        responses={200: None},
    )
    def delete(self, request, slug):
        program = self._get_obj(slug)
        if not program:
            return api_response("Program not found.", status_code=status.HTTP_404_NOT_FOUND)
        program.delete()
        return api_response("Program deleted.")


# ─── BH-014: Admin — manage program days ─────────────────────────────────────

@extend_schema(tags=["Motivation Admin"])
class AdminProgramDayListCreateView(ExceptionMixin, APIView):
    permission_classes = [IsAdminUser]

    def _get_program(self, slug):
        try:
            return BadHabitProgram.objects.get(slug=slug)
        except BadHabitProgram.DoesNotExist:
            return None

    @extend_schema(
        summary="[Admin] List days for a program",
        operation_id="admin_motivation_days_list",
        responses={200: AdminProgramDaySerializer(many=True)},
    )
    def get(self, request, slug):
        program = self._get_program(slug)
        if not program:
            return api_response("Program not found.", status_code=status.HTTP_404_NOT_FOUND)
        days = ProgramDay.objects.filter(program=program).select_related("audio")
        return api_response(
            "Days retrieved.",
            data=AdminProgramDaySerializer(days, many=True, context={"request": request}).data,
        )

    @extend_schema(
        summary="[Admin] Create a program day",
        operation_id="admin_motivation_days_create",
        request=AdminProgramDaySerializer,
        responses={201: AdminProgramDaySerializer},
    )
    def post(self, request, slug):
        program = self._get_program(slug)
        if not program:
            return api_response("Program not found.", status_code=status.HTTP_404_NOT_FOUND)
        serializer = AdminProgramDaySerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return api_response(
                "Validation error.",
                data=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        day = serializer.save(program=program)
        return api_response(
            "Day created.",
            data=AdminProgramDaySerializer(day, context={"request": request}).data,
            status_code=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Motivation Admin"])
class AdminProgramDayDetailView(ExceptionMixin, APIView):
    permission_classes = [IsAdminUser]

    def _get_obj(self, pk):
        try:
            return ProgramDay.objects.select_related("audio", "program").get(pk=pk)
        except ProgramDay.DoesNotExist:
            return None

    @extend_schema(
        summary="[Admin] Update a program day",
        operation_id="admin_motivation_day_update",
        request=AdminProgramDaySerializer,
        responses={200: AdminProgramDaySerializer},
    )
    def patch(self, request, pk):
        day = self._get_obj(pk)
        if not day:
            return api_response("Day not found.", status_code=status.HTTP_404_NOT_FOUND)
        serializer = AdminProgramDaySerializer(
            day, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return api_response(
                "Validation error.",
                data=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        day = serializer.save()
        return api_response(
            "Day updated.",
            data=AdminProgramDaySerializer(day, context={"request": request}).data,
        )

    @extend_schema(
        summary="[Admin] Delete a program day",
        operation_id="admin_motivation_day_delete",
        responses={200: None},
    )
    def delete(self, request, pk):
        day = self._get_obj(pk)
        if not day:
            return api_response("Day not found.", status_code=status.HTTP_404_NOT_FOUND)
        day.delete()
        return api_response("Day deleted.")

