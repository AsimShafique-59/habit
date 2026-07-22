"""Utility helpers for the authentication app."""

import base64
import logging
import re

import jwt
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from django.conf import settings
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


def _app_name():
    return getattr(settings, "APP_NAME", "Habit Tracker")


def send_verification_email(user, token):
    base = settings.FRONTEND_BASE_URL.rstrip('/')
    verify_url = f"{base}/auth/verify-email/?token={token}"
    app = _app_name()
    send_mail(
        subject=f"Verify your email – {app}",
        message=(
            f"Hi {user.name or user.email},\n\n"
            f"Verify your email by clicking the link below:\n{verify_url}\n\n"
            f"This link expires in {settings.EMAIL_VERIFICATION_TTL_HOURS} hours.\n\n"
            f"If you did not create an account, ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def send_password_reset_email(user, token):
    base = settings.FRONTEND_BASE_URL.rstrip('/')
    reset_url = f"{base}/auth/password-reset/complete/?token={token}"
    app = _app_name()
    send_mail(
        subject=f"Reset your password – {app}",
        message=(
            f"Hi {user.name or user.email},\n\n"
            f"Reset your password by clicking the link below:\n{reset_url}\n\n"
            f"This link expires in {settings.PASSWORD_RESET_TTL_HOURS} hour(s).\n\n"
            f"If you didn't request this, ignore this email — your password won't change."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def send_password_reset_confirmation_email(user):
    app = _app_name()
    send_mail(
        subject=f"Your password has been changed – {app}",
        message=(
            f"Hi {user.name or user.email},\n\n"
            f"Your {app} password was just changed successfully.\n\n"
            "All active sessions have been logged out for your security.\n\n"
            "If you didn't make this change, contact support immediately."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def send_account_deletion_email(user, cancel_token):
    base = settings.FRONTEND_BASE_URL.rstrip('/')
    cancel_url = f"{base}/auth/delete/cancel/{cancel_token}/"
    app = _app_name()
    send_mail(
        subject=f"Your {app} account is scheduled for deletion",
        message=(
            f"Hi {user.name or user.email},\n\n"
            f"Your {app} account has been scheduled for permanent deletion in 30 days.\n\n"
            "Changed your mind? Cancel the deletion here (valid for 30 days):\n"
            f"{cancel_url}\n\n"
            "After 30 days, all your data will be permanently removed."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def verify_google_token(id_token_str):
    """Verify Google ID token, return claims dict or None."""
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        idinfo = google_id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
        return idinfo
    except Exception:
        return None


def verify_apple_token(identity_token_str):
    """Verify Apple identity token, return claims dict or None."""
    try:
        apple_keys_url = settings.APPLE_KEYS_URL
        apple_keys_timeout = settings.APPLE_KEYS_TIMEOUT

        resp = requests.get(apple_keys_url, timeout=apple_keys_timeout)
        apple_keys = resp.json()["keys"]

        header = jwt.get_unverified_header(identity_token_str)
        kid = header.get("kid")
        key_data = next((k for k in apple_keys if k["kid"] == kid), None)
        if not key_data:
            return None

        public_key = _build_rsa_key(key_data)
        claims = jwt.decode(
            identity_token_str,
            public_key,
            algorithms=["RS256"],
            audience=settings.APPLE_CLIENT_ID,
        )
        return claims
    except Exception:
        return None


def _build_rsa_key(key_data):
    def _b64url_to_int(val):
        padding = 4 - len(val) % 4
        val += "=" * padding
        return int.from_bytes(base64.urlsafe_b64decode(val), "big")

    n = _b64url_to_int(key_data["n"])
    e = _b64url_to_int(key_data["e"])
    return RSAPublicNumbers(e, n).public_key(default_backend())


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def write_audit_log(user, action, request=None, metadata=None):
    from .models import AuditLog

    AuditLog.objects.create(
        user=user,
        action=action,
        ip_address=get_client_ip(request) if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Validators (merged from validators.py)
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

BCP47_PATTERN = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$")
TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def validate_email_unique_ci(email):
    from .models import User
    if User.objects.filter(email__iexact=email).exists():
        raise ValueError("EMAIL_TAKEN")


def validate_email_mx(email):
    """Reject email if the domain has no MX records."""
    import dns.resolver
    domain = email.split("@")[-1].lower()
    try:
        dns.resolver.resolve(domain, "MX")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        raise ValueError("INVALID_EMAIL_DOMAIN")
    except Exception as e:
        # Network/timeout issues — log but allow through to avoid blocking signup
        logger.warning("MX lookup failed for domain %s: %s", domain, e)


def normalize_locale(locale):
    if locale and BCP47_PATTERN.match(locale):
        return locale
    return "en-US"


def normalize_timezone(tz):
    try:
        import pytz
        pytz.timezone(tz)
        return tz
    except Exception:
        return "UTC"
