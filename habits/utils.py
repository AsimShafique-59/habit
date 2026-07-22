"""
Streak calculation engine for the habits app.

Entry point: recalculate_streak(habit, user) -> dict
"""
import logging
import zoneinfo
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# Maximum number of days / periods to walk back when computing streaks.
# Prevents runaway loops on habits with no completions.
MAX_LOOKBACK_DAYS = 500
MAX_LOOKBACK_WEEKS = 75  # ~1.5 years


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def recalculate_streak(habit, user) -> dict:
    """
    Recalculate current_streak, longest_streak and streak_freezes_available
    for *habit*, persisting the results back to the database.

    Returns:
        {
            "current_streak": int,
            "longest_streak": int,
            "streak_freeze_used": bool,  # True if a freeze was consumed this call
        }
    """
    from .models import HabitCompletion, VacationPeriod, StreakEvent  # avoid circular import

    tz = _user_timezone(user)
    today = _today_in_tz(tz)

    # Award one weekly freeze if not yet given this ISO week.
    _award_weekly_freeze(habit, user, today)

    # Snapshot current freeze count (may have just been incremented above).
    habit.refresh_from_db(fields=["streak_freezes_available"])

    # Build lookup sets for completions and vacation dates (last MAX_LOOKBACK_DAYS days).
    lookback_start = today - timedelta(days=MAX_LOOKBACK_DAYS)
    completion_dates: set[date] = set(
        HabitCompletion.objects.filter(
            habit=habit, completion_date__gte=lookback_start
        ).values_list("completion_date", flat=True)
    )
    vacation_dates: set[date] = _vacation_dates(user, lookback_start)

    # Calculate streak according to frequency type.
    freq = habit.frequency_type
    if freq == "daily":
        current_streak, streak_freeze_used = _calc_daily(
            habit, today, completion_dates, vacation_dates
        )
    elif freq == "weekdays":
        current_streak, streak_freeze_used = _calc_weekdays(
            habit, today, completion_dates, vacation_dates
        )
    elif freq == "n_per_week":
        current_streak, streak_freeze_used = _calc_n_per_week(
            habit, today, completion_dates, vacation_dates
        )
    else:
        logger.warning("Unknown frequency_type '%s' for habit %s", freq, habit.id)
        current_streak, streak_freeze_used = 0, False

    longest_streak = max(habit.longest_streak, current_streak)

    habit.current_streak = current_streak
    habit.longest_streak = longest_streak
    habit.save(update_fields=["current_streak", "longest_streak", "streak_freezes_available"])

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "streak_freeze_used": streak_freeze_used,
    }


# ---------------------------------------------------------------------------
# Freeze award helper
# ---------------------------------------------------------------------------

def _award_weekly_freeze(habit, user, today: date) -> None:
    """
    Award one streak freeze to *habit* for the current ISO week if:
      • no freeze has been awarded this week yet (checked via StreakEvent), and
      • habit.streak_freezes_available < 2.
    """
    from .models import StreakEvent

    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    already_awarded = StreakEvent.objects.filter(
        habit=habit,
        event_type="freeze_earned",
        event_date__range=[monday, sunday],
    ).exists()

    if not already_awarded and habit.streak_freezes_available < 2:
        habit.streak_freezes_available += 1
        habit.save(update_fields=["streak_freezes_available"])
        StreakEvent.objects.create(
            habit=habit,
            user=user,
            event_type="freeze_earned",
            event_date=today,
            streak_value=habit.current_streak,
        )


# ---------------------------------------------------------------------------
# Per-frequency streak calculators
# ---------------------------------------------------------------------------

def _calc_daily(habit, today: date, completions: set, vacations: set):
    """Daily: completed every calendar day."""
    from .models import StreakEvent

    streak = 0
    freeze_used = False
    freezes = habit.streak_freezes_available

    # Start from today if completed, else from yesterday.
    if today in completions or today in vacations:
        day = today
    else:
        day = today - timedelta(days=1)

    for _ in range(MAX_LOOKBACK_DAYS):
        if day in vacations:
            streak += 1
            day -= timedelta(days=1)
            continue

        if day in completions:
            streak += 1
            day -= timedelta(days=1)
        else:
            if streak >= 3 and freezes > 0:
                freezes -= 1
                freeze_used = True
                StreakEvent.objects.create(
                    habit=habit,
                    user=habit.user,
                    event_type="freeze_used",
                    event_date=day,
                    streak_value=streak,
                )
                streak += 1
                day -= timedelta(days=1)
            else:
                break

    habit.streak_freezes_available = freezes
    return streak, freeze_used


def _calc_weekdays(habit, today: date, completions: set, vacations: set):
    """
    Weekdays: must complete on user-specified weekdays (stored in habit.frequency_days).
    Non-scheduled days are transparent — they are skipped silently.
    """
    from .models import StreakEvent

    scheduled: set[int] = set(habit.frequency_days) if habit.frequency_days else {1, 2, 3, 4, 5}

    streak = 0
    freeze_used = False
    freezes = habit.streak_freezes_available

    # Find the most recent scheduled day.
    day = today
    steps = 0
    while day.isoweekday() not in scheduled:
        day -= timedelta(days=1)
        steps += 1
        if steps > 7:
            # No scheduled days defined (shouldn't happen after validation).
            return 0, False

    # If that day wasn't completed, retreat one more scheduled day.
    if day not in completions and day not in vacations:
        day -= timedelta(days=1)
        steps2 = 0
        while day.isoweekday() not in scheduled:
            day -= timedelta(days=1)
            steps2 += 1
            if steps2 > 7:
                return 0, False

    for _ in range(MAX_LOOKBACK_DAYS):
        # Skip non-scheduled days transparently.
        if day.isoweekday() not in scheduled:
            day -= timedelta(days=1)
            continue

        if day in vacations:
            streak += 1
            day -= timedelta(days=1)
            continue

        if day in completions:
            streak += 1
            day -= timedelta(days=1)
        else:
            if streak >= 3 and freezes > 0:
                freezes -= 1
                freeze_used = True
                StreakEvent.objects.create(
                    habit=habit,
                    user=habit.user,
                    event_type="freeze_used",
                    event_date=day,
                    streak_value=streak,
                )
                streak += 1
                day -= timedelta(days=1)
            else:
                break

    habit.streak_freezes_available = freezes
    return streak, freeze_used


def _calc_n_per_week(habit, today: date, completions: set, vacations: set):
    """
    N per week: must complete habit.frequency_count times in the ISO week.
    Streak is counted in weeks.  The current (possibly in-progress) week is
    skipped if it hasn't ended and the target hasn't been met yet.
    """
    from .models import StreakEvent

    streak = 0
    freeze_used = False
    freezes = habit.streak_freezes_available

    # Monday of current week.
    week_start = today - timedelta(days=today.weekday())
    first_week = True

    for _ in range(MAX_LOOKBACK_WEEKS):
        week_end = week_start + timedelta(days=6)

        week_completions = sum(1 for d in completions if week_start <= d <= week_end)
        week_vacations = sum(1 for d in vacations if week_start <= d <= week_end)
        effective_target = max(0, habit.frequency_count - week_vacations)

        if effective_target == 0:
            # Entire week is vacation — treat as met.
            streak += 1
            week_start -= timedelta(days=7)
            first_week = False
            continue

        if week_completions >= effective_target:
            streak += 1
            week_start -= timedelta(days=7)
        elif first_week and today <= week_end:
            # Current week is still in progress — skip without breaking streak.
            week_start -= timedelta(days=7)
        else:
            if streak >= 3 and freezes > 0:
                freezes -= 1
                freeze_used = True
                StreakEvent.objects.create(
                    habit=habit,
                    user=habit.user,
                    event_type="freeze_used",
                    event_date=week_start,
                    streak_value=streak,
                )
                streak += 1
                week_start -= timedelta(days=7)
            else:
                break

        first_week = False

    habit.streak_freezes_available = freezes
    return streak, freeze_used


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _user_timezone(user) -> zoneinfo.ZoneInfo:
    tz_str = getattr(user, "timezone", "UTC") or "UTC"
    try:
        return zoneinfo.ZoneInfo(tz_str)
    except (zoneinfo.ZoneInfoNotFoundError, Exception):
        return zoneinfo.ZoneInfo("UTC")


def _today_in_tz(tz: zoneinfo.ZoneInfo) -> date:
    from datetime import datetime
    return datetime.now(tz).date()


def _vacation_dates(user, since: date) -> set[date]:
    """Return a set of every calendar date covered by the user's vacation periods."""
    from .models import VacationPeriod

    dates: set[date] = set()
    for vp in VacationPeriod.objects.filter(user=user, end_date__gte=since):
        d = max(vp.start_date, since)
        while d <= vp.end_date:
            dates.add(d)
            d += timedelta(days=1)
    return dates
