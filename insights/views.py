import logging
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from utils.response import ExceptionMixin, api_response
from .models import AudioContent, Category, UserInsightInteraction
from .serializers import *

logger = logging.getLogger(__name__)


# ─── User: Category List ──────────────────────────────────────────────────────

@extend_schema(tags=["Insights"])
class CategoryListView(ExceptionMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="List active categories",
        operation_id="insights_categories_list",
        responses={200: CategorySerializer(many=True)},
    )
    def get(self, request):
        qs = Category.objects.filter(is_active=True)
        serializer = CategorySerializer(qs, many=True)
        return api_response("Categories retrieved.", data=serializer.data)


# ─── User: Audios by Category ─────────────────────────────────────────────────

@extend_schema(tags=["Insights"])
class CategoryAudioListView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get published audios for a category",
        operation_id="insights_category_audios",
        responses={200: AudioContentSerializer(many=True)},
    )
    def get(self, request, slug):
        try:
            category = Category.objects.get(slug=slug, is_active=True)
        except Category.DoesNotExist:
            return api_response("Category not found.", status_code=status.HTTP_404_NOT_FOUND)
        qs = AudioContent.objects.filter(
            category=category, is_published=True
        ).select_related("category")
        serializer = AudioContentSerializer(qs, many=True, context={"request": request})
        return api_response(
            f"Audios for '{category.name}' retrieved.",
            data={"category": CategorySerializer(category).data, "audios": serializer.data},
        )


# ─── User: Audio List & Detail ────────────────────────────────────────────────

@extend_schema(tags=["Insights"])
class AudioContentListView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List all published audio content",
        operation_id="insights_list",
        responses={200: AudioContentSerializer(many=True)},
    )
    def get(self, request):
        qs = AudioContent.objects.filter(is_published=True).select_related("category")
        serializer = AudioContentSerializer(qs, many=True, context={"request": request})
        return api_response("Audio content retrieved.", data=serializer.data)


@extend_schema(tags=["Insights"])
class AudioContentDetailView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get a single audio content item",
        operation_id="insights_detail",
        responses={200: AudioContentSerializer},
    )
    def get(self, request, pk):
        try:
            obj = AudioContent.objects.select_related("category").get(pk=pk, is_published=True)
        except AudioContent.DoesNotExist:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)
        serializer = AudioContentSerializer(obj, context={"request": request})
        return api_response("Audio content retrieved.", data=serializer.data)


# ─── Admin: Category CRUD ─────────────────────────────────────────────────────

@extend_schema(tags=["Insights (Admin)"])
class AdminCategoryListView(ExceptionMixin, APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="[Admin] List all categories",
        operation_id="admin_categories_list",
        responses={200: CategorySerializer(many=True)},
    )
    def get(self, request):
        qs = Category.objects.all()
        return api_response("Categories retrieved.", data=CategorySerializer(qs, many=True).data)

    @extend_schema(
        summary="[Admin] Create category",
        operation_id="admin_categories_create",
        request=CategoryCreateSerializer,
        responses={201: CategorySerializer},
    )
    def post(self, request):
        serializer = CategoryCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response("Validation error.", data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        obj = serializer.save()
        return api_response("Category created.", data=CategorySerializer(obj).data, status_code=status.HTTP_201_CREATED)


@extend_schema(tags=["Insights (Admin)"])
class AdminCategoryDetailView(ExceptionMixin, APIView):
    permission_classes = [IsAdminUser]

    def _get_obj(self, pk):
        try:
            return Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return None

    @extend_schema(
        summary="[Admin] Update category",
        operation_id="admin_categories_update",
        request=CategoryCreateSerializer,
        responses={200: CategorySerializer},
    )
    def patch(self, request, pk):
        obj = self._get_obj(pk)
        if not obj:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)
        serializer = CategoryCreateSerializer(obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response("Validation error.", data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        obj = serializer.save()
        return api_response("Category updated.", data=CategorySerializer(obj).data)

    @extend_schema(
        summary="[Admin] Delete category",
        operation_id="admin_categories_delete",
        responses={200: None},
    )
    def delete(self, request, pk):
        obj = self._get_obj(pk)
        if not obj:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return api_response("Category deleted.")


# ─── Admin: Audio CRUD ────────────────────────────────────────────────────────

@extend_schema(tags=["Insights (Admin)"])
class AdminAudioContentListView(ExceptionMixin, APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="[Admin] List all audio content",
        operation_id="admin_insights_list",
        responses={200: AudioContentSerializer(many=True)},
    )
    def get(self, request):
        qs = AudioContent.objects.all().select_related("category").order_by("-created_at")
        serializer = AudioContentSerializer(qs, many=True, context={"request": request})
        return api_response("All audio content retrieved.", data=serializer.data)

    @extend_schema(
        summary="[Admin] Upload new audio content",
        operation_id="admin_insights_create",
        request=AudioContentCreateSerializer,
        responses={201: AudioContentSerializer},
    )
    def post(self, request):
        serializer = AudioContentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response("Validation error.", data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        obj = serializer.save()
        out = AudioContentSerializer(obj, context={"request": request})
        return api_response("Audio content created.", data=out.data, status_code=status.HTTP_201_CREATED)


@extend_schema(tags=["Insights (Admin)"])
class AdminAudioContentDetailView(ExceptionMixin, APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def _get_obj(self, pk):
        try:
            return AudioContent.objects.select_related("category").get(pk=pk)
        except AudioContent.DoesNotExist:
            return None

    @extend_schema(
        summary="[Admin] Get any audio content item",
        operation_id="admin_insights_detail",
        responses={200: AudioContentSerializer},
    )
    def get(self, request, pk):
        obj = self._get_obj(pk)
        if not obj:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)
        return api_response("Audio content retrieved.", data=AudioContentSerializer(obj, context={"request": request}).data)

    @extend_schema(
        summary="[Admin] Update audio content",
        operation_id="admin_insights_update",
        request=AudioContentCreateSerializer,
        responses={200: AudioContentSerializer},
    )
    def patch(self, request, pk):
        obj = self._get_obj(pk)
        if not obj:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)
        serializer = AudioContentCreateSerializer(obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response("Validation error.", data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        obj = serializer.save()
        return api_response("Audio content updated.", data=AudioContentSerializer(obj, context={"request": request}).data)

    @extend_schema(
        summary="[Admin] Delete audio content",
        operation_id="admin_insights_delete",
        responses={200: None},
    )
    def delete(self, request, pk):
        obj = self._get_obj(pk)
        if not obj:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return api_response("Audio content deleted.")


# ─── DI-004: Save / Favourite / Note ─────────────────────────────────────────

def _get_interaction(user, pk):
    """Get or initialise (unsaved) interaction object for a given audio content."""
    try:
        content = AudioContent.objects.get(pk=pk, is_published=True)
    except AudioContent.DoesNotExist:
        return None, None
    obj, _ = UserInsightInteraction.objects.get_or_create(user=user, audio_content=content)
    return content, obj


@extend_schema(tags=["Insights"])
class InsightSaveView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Save an insight (DI-004)", operation_id="insights_save")
    def post(self, request, pk):
        content, interaction = _get_interaction(request.user, pk)
        if content is None:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)
        interaction.is_saved = True
        interaction.save(update_fields=["is_saved", "updated_at"])
        return api_response("Insight saved.", data={"insight_id": str(pk), "is_saved": True})

    @extend_schema(summary="Unsave an insight (DI-004)", operation_id="insights_unsave")
    def delete(self, request, pk):
        content, interaction = _get_interaction(request.user, pk)
        if content is None:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)
        interaction.is_saved = False
        interaction.save(update_fields=["is_saved", "updated_at"])
        return api_response("Insight unsaved.", data={"insight_id": str(pk), "is_saved": False})


@extend_schema(tags=["Insights"])
class InsightFavoriteView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Favourite an insight (DI-004)", operation_id="insights_favorite")
    def post(self, request, pk):
        content, interaction = _get_interaction(request.user, pk)
        if content is None:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)
        interaction.is_favorited = True
        interaction.save(update_fields=["is_favorited", "updated_at"])
        return api_response("Insight favourited.", data={"insight_id": str(pk), "is_favorited": True})

    @extend_schema(summary="Un-favourite an insight (DI-004)", operation_id="insights_unfavorite")
    def delete(self, request, pk):
        content, interaction = _get_interaction(request.user, pk)
        if content is None:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)
        interaction.is_favorited = False
        interaction.save(update_fields=["is_favorited", "updated_at"])
        return api_response("Insight un-favourited.", data={"insight_id": str(pk), "is_favorited": False})


@extend_schema(tags=["Insights"])
class InsightNoteView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Add / update a personal note on an insight (DI-004)", operation_id="insights_note")
    def put(self, request, pk):
        content, interaction = _get_interaction(request.user, pk)
        if content is None:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)
        note = request.data.get("note", "")
        if not isinstance(note, str):
            return api_response("'note' must be a string.", status_code=status.HTTP_400_BAD_REQUEST)
        interaction.note = note
        interaction.save(update_fields=["note", "updated_at"])
        return api_response("Note saved.", data={"insight_id": str(pk), "note": note})


# ─── DI-006: Offline download (premium-gated) ────────────────────────────────

@extend_schema(tags=["Insights"])
class InsightDownloadView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get download URL for offline playback — premium only (DI-006)",
        operation_id="insights_download",
    )
    def post(self, request, pk):
        user = request.user
        if getattr(user, "subscription_tier", "free") != "premium":
            return api_response(
                "This feature requires a premium subscription.",
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
            )
        try:
            content = AudioContent.objects.get(pk=pk, is_published=True)
        except AudioContent.DoesNotExist:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)

        if not content.audio_file:
            return api_response("Audio file not available.", status_code=status.HTTP_404_NOT_FOUND)

        audio_url = request.build_absolute_uri(content.audio_file.url)
        return api_response(
            "Download URL generated.",
            data={
                "insight_id": str(pk),
                "download_url": audio_url,
                "title": content.title,
                "duration_seconds": content.duration_seconds,
            },
        )
