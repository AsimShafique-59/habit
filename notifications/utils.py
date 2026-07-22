"""
Firebase FCM helper.
If FIREBASE_CREDENTIALS_JSON is set in .env, real pushes are sent.
Otherwise, push is logged to console (dev mode).
"""
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)
_firebase_initialized = False


def _init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return True
    creds_json = getattr(settings, "FIREBASE_CREDENTIALS_JSON", "")
    if not creds_json:
        return False
    try:
        import os
        import firebase_admin
        from firebase_admin import credentials
        # Support both a file path and a raw JSON string
        if os.path.isfile(creds_json):
            cred = credentials.Certificate(creds_json)
        else:
            cred = credentials.Certificate(json.loads(creds_json))
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        logger.info("Firebase initialized.")
        return True
    except Exception:
        logger.exception("Firebase init failed.")
        return False


def send_push(token: str, title: str, body: str, data: dict = None):
    """Send a single FCM push notification. Falls back to console log if not configured."""
    if not _init_firebase():
        logger.info("[FCM-DEV] token=%s | %s: %s | data=%s", token[:20], title, body, data)
        return

    try:
        from firebase_admin import messaging
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={str(k): str(v) for k, v in (data or {}).items()},
            token=token,
        )
        response = messaging.send(message)
        logger.info("FCM sent: %s", response)
    except Exception:
        logger.exception("FCM send failed for token=%s", token[:20])


def send_push_multicast(tokens: list, title: str, body: str, data: dict = None):
    """Send to multiple device tokens at once."""
    if not tokens:
        return
    if not _init_firebase():
        for t in tokens:
            logger.info("[FCM-DEV] token=%s | %s: %s", t[:20], title, body)
        return

    try:
        from firebase_admin import messaging
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data={str(k): str(v) for k, v in (data or {}).items()},
            tokens=tokens,
        )
        response = messaging.send_each_for_multicast(message)
        logger.info("FCM multicast: success=%d fail=%d", response.success_count, response.failure_count)
    except Exception:
        logger.exception("FCM multicast failed.")
