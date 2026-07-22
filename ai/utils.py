"""Utility helpers for the ai app."""

import datetime
import json
import logging
import re

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Groq client (merged from groq_client.py)
# ---------------------------------------------------------------------------

def get_groq_client():
    from groq import Groq
    return Groq(api_key=settings.GROQ_API_KEY)


def call_groq(
    system_prompt: str,
    user_prompt: str,
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.7,
) -> str:
    """Call Groq API. Returns raw string content."""
    try:
        client = get_groq_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=2048,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        raise


def parse_json_response(raw: str) -> "dict | list":
    """Extract JSON from LLM response (handles markdown code blocks)."""
    # Strip markdown code blocks
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Prompts (merged from prompts.py)
# ---------------------------------------------------------------------------

PROMPT_VERSION = "v1"

SYSTEM_HABIT_GENERATOR = """You are a professional habit coach. Generate personalized habit suggestions based on the user's profile.
Always respond with valid JSON only. No explanation outside the JSON.
Safety rules:
- Never suggest medication dosages or medical treatments
- For exercise habits, cap at reasonable targets (e.g., max 25000 steps, max 2hr workout)
- If user has pregnancy/disability/chronic_illness flags, avoid intense physical habits
- Always include a helpful rationale
"""


def build_habit_generation_prompt(profile_answers: dict, mode: str, health_flags: list) -> str:
    count = "5 to 7" if mode == "starter" else "30 to 40"
    return f"""
User profile answers: {json.dumps(profile_answers)}
Health flags: {health_flags}
Mode: {mode}

Generate {count} habit suggestions. Return JSON array:
[
  {{
    "title": "string (max 80 chars)",
    "description": "string",
    "category": "Health|Fitness|Mindfulness|Productivity|Learning|Finance|Relationships|Other",
    "frequency_type": "daily|weekdays|n_per_week",
    "quantity_target": null or number,
    "duration_minutes": null or number,
    "difficulty": "tiny|small|medium",
    "rationale": "1-2 sentence explanation why this suits the user"
  }}
]
"""


def build_nl_modification_prompt(habit: dict, instruction: str) -> str:
    return f"""
Current habit: {json.dumps(habit)}
User instruction: "{instruction}"

Propose changes to this habit based on the instruction. Return JSON:
{{
  "proposed_changes": {{ ...only changed fields... }},
  "explanation": "Brief explanation of changes"
}}
Valid fields to change: title, description, frequency_type, frequency_days, frequency_count, quantity_target, duration_minutes, time_window_start, time_window_end, difficulty, reminder_times
"""


def build_coaching_review_prompt(habits_summary: list, completion_stats: dict) -> str:
    return f"""
User's habits: {json.dumps(habits_summary)}
Completion stats (last 14 days): {json.dumps(completion_stats)}

Analyze and propose adjustments. Return JSON array of proposals:
[
  {{
    "proposal_id": "generate a uuid string",
    "habit_id": "uuid or null for new",
    "proposal_type": "drop|scale_up|scale_down|restack|add_stack|add_new",
    "explanation": "Why this change is recommended",
    "proposed_changes": {{ ...fields... }}
  }}
]
"""


# ---------------------------------------------------------------------------
# Safety (merged from safety.py)
# ---------------------------------------------------------------------------

DISALLOWED_KEYWORDS = [
    "medication",
    "prescription",
    "dosage",
    "mg ",
    "insulin",
    "chemotherapy",
    "surgery",
    "extreme fast",
    "starvation",
]

UNSAFE_TARGETS = {
    "steps": 25000,
    "calories_burned": 3000,
    "minutes_exercise": 180,
}


def filter_suggestions(suggestions: list, health_flags: list) -> list:
    """Filter/hedge unsafe suggestions."""
    safe = []
    for s in suggestions:
        title_lower = s.get("title", "").lower()
        desc_lower = s.get("description", "").lower()
        text = title_lower + " " + desc_lower

        # Block disallowed content
        if any(kw in text for kw in DISALLOWED_KEYWORDS):
            continue

        # Skip intense physical for sensitive health flags
        if health_flags and any(
            f in health_flags for f in ["pregnancy", "disability", "chronic_illness"]
        ):
            if s.get("category") == "Fitness" and s.get("difficulty") == "medium":
                s["difficulty"] = "tiny"
                s["rationale"] = s.get("rationale", "") + " (adjusted for your health profile)"

        safe.append(s)
    return safe


# ---------------------------------------------------------------------------
# Rate limiting (merged from rate_limit.py)
# ---------------------------------------------------------------------------

def check_ai_rate_limit(user_id: str, action: str, limit: int) -> bool:
    """Returns True if under limit. Increments counter."""
    key = f"ai_rate:{action}:{user_id}:{datetime.date.today()}"
    count = cache.get(key, 0)
    if count >= limit:
        return False
    cache.set(key, count + 1, timeout=86400)
    return True


# ---------------------------------------------------------------------------
# Seed data (merged from seed_data.py)
# ---------------------------------------------------------------------------

DEFAULT_QUESTIONS = [
    {
        "id": "q_identity",
        "question_type": "multi_select",
        "prompt": "Which of these best describe you? (pick up to 3)",
        "options": [
            "Fitness enthusiast",
            "Busy professional",
            "Student",
            "Parent",
            "Creative",
            "Night owl",
            "Early bird",
        ],
        "max_selections": 3,
        "order": 1,
        "is_progressive": False,
    },
    {
        "id": "q_goals",
        "question_type": "multi_select",
        "prompt": "What are your main goals?",
        "options": [
            "Improve health",
            "Build fitness",
            "Reduce stress",
            "Learn new skills",
            "Save money",
            "Better sleep",
            "More focus",
        ],
        "max_selections": 3,
        "order": 2,
        "is_progressive": False,
    },
    {
        "id": "q_time",
        "question_type": "single_select",
        "prompt": "How much time can you dedicate to new habits daily?",
        "options": [
            "< 5 minutes",
            "5\u201315 minutes",
            "15\u201330 minutes",
            "30\u201360 minutes",
            "> 1 hour",
        ],
        "max_selections": 1,
        "order": 3,
        "is_progressive": False,
    },
    {
        "id": "q_constraints",
        "question_type": "multi_select",
        "prompt": "Any constraints we should know about?",
        "options": [
            "Pregnancy",
            "Physical disability",
            "Chronic illness",
            "Shift work",
            "None",
        ],
        "max_selections": 5,
        "order": 4,
        "is_progressive": False,
    },
    {
        "id": "q_experience",
        "question_type": "scale",
        "prompt": "How experienced are you with habit tracking? (1 = beginner, 5 = expert)",
        "options": ["1", "2", "3", "4", "5"],
        "max_selections": 1,
        "order": 5,
        "is_progressive": False,
    },
]
