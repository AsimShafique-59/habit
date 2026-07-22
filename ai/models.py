import uuid
from django.db import models
from django.conf import settings


class OnboardingQuestion(models.Model):
    """Static onboarding questions — seeded once, not user-specific."""

    QUESTION_TYPE_CHOICES = [
        ("single_select", "Single Select"),
        ("multi_select", "Multi Select"),
        ("scale", "Scale"),
        ("free_text", "Free Text"),
    ]

    id = models.CharField(max_length=40, primary_key=True)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
    prompt = models.TextField()
    options = models.JSONField(default=list)
    max_selections = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    is_progressive = models.BooleanField(default=False)

    class Meta:
        db_table = "onboarding_questions"
        ordering = ["order"]

    def __str__(self):
        return f"{self.id}: {self.prompt[:60]}"


class UserAIProfile(models.Model):
    """One AI profile per user — stores onboarding answers and archetype data."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_profile",
    )
    answers = models.JSONField(default=dict)
    archetype_hash = models.CharField(max_length=64, blank=True)
    onboarding_completed = models.BooleanField(default=False)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    health_flags = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_ai_profiles"

    def __str__(self):
        return f"AIProfile({self.user_id})"


class HabitSuggestion(models.Model):
    """LLM-generated habit suggestion for a specific user."""

    DIFFICULTY_CHOICES = [
        ("tiny", "Tiny"),
        ("small", "Small"),
        ("medium", "Medium"),
    ]
    MODE_CHOICES = [
        ("starter", "Starter"),
        ("expanded", "Expanded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habit_suggestions",
    )
    suggestion_id = models.UUIDField(default=uuid.uuid4)
    title = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=40)
    frequency_type = models.CharField(max_length=20, default="daily")
    quantity_target = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default="tiny")
    rationale = models.TextField(blank=True)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="starter")
    archetype_hash = models.CharField(max_length=64, blank=True)
    is_accepted = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    created_habit_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "habit_suggestions"

    def __str__(self):
        return f"{self.title} ({self.user_id})"


class AIArchetypeCache(models.Model):
    """Cached LLM responses keyed by archetype hash to avoid redundant API calls."""

    MODE_CHOICES = [
        ("starter", "Starter"),
        ("expanded", "Expanded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    archetype_hash = models.CharField(max_length=80, unique=True)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    suggestions_json = models.JSONField()
    prompt_version = models.CharField(max_length=10, default="v1")
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_archetype_cache"

    def __str__(self):
        return f"Cache({self.archetype_hash[:16]}…, {self.mode})"


class CoachingReview(models.Model):
    """AI-generated coaching review with habit adjustment proposals."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("responded", "Responded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="coaching_reviews",
    )
    proposals = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "coaching_reviews"
        ordering = ["-created_at"]

    def __str__(self):
        return f"CoachingReview({self.user_id}, {self.status})"


class NLModification(models.Model):
    """Log of natural-language habit modification requests."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="nl_modifications",
    )
    habit_id = models.UUIDField()
    instruction = models.TextField()
    proposed_changes = models.JSONField(default=dict)
    explanation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "nl_modifications"

    def __str__(self):
        return f"NLMod({self.user_id}, habit={self.habit_id})"

 