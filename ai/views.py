import hashlib
import json
import logging
import uuid

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from utils.response import ExceptionMixin, api_response
from .utils import call_groq, parse_json_response
from .models import *
from .utils import (
    PROMPT_VERSION,
    SYSTEM_HABIT_GENERATOR,
    build_coaching_review_prompt,
    build_habit_generation_prompt,
    build_nl_modification_prompt,
)
from .utils import check_ai_rate_limit
from .utils import filter_suggestions
from .utils import DEFAULT_QUESTIONS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fallback habits used when Groq is unavailable
# ---------------------------------------------------------------------------
DEFAULT_STARTER_HABITS = [
    {
        "title": "Drink 8 glasses of water",
        "description": "Stay hydrated throughout the day",
        "category": "Health",
        "frequency_type": "daily",
        "quantity_target": 8,
        "duration_minutes": None,
        "difficulty": "tiny",
        "rationale": "Hydration is the foundation of good health.",
    },
    {
        "title": "10-minute morning walk",
        "description": "Start your day with movement",
        "category": "Fitness",
        "frequency_type": "daily",
        "quantity_target": None,
        "duration_minutes": 10,
        "difficulty": "tiny",
        "rationale": "A short walk boosts energy and mood for the day.",
    },
    {
        "title": "5-minute meditation",
        "description": "Calm your mind before the day starts",
        "category": "Mindfulness",
        "frequency_type": "daily",
        "quantity_target": None,
        "duration_minutes": 5,
        "difficulty": "tiny",
        "rationale": "Even 5 minutes of mindfulness reduces stress significantly.",
    },
    {
        "title": "Read for 15 minutes",
        "description": "Build a reading habit",
        "category": "Learning",
        "frequency_type": "daily",
        "quantity_target": None,
        "duration_minutes": 15,
        "difficulty": "small",
        "rationale": "Consistent reading compounds into significant knowledge over time.",
    },
    {
        "title": "Write 3 things you're grateful for",
        "description": "End your day with gratitude",
        "category": "Mindfulness",
        "frequency_type": "daily",
        "quantity_target": 3,
        "duration_minutes": 5,
        "difficulty": "tiny",
        "rationale": "Gratitude journaling improves sleep quality and wellbeing.",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_archetype_hash(answers: dict) -> str:
    """SHA-256 of the canonically sorted JSON of answers."""
    canonical = json.dumps(answers, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _get_or_create_profile(user) -> UserAIProfile:
    profile, _ = UserAIProfile.objects.get_or_create(user=user)
    return profile


def _serialize_suggestion(s: HabitSuggestion) -> dict:
    return {
        "suggestion_id": str(s.id),
        "title": s.title,
        "description": s.description,
        "category": s.category,
        "frequency_type": s.frequency_type,
        "quantity_target": float(s.quantity_target) if s.quantity_target is not None else None,
        "duration_minutes": s.duration_minutes,
        "difficulty": s.difficulty,
        "rationale": s.rationale,
        "mode": s.mode,
        "is_accepted": s.is_accepted,
        "is_dismissed": s.is_dismissed,
        "created_at": s.created_at.isoformat(),
    }


def _save_suggestions(user, raw_suggestions: list, mode: str, archetype_hash: str) -> list:
    """Persist a list of raw suggestion dicts as HabitSuggestion rows and return them."""
    objs = []
    for s in raw_suggestions:
        obj = HabitSuggestion.objects.create(
            user=user,
            title=s.get("title", "")[:80],
            description=s.get("description", ""),
            category=s.get("category", "Other"),
            frequency_type=s.get("frequency_type", "daily"),
            quantity_target=s.get("quantity_target"),
            duration_minutes=s.get("duration_minutes"),
            difficulty=s.get("difficulty", "tiny"),
            rationale=s.get("rationale", ""),
            mode=mode,
            archetype_hash=archetype_hash,
        )
        objs.append(obj)
    return objs


# ---------------------------------------------------------------------------
# AI-001a — GET /ai/onboarding/questions/
# ---------------------------------------------------------------------------

@extend_schema(tags=["AI"])
class OnboardingQuestionsView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="ai_onboarding_questions_get",
        summary="Get onboarding questions",
        responses={
            200: inline_serializer(
                "OnboardingQuestionsResponse",
                fields={
                    "status": drf_serializers.IntegerField(),
                    "message": drf_serializers.CharField(),
                    "data": inline_serializer(
                        "OnboardingQuestionsData",
                        fields={
                            "questions": drf_serializers.ListField(),
                            "onboarding_completed": drf_serializers.BooleanField(),
                        },
                    ),
                },
            )
        },
    )
    def get(self, request):
        profile = _get_or_create_profile(request.user)

        qs = OnboardingQuestion.objects.all()
        if not qs.exists():
            # Fall back to seed data constants if DB is empty
            questions = DEFAULT_QUESTIONS
        else:
            questions = list(
                qs.values(
                    "id", "question_type", "prompt", "options",
                    "max_selections", "order", "is_progressive",
                )
            )

        if profile.onboarding_completed:
            # Return only progressive questions (shown after day 0)
            if isinstance(questions[0], dict) and "is_progressive" in questions[0]:
                questions = [q for q in questions if q.get("is_progressive")]
            else:
                questions = []

        return api_response(
            "Onboarding questions retrieved.",
            data={
                "questions": questions,
                "onboarding_completed": profile.onboarding_completed,
            },
        )


# ---------------------------------------------------------------------------
# AI-001b — POST /ai/onboarding/answers/
# ---------------------------------------------------------------------------

@extend_schema(tags=["AI"])
class OnboardingAnswersView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="ai_onboarding_answers_post",
        summary="Submit onboarding answers",
        request=inline_serializer(
            "OnboardingAnswersRequest",
            fields={"answers": drf_serializers.DictField()},
        ),
        responses={
            200: inline_serializer(
                "OnboardingAnswersResponse",
                fields={
                    "status": drf_serializers.IntegerField(),
                    "message": drf_serializers.CharField(),
                    "data": inline_serializer(
                        "OnboardingAnswersData",
                        fields={
                            "onboarding_completed": drf_serializers.BooleanField(),
                            "archetype_hash": drf_serializers.CharField(),
                        },
                    ),
                },
            )
        },
    )
    def post(self, request):
        answers = request.data.get("answers")
        if not isinstance(answers, dict):
            return api_response(
                "Field 'answers' must be a dict.", status_code=status.HTTP_400_BAD_REQUEST
            )

        profile = _get_or_create_profile(request.user)

        # Merge (not replace) with existing answers
        merged = {**profile.answers, **answers}
        profile.answers = merged

        # Detect health flags from q_constraints
        constraint_answer = merged.get("q_constraints", [])
        if isinstance(constraint_answer, list):
            flag_map = {
                "Pregnancy": "pregnancy",
                "Physical disability": "disability",
                "Chronic illness": "chronic_illness",
            }
            profile.health_flags = [
                flag_map[c] for c in constraint_answer if c in flag_map
            ]

        # Compute archetype hash
        profile.archetype_hash = _compute_archetype_hash(merged)

        # Determine completion: all non-progressive questions answered
        non_prog_ids = set(
            OnboardingQuestion.objects.filter(is_progressive=False).values_list("id", flat=True)
        )
        if not non_prog_ids:
            # Fall back to seed data ids
            non_prog_ids = {q["id"] for q in DEFAULT_QUESTIONS if not q["is_progressive"]}

        if non_prog_ids and non_prog_ids.issubset(set(merged.keys())):
            if not profile.onboarding_completed:
                profile.onboarding_completed = True
                profile.onboarding_completed_at = timezone.now()

        profile.save()

        return api_response(
            "Answers saved.",
            data={
                "onboarding_completed": profile.onboarding_completed,
                "archetype_hash": profile.archetype_hash,
            },
        )


# ---------------------------------------------------------------------------
# AI-002 — POST /ai/habits/generate/
# ---------------------------------------------------------------------------

@extend_schema(tags=["AI"])
class GenerateHabitsView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="ai_habits_generate",
        summary="Generate AI habit suggestions",
        request=inline_serializer(
            "GenerateHabitsRequest",
            fields={
                "mode": drf_serializers.ChoiceField(choices=["starter", "expanded"]),
            },
        ),
        responses={
            200: inline_serializer(
                "GenerateHabitsResponse",
                fields={
                    "status": drf_serializers.IntegerField(),
                    "message": drf_serializers.CharField(),
                    "data": inline_serializer(
                        "GenerateHabitsData",
                        fields={
                            "suggestions": drf_serializers.ListField(),
                            "mode": drf_serializers.CharField(),
                            "from_cache": drf_serializers.BooleanField(),
                        },
                    ),
                },
            )
        },
    )
    def post(self, request):
        # Rate limit: 10 per day
        if not check_ai_rate_limit(str(request.user.id), "generate_habits", 10):
            return api_response(
                "Rate limit exceeded. You can generate habits up to 10 times per day.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        mode = request.data.get("mode", "starter")
        if mode not in ("starter", "expanded"):
            return api_response(
                "mode must be 'starter' or 'expanded'.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        profile = _get_or_create_profile(request.user)

        if not profile.onboarding_completed:
            return api_response(
                "Complete onboarding first.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        archetype_hash = _compute_archetype_hash(profile.answers)
        profile.archetype_hash = archetype_hash
        profile.save(update_fields=["archetype_hash"])

        # Check cache
        from_cache = False
        cache_key = f"{archetype_hash}:{mode}"
        cached = (
            AIArchetypeCache.objects.filter(
                archetype_hash=cache_key,
                mode=mode,
                expires_at__gt=timezone.now(),
                prompt_version=PROMPT_VERSION,
            )
            .first()
        )

        if cached:
            raw_suggestions = cached.suggestions_json
            from_cache = True
        else:
            # Call Groq (or fallback)
            groq_available = bool(getattr(settings, "GROQ_API_KEY", ""))
            if groq_available:
                try:
                    system = SYSTEM_HABIT_GENERATOR
                    user_prompt = build_habit_generation_prompt(
                        profile.answers, mode, profile.health_flags
                    )
                    raw = call_groq(system, user_prompt)
                    raw_suggestions = parse_json_response(raw)
                    if not isinstance(raw_suggestions, list):
                        raise ValueError("LLM did not return a list")
                except Exception as exc:
                    logger.warning("Groq failed, using fallback: %s", exc)
                    raw_suggestions = DEFAULT_STARTER_HABITS
            else:
                logger.info("GROQ_API_KEY not set — using fallback habits")
                raw_suggestions = DEFAULT_STARTER_HABITS

            # Apply safety filters
            raw_suggestions = filter_suggestions(raw_suggestions, profile.health_flags)

            # Cache for 30 days
            AIArchetypeCache.objects.update_or_create(
                archetype_hash=cache_key,
                defaults={
                    "mode": mode,
                    "suggestions_json": raw_suggestions,
                    "prompt_version": PROMPT_VERSION,
                    "expires_at": timezone.now() + timezone.timedelta(days=30),
                },
            )

        # Persist suggestions for this user
        suggestion_objs = _save_suggestions(
            request.user, raw_suggestions, mode, archetype_hash
        )

        return api_response(
            "Habit suggestions generated.",
            data={
                "suggestions": [_serialize_suggestion(s) for s in suggestion_objs],
                "mode": mode,
                "from_cache": from_cache,
            },
        )


# ---------------------------------------------------------------------------
# AI-003 — POST /ai/habits/accept/
# ---------------------------------------------------------------------------

@extend_schema(tags=["AI"])
class AcceptSuggestionsView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="ai_habits_accept",
        summary="Accept (and optionally modify) habit suggestions",
        request=inline_serializer(
            "AcceptSuggestionsRequest",
            fields={
                "suggestion_ids": drf_serializers.ListField(
                    child=drf_serializers.UUIDField()
                ),
                "modifications": drf_serializers.DictField(required=False),
            },
        ),
        responses={
            200: inline_serializer(
                "AcceptSuggestionsResponse",
                fields={
                    "status": drf_serializers.IntegerField(),
                    "message": drf_serializers.CharField(),
                    "data": inline_serializer(
                        "AcceptSuggestionsData",
                        fields={"created_habits": drf_serializers.ListField()},
                    ),
                },
            )
        },
    )
    def post(self, request):
        suggestion_ids = request.data.get("suggestion_ids", [])
        modifications = request.data.get("modifications", {})

        if not suggestion_ids:
            return api_response(
                "suggestion_ids is required.", status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            from habits.models import Habit
        except ImportError:
            return api_response(
                "Habits service is not yet available.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        created_habits = []
        for sid in suggestion_ids:
            try:
                suggestion = HabitSuggestion.objects.get(
                    id=sid, user=request.user, is_accepted=False
                )
            except HabitSuggestion.DoesNotExist:
                continue

            # Apply any caller-supplied field overrides
            overrides = modifications.get(str(sid), {})

            # Build habit creation kwargs from suggestion
            habit_kwargs = dict(
                user=request.user,
                title=overrides.get("title", suggestion.title),
                description=overrides.get("description", suggestion.description),
                category=overrides.get("category", suggestion.category),
                frequency_type=overrides.get("frequency_type", suggestion.frequency_type),
                difficulty=overrides.get("difficulty", suggestion.difficulty),
            )
            if suggestion.quantity_target is not None:
                habit_kwargs["quantity_target"] = overrides.get(
                    "quantity_target", suggestion.quantity_target
                )
            if suggestion.duration_minutes is not None:
                habit_kwargs["duration_minutes"] = overrides.get(
                    "duration_minutes", suggestion.duration_minutes
                )

            # Only set fields that Habit actually has
            valid_fields = {f.name for f in Habit._meta.get_fields()}
            filtered_kwargs = {k: v for k, v in habit_kwargs.items() if k in valid_fields}
            filtered_kwargs["user"] = request.user

            habit = Habit.objects.create(**filtered_kwargs)

            suggestion.is_accepted = True
            suggestion.created_habit_id = habit.id
            suggestion.save(update_fields=["is_accepted", "created_habit_id"])

            created_habits.append(
                {"habit_id": str(habit.id), "suggestion_id": str(suggestion.id)}
            )

        return api_response(
            f"{len(created_habits)} habit(s) created.",
            data={"created_habits": created_habits},
        )


# ---------------------------------------------------------------------------
# AI-004 — POST /habits/<uuid:habit_id>/modify-nl/
# ---------------------------------------------------------------------------

@extend_schema(tags=["AI"])
class NLModificationView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="ai_habits_modify_nl",
        summary="Propose natural-language habit modification",
        request=inline_serializer(
            "NLModificationRequest",
            fields={"instruction": drf_serializers.CharField()},
        ),
        responses={
            200: inline_serializer(
                "NLModificationResponse",
                fields={
                    "status": drf_serializers.IntegerField(),
                    "message": drf_serializers.CharField(),
                    "data": inline_serializer(
                        "NLModificationData",
                        fields={
                            "proposed_changes": drf_serializers.DictField(),
                            "explanation": drf_serializers.CharField(),
                            "modification_id": drf_serializers.UUIDField(),
                        },
                    ),
                },
            )
        },
    )
    def post(self, request, habit_id):
        # Rate limit: 5 per day
        if not check_ai_rate_limit(str(request.user.id), "nl_modification", 5):
            return api_response(
                "Rate limit exceeded. You can request NL modifications up to 5 times per day.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        instruction = request.data.get("instruction", "").strip()
        if not instruction:
            return api_response(
                "instruction is required.", status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            from habits.models import Habit
        except ImportError:
            return api_response(
                "Habits service is not yet available.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            habit = Habit.objects.get(id=habit_id, user=request.user)
        except Habit.DoesNotExist:
            return api_response("Habit not found.", status_code=status.HTTP_404_NOT_FOUND)

        # Build a plain dict of habit data to pass to the prompt
        habit_dict = {}
        for field in habit._meta.get_fields():
            if hasattr(field, "attname"):
                val = getattr(habit, field.attname, None)
                habit_dict[field.name] = str(val) if val is not None else None

        groq_available = bool(getattr(settings, "GROQ_API_KEY", ""))
        proposed_changes = {}
        explanation = "No AI service configured — no changes proposed."

        if groq_available:
            try:
                from .utils import SYSTEM_HABIT_GENERATOR
                system = "You are a habit coach assistant. Propose specific changes to habits based on user instructions. Respond with valid JSON only."
                user_prompt = build_nl_modification_prompt(habit_dict, instruction)
                raw = call_groq(system, user_prompt)
                parsed = parse_json_response(raw)
                if isinstance(parsed, dict):
                    proposed_changes = parsed.get("proposed_changes", {})
                    explanation = parsed.get("explanation", "")
            except Exception as exc:
                logger.warning("Groq NL modification failed: %s", exc)
                explanation = "AI service temporarily unavailable."

        # Log the modification request
        nl_mod = NLModification.objects.create(
            user=request.user,
            habit_id=habit_id,
            instruction=instruction,
            proposed_changes=proposed_changes,
            explanation=explanation,
        )

        return api_response(
            "Proposed changes ready. Call PATCH /habits/<id>/ to apply them.",
            data={
                "proposed_changes": proposed_changes,
                "explanation": explanation,
                "modification_id": str(nl_mod.id),
            },
        )


# ---------------------------------------------------------------------------
# AI-005a — GET /ai/coaching/reviews/latest/
# ---------------------------------------------------------------------------

@extend_schema(tags=["AI"])
class CoachingReviewLatestView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="ai_coaching_reviews_latest",
        summary="Get latest coaching review",
        responses={
            200: inline_serializer(
                "CoachingReviewLatestResponse",
                fields={
                    "status": drf_serializers.IntegerField(),
                    "message": drf_serializers.CharField(),
                    "data": inline_serializer(
                        "CoachingReviewLatestData",
                        fields={
                            "review_id": drf_serializers.UUIDField(),
                            "proposals": drf_serializers.ListField(),
                            "status": drf_serializers.CharField(),
                            "created_at": drf_serializers.DateTimeField(),
                            "responded_at": drf_serializers.DateTimeField(allow_null=True),
                        },
                    ),
                },
            )
        },
    )
    def get(self, request):
        review = (
            CoachingReview.objects.filter(user=request.user).order_by("-created_at").first()
        )
        if not review:
            return api_response("No coaching review found.", status_code=status.HTTP_404_NOT_FOUND)

        return api_response(
            "Latest coaching review retrieved.",
            data={
                "review_id": str(review.id),
                "proposals": review.proposals,
                "status": review.status,
                "created_at": review.created_at.isoformat(),
                "responded_at": review.responded_at.isoformat() if review.responded_at else None,
            },
        )


# ---------------------------------------------------------------------------
# AI-005b — POST /ai/coaching/reviews/trigger/
# ---------------------------------------------------------------------------

@extend_schema(tags=["AI"])
class CoachingReviewTriggerView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="ai_coaching_reviews_trigger",
        summary="Trigger an on-demand coaching review",
        request=inline_serializer("CoachingReviewTriggerRequest", fields={}),
        responses={
            200: inline_serializer(
                "CoachingReviewTriggerResponse",
                fields={
                    "status": drf_serializers.IntegerField(),
                    "message": drf_serializers.CharField(),
                    "data": inline_serializer(
                        "CoachingReviewTriggerData",
                        fields={
                            "review_id": drf_serializers.UUIDField(),
                            "proposals": drf_serializers.ListField(),
                        },
                    ),
                },
            )
        },
    )
    def post(self, request):
        # Collect habits and stats
        habits_summary = []
        completion_stats: dict = {}

        try:
            from habits.models import Habit
            user_habits = Habit.objects.filter(user=request.user)
            for h in user_habits:
                habits_summary.append(
                    {
                        "habit_id": str(h.id),
                        "title": h.title,
                        "frequency_type": getattr(h, "frequency_type", "daily"),
                        "difficulty": getattr(h, "difficulty", "tiny"),
                        "category": getattr(h, "category", "Other"),
                    }
                )
        except ImportError:
            pass

        groq_available = bool(getattr(settings, "GROQ_API_KEY", ""))
        proposals = []

        if groq_available and habits_summary:
            try:
                system = "You are a habit coach. Analyze the user's habits and completion data, then propose evidence-based adjustments. Respond with valid JSON only."
                user_prompt = build_coaching_review_prompt(habits_summary, completion_stats)
                raw = call_groq(system, user_prompt)
                parsed = parse_json_response(raw)
                if isinstance(parsed, list):
                    proposals = parsed
                elif isinstance(parsed, dict) and "proposals" in parsed:
                    proposals = parsed["proposals"]
            except Exception as exc:
                logger.warning("Groq coaching review failed: %s", exc)

        review = CoachingReview.objects.create(
            user=request.user,
            proposals=proposals,
        )

        return api_response(
            "Coaching review generated.",
            data={
                "review_id": str(review.id),
                "proposals": proposals,
            },
        )


# ---------------------------------------------------------------------------
# AI-005c — POST /ai/coaching/reviews/<uuid:review_id>/respond/
# ---------------------------------------------------------------------------

@extend_schema(tags=["AI"])
class CoachingReviewRespondView(ExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="ai_coaching_reviews_respond",
        summary="Respond to coaching review proposals",
        request=inline_serializer(
            "CoachingReviewRespondRequest",
            fields={
                "decisions": drf_serializers.ListField(
                    child=inline_serializer(
                        "CoachingDecision",
                        fields={
                            "proposal_id": drf_serializers.CharField(),
                            "action": drf_serializers.ChoiceField(
                                choices=["accept", "modify", "dismiss"]
                            ),
                            "modification": drf_serializers.DictField(required=False),
                        },
                    )
                )
            },
        ),
        responses={
            200: inline_serializer(
                "CoachingReviewRespondResponse",
                fields={
                    "status": drf_serializers.IntegerField(),
                    "message": drf_serializers.CharField(),
                    "data": inline_serializer(
                        "CoachingReviewRespondData",
                        fields={
                            "applied": drf_serializers.ListField(),
                            "skipped": drf_serializers.ListField(),
                        },
                    ),
                },
            )
        },
    )
    def post(self, request, review_id):
        try:
            review = CoachingReview.objects.get(id=review_id, user=request.user)
        except CoachingReview.DoesNotExist:
            return api_response(
                "Coaching review not found.", status_code=status.HTTP_404_NOT_FOUND
            )

        if review.status == "responded":
            return api_response(
                "This review has already been responded to.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        decisions = request.data.get("decisions", [])
        applied = []
        skipped = []

        # Build a map of proposals by proposal_id
        proposal_map = {str(p.get("proposal_id")): p for p in review.proposals}

        for decision in decisions:
            proposal_id = str(decision.get("proposal_id", ""))
            action = decision.get("action", "dismiss")
            modification = decision.get("modification", {})

            proposal = proposal_map.get(proposal_id)
            if not proposal:
                skipped.append({"proposal_id": proposal_id, "reason": "proposal not found"})
                continue

            if action == "dismiss":
                skipped.append({"proposal_id": proposal_id, "reason": "dismissed by user"})
                continue

            proposal_type = proposal.get("proposal_type", "")
            habit_id = proposal.get("habit_id")
            proposed_changes = {**proposal.get("proposed_changes", {}), **modification}

            try:
                from habits.models import Habit
            except ImportError:
                skipped.append({"proposal_id": proposal_id, "reason": "habits service unavailable"})
                continue

            try:
                if proposal_type == "add_new" or not habit_id:
                    # Create a new habit from proposed changes
                    valid_fields = {f.name for f in Habit._meta.get_fields()}
                    new_kwargs = {
                        k: v for k, v in proposed_changes.items() if k in valid_fields
                    }
                    new_kwargs["user"] = request.user
                    if "title" not in new_kwargs:
                        new_kwargs["title"] = proposal.get("explanation", "New habit")[:80]
                    habit = Habit.objects.create(**new_kwargs)
                    applied.append(
                        {"proposal_id": proposal_id, "action": action, "habit_id": str(habit.id)}
                    )

                elif proposal_type == "drop":
                    Habit.objects.filter(id=habit_id, user=request.user).delete()
                    applied.append(
                        {"proposal_id": proposal_id, "action": action, "habit_id": habit_id}
                    )

                else:
                    # scale_up, scale_down, restack, add_stack — update existing habit
                    valid_fields = {f.name for f in Habit._meta.get_fields()}
                    update_kwargs = {
                        k: v for k, v in proposed_changes.items() if k in valid_fields
                    }
                    if update_kwargs:
                        Habit.objects.filter(id=habit_id, user=request.user).update(**update_kwargs)
                    applied.append(
                        {"proposal_id": proposal_id, "action": action, "habit_id": habit_id}
                    )

            except Exception as exc:
                logger.warning("Failed to apply proposal %s: %s", proposal_id, exc)
                skipped.append({"proposal_id": proposal_id, "reason": str(exc)})

        # Mark review as responded
        review.status = "responded"
        review.responded_at = timezone.now()
        review.save(update_fields=["status", "responded_at"])

        return api_response(
            "Review response recorded.",
            data={"applied": applied, "skipped": skipped},
        )

