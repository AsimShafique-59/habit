import logging
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers
from utils.response import ExceptionMixin, api_response
from .models import DeviceToken, Notification
from .serializers import DeviceTokenSerializer, NotificationSerializer

logger = logging.getLogger(__name__)


@extend_schema(tags=["Notifications"])
class DeviceTokenView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Register device push token",
        operation_id="notifications_device_token_register",
        request=DeviceTokenSerializer,
        responses={201: DeviceTokenSerializer, 200: DeviceTokenSerializer},
    )
    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        platform = serializer.validated_data["platform"]

        DeviceToken.objects.filter(token=token).exclude(user=request.user).update(is_active=False)
        obj, created = DeviceToken.objects.update_or_create(
            token=token,
            defaults={"user": request.user, "platform": platform, "is_active": True},
        )
        logger.info("Device token %s: user=%s platform=%s", "registered" if created else "updated", request.user.email, platform)
        return api_response(
            "Device token registered.",
            data=DeviceTokenSerializer(obj).data,
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Deactivate device push token",
        operation_id="notifications_device_token_deactivate",
        request=inline_serializer("DeactivateTokenRequest", fields={"token": drf_serializers.CharField()}),
        responses={200: inline_serializer("DeactivateTokenResponse", fields={
            "status": drf_serializers.IntegerField(),
            "message": drf_serializers.CharField(),
            "data": drf_serializers.DictField(),
        })},
    )
    def delete(self, request):
        token = request.data.get("token", "")
        if not token:
            return api_response("token is required.", status_code=status.HTTP_400_BAD_REQUEST)
        updated = DeviceToken.objects.filter(user=request.user, token=token).update(is_active=False)
        if not updated:
            return api_response("Token not found.", status_code=status.HTTP_404_NOT_FOUND)
        logger.info("Device token deactivated: user=%s", request.user.email)
        return api_response("Device token deactivated.")


@extend_schema(tags=["Notifications"])
class NotificationListView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List notifications",
        operation_id="notifications_list",
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        if request.query_params.get("unread") == "true":
            qs = qs.filter(is_read=False)
        serializer = NotificationSerializer(qs[:50], many=True)
        return api_response("Notifications retrieved.", data={
            "items": serializer.data,
            "unread_count": Notification.objects.filter(user=request.user, is_read=False).count(),
        })


@extend_schema(tags=["Notifications"])
class NotificationReadView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mark notification as read",
        operation_id="notifications_mark_read",
        request=None,
        responses={200: NotificationSerializer},
    )
    def patch(self, request, pk):
        try:
            notif = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return api_response("Not found.", status_code=status.HTTP_404_NOT_FOUND)
        if not notif.is_read:
            notif.is_read = True
            notif.read_at = timezone.now()
            notif.save(update_fields=["is_read", "read_at"])
        return api_response("Notification marked as read.", data=NotificationSerializer(notif).data)


@extend_schema(tags=["Notifications"])
class NotificationMarkAllReadView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mark all notifications as read",
        operation_id="notifications_mark_all_read",
        request=None,
        responses={200: inline_serializer("MarkAllReadResponse", fields={
            "status": drf_serializers.IntegerField(),
            "message": drf_serializers.CharField(),
            "data": drf_serializers.DictField(),
        })},
    )
    def post(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        logger.info("Mark all read: user=%s count=%d", request.user.email, count)
        return api_response(f"{count} notifications marked as read.")
