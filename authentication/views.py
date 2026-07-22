import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from utils.response import ExceptionMixin, api_response
from .models import AuditLog, DataExport, DeleteCancelToken, EmailVerificationToken, PasswordResetToken
from .serializers import *
from .tasks import export_user_data_task
from .utils import *

User = get_user_model()
logger = logging.getLogger(__name__)


# Email/password sign-up

@extend_schema(tags=['Auth'])
class SignupEmailView(ExceptionMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Sign up with email & password',
        request=SignupSerializer,
        responses={
            201: inline_serializer('SignupResponse', fields={
                'status': drf_serializers.IntegerField(),
                'message': drf_serializers.CharField(),
                'data': inline_serializer('SignupData', fields={
                    'user': UserInfoSerializer(),
                    'tokens': inline_serializer('SignupTokens', fields={
                        'access': drf_serializers.CharField(),
                        'refresh': drf_serializers.CharField(),
                    }),
                    'email_verified': drf_serializers.BooleanField(),
                }),
            }),
        },
        auth=[],
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            flat = str(serializer.errors)
            if 'EMAIL_TAKEN' in flat:
                logger.warning('Signup rejected — email taken: %s', request.data.get('email', ''))
                return api_response('An account with this email already exists.', status_code=status.HTTP_409_CONFLICT)
            if 'INVALID_EMAIL_DOMAIN' in flat:
                logger.warning('Signup rejected — no MX record: %s', request.data.get('email', ''))
                return api_response('Email domain does not exist or cannot receive emails.', status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
            errors = {f: (v[0] if isinstance(v, list) else v) for f, v in serializer.errors.items()}
            return api_response(str(next(iter(errors.values()))), data=errors, status_code=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        token_obj = EmailVerificationToken.create_for_user(user)
        send_verification_email(user, token_obj.token)
        write_audit_log(user, 'signup_email', request)
        logger.info('New user signed up: %s (id=%s)', user.email, user.id)

        return api_response(
            'Account created. Please verify your email.',
            data={
                'user': UserInfoSerializer(user).data,
                'tokens': get_tokens_for_user(user),
                'email_verified': False,
            },
            status_code=status.HTTP_201_CREATED,
        )


# Apple Sign-In
@extend_schema(tags=['Auth'])
class AppleSignInView(ExceptionMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Sign in / sign up with Apple ID',
        request=AppleSignInSerializer,
        responses={200: inline_serializer('AppleAuthResponse', fields={
            'status': drf_serializers.IntegerField(),
            'message': drf_serializers.CharField(),
            'data': inline_serializer('AppleAuthData', fields={
                'user': UserInfoSerializer(),
                'tokens': inline_serializer('AppleTokens', fields={
                    'access': drf_serializers.CharField(),
                    'refresh': drf_serializers.CharField(),
                }),
                'is_new_user': drf_serializers.BooleanField(),
            }),
        })},
        auth=[],
    )
    def post(self, request):
        serializer = AppleSignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        claims = verify_apple_token(data['identity_token'])
        if not claims:
            logger.warning('Apple Sign-In — invalid token (ip=%s)', request.META.get('REMOTE_ADDR'))
            return api_response('Invalid or expired Apple identity token.', status_code=status.HTTP_401_UNAUTHORIZED)

        apple_sub = claims['sub']
        email = claims.get('email', '')
        is_new_user = False

        user = User.objects.filter(apple_id=apple_sub).first()
        if not user:
            email_user = User.objects.filter(email__iexact=email).first() if email else None
            if email_user:
                email_user.apple_id = apple_sub
                email_user.save(update_fields=['apple_id'])
                user = email_user
            else:
                is_new_user = True
                user = User.objects.create_user(
                    username=email or apple_sub,
                    email=email or f'{apple_sub}@privaterelay.appleid.com',
                    password=None,
                    name=data.get('name', '') or '',
                    locale=data.get('locale', 'en-US'),
                    timezone=data.get('timezone', 'UTC'),
                    apple_id=apple_sub,
                    email_verified=True,
                )

        write_audit_log(user, 'signin_apple', request, {'is_new_user': is_new_user})
        logger.info('Apple Sign-In: user=%s is_new=%s', user.email, is_new_user)

        return api_response(
            'Authenticated successfully.',
            data={
                'user': UserInfoSerializer(user).data,
                'tokens': get_tokens_for_user(user),
                'is_new_user': is_new_user,
            },
        )



# Google Sign-In
@extend_schema(tags=['Auth'])
class GoogleSignInView(ExceptionMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Sign in / sign up with Google',
        request=GoogleSignInSerializer,
        responses={200: inline_serializer('GoogleAuthResponse', fields={
            'status': drf_serializers.IntegerField(),
            'message': drf_serializers.CharField(),
            'data': inline_serializer('GoogleAuthData', fields={
                'user': UserInfoSerializer(),
                'tokens': inline_serializer('GoogleTokens', fields={
                    'access': drf_serializers.CharField(),
                    'refresh': drf_serializers.CharField(),
                }),
                'is_new_user': drf_serializers.BooleanField(),
            }),
        })},
        auth=[],
    )
    def post(self, request):
        serializer = GoogleSignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        claims = verify_google_token(data['id_token'])
        if not claims:
            logger.warning('Google Sign-In — invalid token (ip=%s)', request.META.get('REMOTE_ADDR'))
            return api_response('Invalid or expired Google ID token.', status_code=status.HTTP_401_UNAUTHORIZED)

        google_sub = claims['sub']
        email = claims.get('email', '')
        is_new_user = False

        user = User.objects.filter(google_id=google_sub).first()
        if not user:
            email_user = User.objects.filter(email__iexact=email).first() if email else None
            if email_user:
                email_user.google_id = google_sub
                email_user.save(update_fields=['google_id'])
                user = email_user
            else:
                is_new_user = True
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=None,
                    name=claims.get('name', ''),
                    locale=data.get('locale', 'en-US'),
                    timezone=data.get('timezone', 'UTC'),
                    google_id=google_sub,
                    email_verified=claims.get('email_verified', False),
                )

        write_audit_log(user, 'signin_google', request, {'is_new_user': is_new_user})
        logger.info('Google Sign-In: user=%s is_new=%s', user.email, is_new_user)

        return api_response(
            'Authenticated successfully.',
            data={
                'user': UserInfoSerializer(user).data,
                'tokens': get_tokens_for_user(user),
                'is_new_user': is_new_user,
            },
        )


# login
@extend_schema(tags=['Auth'])
class LoginView(ExceptionMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Login with email & password',
        request=LoginSerializer,
        responses={
            200: inline_serializer('LoginResponse', fields={
                'status': drf_serializers.IntegerField(),
                'message': drf_serializers.CharField(),
                'data': inline_serializer('LoginData', fields={
                    'user': UserInfoSerializer(),
                    'tokens': inline_serializer('LoginTokens', fields={
                        'access': drf_serializers.CharField(),
                        'refresh': drf_serializers.CharField(),
                    }),
                }),
            }),
        },
        auth=[],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            errors = {f: (v[0] if isinstance(v, list) else v) for f, v in serializer.errors.items()}
            return api_response(str(next(iter(errors.values()))), data=errors, status_code=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            logger.warning('Login failed — email not found (ip=%s)', request.META.get('REMOTE_ADDR'))
            return api_response('Invalid email or password.', status_code=status.HTTP_401_UNAUTHORIZED)

        if user.deleted_at:
            logger.warning('Login rejected — account deactivated: %s', email)
            return api_response('This account has been deactivated.', status_code=status.HTTP_403_FORBIDDEN)

        if not user.check_password(password):
            write_audit_log(user, 'login_failed', request)
            logger.warning('Login failed — wrong password: %s', email)
            return api_response('Invalid email or password.', status_code=status.HTTP_401_UNAUTHORIZED)

        write_audit_log(user, 'login_success', request)
        logger.info('Login success: %s (id=%s)', user.email, user.id)

        return api_response(
            'Login successful.',
            data={
                'user': UserInfoSerializer(user).data,
                'tokens': get_tokens_for_user(user),
            },
        )


# ---------------------------------------------------------------------------
# AUTH-005 — Token refresh
# ---------------------------------------------------------------------------
@extend_schema(tags=['Auth'])
class TokenRefreshView(ExceptionMixin, BaseTokenRefreshView):
    @extend_schema(
        summary='Refresh access token',
        description='Exchange a valid refresh token for a new access + refresh pair (rotation).',
        request=inline_serializer('TokenRefreshRequest', fields={
            'refresh': drf_serializers.CharField(),
        }),
        responses={200: inline_serializer('TokenRefreshResponse', fields={
            'status': drf_serializers.IntegerField(),
            'message': drf_serializers.CharField(),
            'data': inline_serializer('TokenRefreshData', fields={
                'access': drf_serializers.CharField(),
                'refresh': drf_serializers.CharField(),
            }),
        })},
        auth=[],
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return api_response('Token refreshed.', data=response.data)
        detail = response.data.get('detail', 'Invalid or expired refresh token.')
        return api_response(str(detail), status_code=response.status_code)


# ---------------------------------------------------------------------------
# AUTH-007 — Email verification
# ---------------------------------------------------------------------------
@extend_schema(tags=['Auth'])
class VerifyEmailView(ExceptionMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Verify email address via token',
        responses={200: inline_serializer('VerifyEmailResponse', fields={
            'status': drf_serializers.IntegerField(),
            'message': drf_serializers.CharField(),
            'data': drf_serializers.DictField(),
        })},
        auth=[],
    )
    def get(self, request):
        token_str = request.query_params.get('token', '')

        try:
            token_obj = EmailVerificationToken.objects.select_related('user').get(token=token_str)
        except EmailVerificationToken.DoesNotExist:
            return api_response('Invalid verification token.', status_code=status.HTTP_400_BAD_REQUEST)

        if not token_obj.is_valid:
            return api_response('Verification token has expired. Please request a new one.', status_code=status.HTTP_400_BAD_REQUEST)

        token_obj.consumed = True
        token_obj.save(update_fields=['consumed'])

        if not token_obj.user.email_verified:
            token_obj.user.email_verified = True
            token_obj.user.save(update_fields=['email_verified'])
            write_audit_log(token_obj.user, 'email_verified', request)
            logger.info('Email verified: user=%s', token_obj.user.email)

        return api_response('Email verified successfully.')


# ---------------------------------------------------------------------------
# AUTH-007b — Resend verification email
# ---------------------------------------------------------------------------
@extend_schema(tags=['Auth'])
class ResendVerificationView(ExceptionMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Resend email verification link',
        request=ResendVerificationSerializer,
        responses={200: inline_serializer('ResendVerificationResponse', fields={
            'status': drf_serializers.IntegerField(),
            'message': drf_serializers.CharField(),
        })},
        auth=[],
    )
    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email__iexact=email)
            if not user.email_verified:
                token_obj = EmailVerificationToken.create_for_user(user)
                send_verification_email(user, token_obj.token)
                logger.info('Verification email resent: user=%s', user.email)
        except User.DoesNotExist:
            pass  # Never disclose whether email exists

        return api_response('If that email exists and is unverified, a new link has been sent.')


# ---------------------------------------------------------------------------
# AUTH-008 — Password reset
# ---------------------------------------------------------------------------
@extend_schema(tags=['Auth'])
class PasswordResetRequestView(ExceptionMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Request password reset email',
        request=PasswordResetRequestSerializer,
        responses={200: inline_serializer('PasswordResetRequestResponse', fields={
            'status': drf_serializers.IntegerField(),
            'message': drf_serializers.CharField(),
        })},
        auth=[],
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(email__iexact=serializer.validated_data['email'])
            token_obj = PasswordResetToken.create_for_user(user)
            send_password_reset_email(user, token_obj.token)
            logger.info('Password reset email sent: %s', user.email)
        except User.DoesNotExist:
            pass  # Never disclose whether email exists

        return api_response('If that email exists, a reset link has been sent.')


@extend_schema(tags=['Auth'])
class PasswordResetCompleteView(ExceptionMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Complete password reset with token',
        request=PasswordResetCompleteSerializer,
        responses={200: inline_serializer('PasswordResetCompleteResponse', fields={
            'status': drf_serializers.IntegerField(),
            'message': drf_serializers.CharField(),
        })},
        auth=[],
    )
    def post(self, request):
        serializer = PasswordResetCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token_obj = PasswordResetToken.objects.select_related('user').get(
                token=serializer.validated_data['token']
            )
        except PasswordResetToken.DoesNotExist:
            return api_response('Invalid reset token.', status_code=status.HTTP_400_BAD_REQUEST)

        if not token_obj.is_valid:
            return api_response('Reset token has expired.', status_code=status.HTTP_400_BAD_REQUEST)

        user = token_obj.user
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        token_obj.consumed = True
        token_obj.save(update_fields=['consumed'])

        # Revoke all sessions
        for t in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=t)

        send_password_reset_confirmation_email(user)
        write_audit_log(user, 'password_reset_complete', request)
        logger.info('Password reset completed: user=%s — all sessions revoked', user.email)
        return api_response('Password updated successfully. Please log in again.')


# ---------------------------------------------------------------------------
# AUTH-009 — Get / update user profile
# ---------------------------------------------------------------------------
@extend_schema(tags=['Users'])
class UserProfileView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Get current user profile', responses={200: UserProfileSerializer})
    def get(self, request):
        return api_response('Profile retrieved.', data=UserProfileSerializer(request.user).data)

    @extend_schema(summary='Update current user profile', request=UserProfileSerializer, responses={200: UserProfileSerializer})
    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info('Profile updated: user=%s', request.user.email)
        return api_response('Profile updated.', data=serializer.data)


# ---------------------------------------------------------------------------
# AUTH-010 — Account deletion
# ---------------------------------------------------------------------------
@extend_schema(tags=['Users'])
class AccountDeleteView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Request account deletion (30-day grace period)',
        request=AccountDeleteSerializer,
        responses={200: inline_serializer('AccountDeleteResponse', fields={
            'status': drf_serializers.IntegerField(),
            'message': drf_serializers.CharField(),
        })},
    )
    def post(self, request):
        serializer = AccountDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        data = serializer.validated_data

        # Re-authentication: email users need password; OAuth users need their token
        if user.google_id:
            id_token = data.get('google_id_token', '')
            if not id_token:
                return api_response('Google re-authentication required. Provide google_id_token.', status_code=status.HTTP_400_BAD_REQUEST)
            claims = verify_google_token(id_token)
            if not claims or claims.get('sub') != user.google_id:
                return api_response('Google re-authentication failed.', status_code=status.HTTP_401_UNAUTHORIZED)

        elif user.apple_id:
            identity_token = data.get('apple_identity_token', '')
            if not identity_token:
                return api_response('Apple re-authentication required. Provide apple_identity_token.', status_code=status.HTTP_400_BAD_REQUEST)
            claims = verify_apple_token(identity_token)
            if not claims or claims.get('sub') != user.apple_id:
                return api_response('Apple re-authentication failed.', status_code=status.HTTP_401_UNAUTHORIZED)

        else:
            # Email/password account
            pw = data.get('password', '')
            if not pw or not user.check_password(pw):
                return api_response('Incorrect password.', status_code=status.HTTP_400_BAD_REQUEST)

        write_audit_log(user, 'account_delete_requested', request, {
            'reason': data.get('reason', '')
        })
        user.soft_delete()

        # Revoke all sessions
        for t in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=t)

        # Create cancel token and send email
        cancel_token_obj = DeleteCancelToken.create_for_user(user)
        send_account_deletion_email(user, cancel_token_obj.token)

        logger.warning('Account deletion requested: user=%s (id=%s)', user.email, user.id)
        return api_response('Account scheduled for deletion in 30 days. Check your email to cancel.')


@extend_schema(tags=['Users'])
class AccountDeleteCancelView(ExceptionMixin, APIView):
    """Cancel account deletion using the token sent by email (public endpoint)."""
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Cancel account deletion via email token',
        responses={200: inline_serializer('AccountDeleteCancelResponse', fields={
            'status': drf_serializers.IntegerField(),
            'message': drf_serializers.CharField(),
        })},
        auth=[],
    )
    def get(self, request, cancel_token):
        try:
            token_obj = DeleteCancelToken.objects.select_related('user').get(token=cancel_token)
        except DeleteCancelToken.DoesNotExist:
            return api_response('Invalid cancellation token.', status_code=status.HTTP_400_BAD_REQUEST)

        if not token_obj.is_valid:
            return api_response('Cancellation token has expired. Your account has been deleted.', status_code=status.HTTP_400_BAD_REQUEST)

        user = token_obj.user
        user.deleted_at = None
        user.is_active = True
        user.save(update_fields=['deleted_at', 'is_active'])
        token_obj.consumed = True
        token_obj.save(update_fields=['consumed'])

        write_audit_log(user, 'account_delete_cancelled', request)
        logger.info('Account deletion cancelled: user=%s', user.email)
        return api_response('Account deletion cancelled. Your account is active again.')


# ---------------------------------------------------------------------------
# AUTH-011 — Data export
# ---------------------------------------------------------------------------
@extend_schema(tags=['Users'])
class DataExportRequestView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Request data export (async)',
        request=None,
        responses={202: inline_serializer('DataExportRequestResponse', fields={
            'status': drf_serializers.IntegerField(),
            'message': drf_serializers.CharField(),
            'data': inline_serializer('DataExportRequestData', fields={
                'export_id': drf_serializers.UUIDField(),
                'status': drf_serializers.CharField(),
            }),
        })},
    )
    def post(self, request):
        export = DataExport.objects.create(user=request.user)
        export_user_data_task.delay(str(export.id))
        logger.info('Data export queued: user=%s export_id=%s', request.user.email, export.id)
        return api_response(
            'Export queued. Check status using the export_id.',
            data={'export_id': str(export.id), 'status': export.status},
            status_code=status.HTTP_202_ACCEPTED,
        )


@extend_schema(tags=['Users'])
class DataExportStatusView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get data export status and download URL',
        responses={200: inline_serializer('DataExportStatusResponse', fields={
            'status': drf_serializers.IntegerField(),
            'message': drf_serializers.CharField(),
            'data': inline_serializer('DataExportStatusData', fields={
                'export_id': drf_serializers.UUIDField(),
                'status': drf_serializers.CharField(),
                'download_url': drf_serializers.CharField(allow_null=True),
                'expires_at': drf_serializers.DateTimeField(allow_null=True),
            }),
        })},
    )
    def get(self, request, export_id):
        try:
            export = DataExport.objects.get(id=export_id, user=request.user)
        except DataExport.DoesNotExist:
            return api_response('Export not found.', status_code=status.HTTP_404_NOT_FOUND)

        return api_response(
            'Export status retrieved.',
            data={
                'export_id': str(export.id),
                'status': export.status,
                'download_url': export.download_url,
                'expires_at': export.expires_at.isoformat() if export.expires_at else None,
            },
        )


@extend_schema(tags=['Users'])
class DataExportDownloadView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Download exported user data as JSON',
        responses={200: inline_serializer('DataExportDownloadResponse', fields={
            'status': drf_serializers.IntegerField(),
            'message': drf_serializers.CharField(),
            'data': drf_serializers.DictField(),
        })},
    )
    def get(self, request, export_id):
        try:
            export = DataExport.objects.get(id=export_id, user=request.user)
        except DataExport.DoesNotExist:
            return api_response('Export not found.', status_code=status.HTTP_404_NOT_FOUND)

        if export.status != DataExport.Status.READY:
            return api_response(
                f'Export is not ready yet. Current status: {export.status}',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if export.expires_at and export.expires_at < timezone.now():
            return api_response('Export link has expired. Please request a new export.', status_code=status.HTTP_410_GONE)

        return api_response('Export data retrieved.', data=export.export_data or {})


_NOTIFICATION_CATEGORIES = [
    "habit_reminders",
    "streak_risk",
    "comeback",
    "weekly_review",
    "program_daily",
    "marketing",
]


@extend_schema(tags=['Users'])
class NotificationPreferencesView(ExceptionMixin, APIView):
    """NT-009 — GET / PUT /users/me/notification-preferences"""

    permission_classes = [IsAuthenticated]

    def _defaults(self):
        return {cat: True for cat in _NOTIFICATION_CATEGORIES}

    @extend_schema(
        summary='Get notification preferences (NT-009)',
        responses={200: inline_serializer('NotificationPreferencesResponse', fields={
            'status': drf_serializers.IntegerField(),
            'message': drf_serializers.CharField(),
            'data': drf_serializers.DictField(),
        })},
    )
    def get(self, request):
        prefs = {**self._defaults(), **(request.user.notification_preferences or {})}
        return api_response('Notification preferences retrieved.', data=prefs)

    @extend_schema(
        summary='Update notification preferences (NT-009)',
        responses={200: inline_serializer('NotificationPreferencesUpdateResponse', fields={
            'status': drf_serializers.IntegerField(),
            'message': drf_serializers.CharField(),
            'data': drf_serializers.DictField(),
        })},
    )
    def put(self, request):
        incoming = request.data
        if not isinstance(incoming, dict):
            return api_response('Request body must be a JSON object.', status_code=status.HTTP_400_BAD_REQUEST)

        current = {**self._defaults(), **(request.user.notification_preferences or {})}
        for key, val in incoming.items():
            if key not in _NOTIFICATION_CATEGORIES:
                return api_response(
                    f"Unknown preference key '{key}'. Valid keys: {', '.join(_NOTIFICATION_CATEGORIES)}.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if not isinstance(val, bool):
                return api_response(
                    f"Value for '{key}' must be a boolean.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            current[key] = val

        request.user.notification_preferences = current
        request.user.save(update_fields=['notification_preferences'])
        return api_response('Notification preferences updated.', data=current)

