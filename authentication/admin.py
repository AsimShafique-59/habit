from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditLog, DataExport, EmailVerificationToken, PasswordResetToken, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "name", "subscription_tier", "email_verified", "is_staff", "date_joined")
    list_filter = ("subscription_tier", "email_verified", "is_staff", "is_active")
    search_fields = ("email", "name", "username")
    ordering = ("-date_joined",)
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Profile", {"fields": ("name", "locale", "timezone", "identity_tags", "theme_preference")}),
        ("Status", {"fields": ("email_verified", "subscription_tier", "deleted_at", "locked_until")}),
        ("Social", {"fields": ("apple_id", "google_id")}),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "ip_address", "created_at")
    list_filter = ("action",)
    readonly_fields = ("user", "action", "ip_address", "user_agent", "metadata", "created_at")


admin.site.register(EmailVerificationToken)
admin.site.register(PasswordResetToken)
admin.site.register(DataExport)
