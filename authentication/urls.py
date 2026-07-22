from django.urls import path
from authentication.views import *
urlpatterns = [
    # Auth
    path('auth/signup/', SignupEmailView.as_view(), name='auth-signup'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('auth/verify-email/', VerifyEmailView.as_view(), name='auth-verify-email'),
    path('auth/resend-verification/', ResendVerificationView.as_view(), name='auth-resend-verification'),
    path('auth/password-reset/request/', PasswordResetRequestView.as_view(), name='auth-password-reset-request'),
    path('auth/password-reset/complete/', PasswordResetCompleteView.as_view(), name='auth-password-reset-complete'),
    path('auth/social/apple/', AppleSignInView.as_view(), name='auth-apple'),
    path('auth/social/google/', GoogleSignInView.as_view(), name='auth-google'),
    path('auth/users/me/delete/cancel/<str:cancel_token>/', AccountDeleteCancelView.as_view(), name='users-delete-cancel'),

    # Users (authenticated)
    path('auth/users/me/', UserProfileView.as_view(), name='users-me'),
    path('auth/users/me/delete/', AccountDeleteView.as_view(), name='users-delete'),
    path('auth/users/me/export/', DataExportRequestView.as_view(), name='users-export'),
    path('auth/users/me/export/<uuid:export_id>/', DataExportStatusView.as_view(), name='users-export-status'),
    path('auth/users/me/export/<uuid:export_id>/download/', DataExportDownloadView.as_view(), name='users-export-download'),
    path('auth/users/me/notification-preferences/', NotificationPreferencesView.as_view(), name='users-notification-preferences'),
]
