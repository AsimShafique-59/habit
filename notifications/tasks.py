"""Celery tasks for push notifications."""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_push_to_user(user_id, title, body, notification_type="system", data=None):
    """
    Create an in-app Notification record and send FCM push to all
    active device tokens for the user.
    """
    from django.contrib.auth import get_user_model
    from .models import DeviceToken, Notification
    from .utils import send_push_multicast

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error("send_push_to_user: user %s not found", user_id)
        return

    # Save in-app notification
    Notification.objects.create(
        user=user,
        title=title,
        body=body,
        notification_type=notification_type,
        data=data or {},
    )

    # Send FCM push to all active device tokens
    tokens = list(
        DeviceToken.objects.filter(user=user, is_active=True).values_list("token", flat=True)
    )
    if tokens:
        send_push_multicast(tokens, title, body, data)

    logger.info("Push sent: user=%s title=%s tokens=%d", user.email, title, len(tokens))
