"""Utility helpers for the subscriptions app."""

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from utils.response import api_response

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entitlements (merged from entitlements.py)
# ---------------------------------------------------------------------------

TIER_LEVELS = {"free": 0, "premium": 1}


def get_user_tier(user) -> str:
    """Get current active tier for user."""
    try:
        sub = user.subscription
        if sub.status == "active" and sub.tier:
            # Check not expired
            if sub.expires_at is None or sub.expires_at > timezone.now():
                return sub.tier
    except Exception:
        pass
    return "free"


class IsPremium(BasePermission):
    """Permission class: requires premium tier."""
    message = "This feature requires a Premium subscription."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        tier = get_user_tier(request.user)
        return TIER_LEVELS.get(tier, 0) >= TIER_LEVELS["premium"]


def require_premium(user):
    """Raise 402 if user is not premium. Call inside view methods."""
    tier = get_user_tier(user)
    if TIER_LEVELS.get(tier, 0) < TIER_LEVELS["premium"]:
        from rest_framework.exceptions import APIException

        class PaymentRequired(APIException):
            status_code = 402
            default_code = "UPGRADE_REQUIRED"
            default_detail = "This feature requires a Premium subscription."

        raise PaymentRequired()


# ---------------------------------------------------------------------------
# Receipt verification (merged from receipt_verifier.py)
# ---------------------------------------------------------------------------

def verify_apple_receipt(receipt_data: str, product_id: str) -> dict:
    """
    Verify Apple IAP receipt.
    In production: POST to https://buy.itunes.apple.com/verifyReceipt
    Returns dict with: valid (bool), expires_at (datetime|None), subscription_id (str)
    """
    # Mock implementation — replace with real Apple verification
    logger.warning("Apple receipt verification is using mock implementation.")
    return {
        "valid": True,
        "expires_at": timezone.now() + timedelta(days=30),
        "subscription_id": f"apple_{product_id}_{receipt_data[:8]}",
        "product_id": product_id,
    }


def verify_google_purchase(purchase_token: str, product_id: str) -> dict:
    """
    Verify Google Play purchase.
    In production: Use Google Play Developer API
    Returns dict with: valid (bool), expires_at (datetime|None), subscription_id (str)
    """
    logger.warning("Google purchase verification is using mock implementation.")
    return {
        "valid": True,
        "expires_at": timezone.now() + timedelta(days=30),
        "subscription_id": f"google_{product_id}_{purchase_token[:8]}",
        "product_id": product_id,
    }
