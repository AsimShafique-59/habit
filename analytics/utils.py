"""
Pure computation helpers for the analytics app.

All functions query existing models and return plain Python dicts/lists.
No database writes occur here.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _date_range(from_date: date, to_date: date):
    """Yield each date in [from_date, to_date] inclusive."""
    current = from_date
    while current <= to_date:
        yield current
        current += timedelta(days=1)


def _is_habit_scheduled(habit, d: date) -> bool:
    """Return True if *habit* should be completed on calendar date *d*."""
    freq = habit.frequency_type
    if freq == "daily":
        return True
    if freq == "weekdays":
        # frequency_days stores ISO weekday ints (1=Mon … 7=Sun)
        scheduled = set(habit.frequency_days) if habit.frequency_days else {1, 2, 3, 4, 5}
        return d.isoweekday() in scheduled
    if freq == "n_per_week":
        # For n_per_week we treat every day as potentially scheduled (user
        # can pick any day to fulfil the weekly quota).  We count completions
        # per ISO week and compare against frequency_count in callers that need
        # per-day granularity.  Here we return True so the day is included.
        return True
    return False


def _scheduled_days_in_range(habit, from_date: date, to_date: date) -> list[date]:
    """Return sorted list of dates in the range on which *habit* is scheduled."""
    return [d for d in _date_range(from_date, to_date) if _is_habit_scheduled(habit, d)]


# ---------------------------------------------------------------------------
# RP-001 – Completion rate
# ---------------------------------------------------------------------------

def get_completion_rate(user, from_date: date, to_date: date) -> dict:
    """
    Overall completion rate + per-habit breakdown.

    Returns::

        {
            overall_rate: float,
            by_habit: [
                {habit_id, name, rate, completed, scheduled}
            ]
        }
    """
    from habits.models import Habit, HabitCompletion

    habits = list(
        Habit.objects.filter(user=user, is_archived=False)
    )
    completions = set(
        HabitCompletion.objects.filter(
            user=user,
            completion_date__range=(from_date, to_date),
        ).values_list("habit_id", "completion_date")
    )

    total_scheduled = 0
    total_completed = 0
    by_habit = []

    for habit in habits:
        scheduled_dates = _scheduled_days_in_range(habit, from_date, to_date)
        scheduled = len(scheduled_dates)

        # For n_per_week, cap scheduled count at frequency_count * number_of_weeks
        if habit.frequency_type == "n_per_week":
            num_weeks = max(1, (to_date - from_date).days // 7 + 1)
            scheduled = habit.frequency_count * num_weeks

        completed = sum(
            1 for d in scheduled_dates
            if (habit.id, d) in completions
        )
        rate = (completed / scheduled) if scheduled > 0 else 0.0

        total_scheduled += scheduled
        total_completed += completed
        by_habit.append({
            "habit_id": str(habit.id),
            "name": habit.title,
            "rate": round(rate, 4),
            "completed": completed,
            "scheduled": scheduled,
        })

    overall_rate = (total_completed / total_scheduled) if total_scheduled > 0 else 0.0
    return {
        "overall_rate": round(overall_rate, 4),
        "by_habit": by_habit,
    }


# ---------------------------------------------------------------------------
# RP-002 – Consistency heatmap
# ---------------------------------------------------------------------------

def get_heatmap_data(user, days: int = 365) -> list:
    """
    Per-day completion summary for the last *days* calendar days.

    Returns list of::

        {date, completion_rate, completed, total}
    """
    from habits.models import Habit, HabitCompletion

    to_date = date.today()
    from_date = to_date - timedelta(days=days - 1)

    habits = list(Habit.objects.filter(user=user, is_archived=False))

    # Fetch all relevant completions as a set of (habit_id, completion_date)
    completions = set(
        HabitCompletion.objects.filter(
            user=user,
            completion_date__range=(from_date, to_date),
        ).values_list("habit_id", "completion_date")
    )

    result = []
    for d in _date_range(from_date, to_date):
        scheduled_habits = [h for h in habits if _is_habit_scheduled(h, d)]
        total = len(scheduled_habits)
        completed = sum(1 for h in scheduled_habits if (h.id, d) in completions)
        rate = (completed / total) if total > 0 else 0.0
        result.append({
            "date": d.isoformat(),
            "completion_rate": round(rate, 4),
            "completed": completed,
            "total": total,
        })

    return result


# ---------------------------------------------------------------------------
# RP-003 – Streak dashboard
# ---------------------------------------------------------------------------

def get_streak_dashboard(user) -> dict:
    """
    Current / longest streak per habit plus at-risk flag.

    ``at_risk`` is True when the habit is scheduled today, has not yet been
    completed today, and UTC time is past 18:00.

    Returns::

        {habits: [{habit_id, name, current_streak, longest_streak, at_risk}]}
    """
    from habits.models import Habit, HabitCompletion

    today = date.today()
    now_utc = datetime.now(dt_timezone.utc)
    past_six_pm = now_utc.hour >= 18

    habits = list(Habit.objects.filter(user=user, is_archived=False))

    completed_today = set(
        HabitCompletion.objects.filter(
            user=user,
            completion_date=today,
        ).values_list("habit_id", flat=True)
    )

    result = []
    for habit in habits:
        scheduled_today = _is_habit_scheduled(habit, today)
        at_risk = (
            scheduled_today
            and habit.id not in completed_today
            and past_six_pm
        )
        result.append({
            "habit_id": str(habit.id),
            "name": habit.title,
            "current_streak": habit.current_streak,
            "longest_streak": habit.longest_streak,
            "at_risk": at_risk,
        })

    return {"habits": result}


# ---------------------------------------------------------------------------
# RP-004 – Day-of-week breakdown
# ---------------------------------------------------------------------------

def get_day_of_week_breakdown(user, from_date: date, to_date: date) -> dict:
    """
    Average completion rate per weekday across the date range.

    Returns::

        {Mon: rate, Tue: rate, Wed: rate, Thu: rate, Fri: rate, Sat: rate, Sun: rate}
    """
    from habits.models import Habit, HabitCompletion

    habits = list(Habit.objects.filter(user=user, is_archived=False))
    completions = set(
        HabitCompletion.objects.filter(
            user=user,
            completion_date__range=(from_date, to_date),
        ).values_list("habit_id", "completion_date")
    )

    # day_index 0=Mon … 6=Sun  (matches _DAY_NAMES)
    scheduled_by_day: dict[int, int] = defaultdict(int)
    completed_by_day: dict[int, int] = defaultdict(int)

    for d in _date_range(from_date, to_date):
        day_idx = d.weekday()  # 0=Mon
        for habit in habits:
            if _is_habit_scheduled(habit, d):
                scheduled_by_day[day_idx] += 1
                if (habit.id, d) in completions:
                    completed_by_day[day_idx] += 1

    return {
        _DAY_NAMES[i]: round(
            completed_by_day[i] / scheduled_by_day[i], 4
        ) if scheduled_by_day[i] > 0 else 0.0
        for i in range(7)
    }


# ---------------------------------------------------------------------------
# RP-005 (partial) – Time-of-day heatmap placeholder
# ---------------------------------------------------------------------------

def get_time_of_day_heatmap(user, from_date: date, to_date: date) -> list:
    """
    HabitCompletion does not store completion time granularity for a
    per-hour breakdown; returns empty list with explanatory note.
    """
    return []


# ---------------------------------------------------------------------------
# RP-005 – Momentum index
# ---------------------------------------------------------------------------

def get_momentum_index(user) -> dict:
    """
    Average completion rate over fixed look-back windows.

    Returns::

        {score_7d, score_30d, score_90d}
    """
    today = date.today()

    def _window_rate(days: int) -> float:
        from_date = today - timedelta(days=days - 1)
        data = get_completion_rate(user, from_date, today)
        return data["overall_rate"]

    return {
        "score_7d": _window_rate(7),
        "score_30d": _window_rate(30),
        "score_90d": _window_rate(90),
    }


# ---------------------------------------------------------------------------
# RP-004 – Missed-habit trends
# ---------------------------------------------------------------------------

def get_missed_trends(user, from_date: date, to_date: date) -> dict:
    """
    Day-by-day missed count and total scheduled.

    Returns::

        {
            trend_direction: "improving"|"stable"|"declining",
            data: [{ date, missed_count, total_scheduled }]
        }
    """
    from habits.models import Habit, HabitCompletion

    habits = list(Habit.objects.filter(user=user, is_archived=False))
    completions = set(
        HabitCompletion.objects.filter(
            user=user,
            completion_date__range=(from_date, to_date),
        ).values_list("habit_id", "completion_date")
    )

    rows = []
    for d in _date_range(from_date, to_date):
        scheduled = [h for h in habits if _is_habit_scheduled(h, d)]
        total = len(scheduled)
        completed = sum(1 for h in scheduled if (h.id, d) in completions)
        rows.append({
            "date": d.isoformat(),
            "missed_count": total - completed,
            "total_scheduled": total,
        })

    # Trend: compare first half vs second half miss rate
    if len(rows) >= 4:
        mid = len(rows) // 2
        def _miss_rate(chunk):
            tot = sum(r["total_scheduled"] for r in chunk)
            missed = sum(r["missed_count"] for r in chunk)
            return missed / tot if tot > 0 else 0.0
        first_half_rate = _miss_rate(rows[:mid])
        second_half_rate = _miss_rate(rows[mid:])
        diff = second_half_rate - first_half_rate
        if diff < -0.05:
            trend = "improving"
        elif diff > 0.05:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "stable"

    return {"trend_direction": trend, "data": rows}


# ---------------------------------------------------------------------------
# RP-006 – Monthly performance
# ---------------------------------------------------------------------------

def get_monthly_performance(user, year: int, month: int) -> dict:
    """
    Completion breakdown for a calendar month.

    Returns::

        {
            month, year, completion_rate, total_completed, total_scheduled,
            by_habit: [...], best_day, worst_day
        }
    """
    import calendar
    from_date = date(year, month, 1)
    to_date = date(year, month, calendar.monthrange(year, month)[1])

    rate_data = get_completion_rate(user, from_date, to_date)
    dow = get_day_of_week_breakdown(user, from_date, to_date)
    best_day = max(dow, key=lambda k: dow[k]) if dow else None
    worst_day = min(dow, key=lambda k: dow[k]) if dow else None

    total_scheduled = sum(h["scheduled"] for h in rate_data["by_habit"])
    total_completed = sum(h["completed"] for h in rate_data["by_habit"])

    return {
        "year": year,
        "month": month,
        "completion_rate": rate_data["overall_rate"],
        "total_completed": total_completed,
        "total_scheduled": total_scheduled,
        "by_habit": rate_data["by_habit"],
        "best_day": best_day,
        "worst_day": worst_day,
    }


# ---------------------------------------------------------------------------
# RP-007 – Consistency score
# ---------------------------------------------------------------------------

def get_consistency_score(user) -> dict:
    """
    0-100 weighted score (rolling 30 days).

    Weighting: difficulty multiplier (tiny=0.5, small=1.0, medium=1.5)
    multiplied by streak bonus (current_streak / max(longest_streak, 1)).

    Returns::

        { score: int (0-100), details: [...] }
    """
    from habits.models import Habit, HabitCompletion

    today = date.today()
    from_date = today - timedelta(days=29)

    habits = list(Habit.objects.filter(user=user, is_archived=False))
    if not habits:
        return {"score": 0, "details": []}

    completions = set(
        HabitCompletion.objects.filter(
            user=user,
            completion_date__range=(from_date, today),
        ).values_list("habit_id", "completion_date")
    )

    _difficulty_weight = {"tiny": 0.5, "small": 1.0, "medium": 1.5}
    weighted_sum = 0.0
    max_sum = 0.0
    details = []

    for habit in habits:
        scheduled = [d for d in _date_range(from_date, today) if _is_habit_scheduled(habit, d)]
        if not scheduled:
            continue
        completed_count = sum(1 for d in scheduled if (habit.id, d) in completions)
        rate = completed_count / len(scheduled)
        diff_w = _difficulty_weight.get(habit.difficulty, 1.0)
        streak_bonus = habit.current_streak / max(habit.longest_streak, 1)
        weight = diff_w * (1 + 0.2 * streak_bonus)
        weighted_sum += rate * weight
        max_sum += weight
        details.append({
            "habit_id": str(habit.id),
            "title": habit.title,
            "rate": round(rate, 4),
            "weight": round(weight, 4),
        })

    score = round((weighted_sum / max_sum) * 100) if max_sum > 0 else 0
    return {"score": min(score, 100), "details": details}


# ---------------------------------------------------------------------------
# RP-010 – Time-of-day heatmap
# ---------------------------------------------------------------------------

def get_time_of_day_heatmap_real(user, from_date: date, to_date: date) -> list:
    """
    24×7 grid of completion counts using the `completed_at` timestamp.

    Returns a flat list of 168 dicts: {hour, weekday, count}.
    """
    from habits.models import HabitCompletion
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    completions = HabitCompletion.objects.filter(
        user=user,
        completion_date__range=(from_date, to_date),
    ).values_list("completed_at", flat=True)

    tz_name = getattr(user, "timezone", "UTC") or "UTC"
    try:
        user_tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError):
        user_tz = ZoneInfo("UTC")

    grid: dict[tuple[int, int], int] = defaultdict(int)
    for completed_at in completions:
        local_dt = completed_at.astimezone(user_tz)
        grid[(local_dt.hour, local_dt.weekday())] += 1

    result = []
    for hour in range(24):
        for weekday in range(7):
            result.append({
                "hour": hour,
                "weekday": _DAY_NAMES[weekday],
                "count": grid[(hour, weekday)],
            })
    return result


# ---------------------------------------------------------------------------
# RP-016 – Sleep × habit correlation (stub — requires HealthKit/Fit data)
# ---------------------------------------------------------------------------

def get_sleep_habit_correlation(user, from_date: date, to_date: date) -> dict:
    """
    Correlate sleep data with per-habit completion.

    Requires at least 14 days of sleep data imported via integrations.
    Returns insufficient_data when sleep records are absent.
    """
    from integrations.models import HealthDataPoint

    sleep_qs = HealthDataPoint.objects.filter(
        user=user,
        metric="sleep_minutes",
        recorded_date__range=(from_date, to_date),
    ).values("recorded_date", "value")

    sleep_by_date = {row["recorded_date"]: row["value"] for row in sleep_qs}

    if len(sleep_by_date) < 14:
        return {"available": False, "required_days": 14}

    from habits.models import Habit, HabitCompletion

    habits = list(Habit.objects.filter(user=user, is_archived=False))
    completions = set(
        HabitCompletion.objects.filter(
            user=user,
            completion_date__range=(from_date, to_date),
        ).values_list("habit_id", "completion_date")
    )

    correlations = []
    for habit in habits:
        complete_sleep: list[float] = []
        miss_sleep: list[float] = []

        for d, sleep_val in sleep_by_date.items():
            if not _is_habit_scheduled(habit, d):
                continue
            if (habit.id, d) in completions:
                complete_sleep.append(float(sleep_val))
            else:
                miss_sleep.append(float(sleep_val))

        avg_complete = (sum(complete_sleep) / len(complete_sleep)) if complete_sleep else None
        avg_miss = (sum(miss_sleep) / len(miss_sleep)) if miss_sleep else None

        if avg_complete is not None and avg_miss is not None:
            diff = avg_complete - avg_miss
            correlation = "positive" if diff > 0.3 else ("negative" if diff < -0.3 else "neutral")
        else:
            correlation = "neutral"

        correlations.append({
            "habit_id": str(habit.id),
            "name": habit.title,
            "avg_sleep_on_complete": round(avg_complete, 2) if avg_complete is not None else None,
            "avg_sleep_on_miss": round(avg_miss, 2) if avg_miss is not None else None,
            "correlation": correlation,
        })

    return {"available": True, "correlations": correlations}


# ---------------------------------------------------------------------------
# RP-017 – Identity progress
# ---------------------------------------------------------------------------

def get_identity_progress(user, tag: str, from_date: date, to_date: date) -> dict:
    """
    Days the user behaved consistently with an identity tag.

    A day "counts" if at least one tagged habit was completed.

    Returns::

        {
            tag, total_days, identity_days, identity_rate,
            daily: [{ date, consistent: bool }]
        }
    """
    from habits.models import Habit, HabitCompletion

    tagged_habits = list(Habit.objects.filter(user=user, is_archived=False))
    tagged_habits = [h for h in tagged_habits if tag in (h.identity_tags or [])]

    if not tagged_habits:
        return {
            "tag": tag,
            "total_days": 0,
            "identity_days": 0,
            "identity_rate": 0.0,
            "daily": [],
        }

    completions = set(
        HabitCompletion.objects.filter(
            user=user,
            habit__in=tagged_habits,
            completion_date__range=(from_date, to_date),
        ).values_list("habit_id", "completion_date")
    )

    daily = []
    identity_days = 0
    for d in _date_range(from_date, to_date):
        consistent = any(
            (h.id, d) in completions
            for h in tagged_habits
            if _is_habit_scheduled(h, d)
        )
        if consistent:
            identity_days += 1
        daily.append({"date": d.isoformat(), "consistent": consistent})

    total_days = len(daily)
    return {
        "tag": tag,
        "total_days": total_days,
        "identity_days": identity_days,
        "identity_rate": round(identity_days / total_days, 4) if total_days > 0 else 0.0,
        "daily": daily,
    }


# ---------------------------------------------------------------------------
# RP-018 – Time investment
# ---------------------------------------------------------------------------

def get_time_investment(user, from_date: date, to_date: date) -> dict:
    """
    Total duration_minutes invested per category and per habit.

    Returns::

        {
            total_minutes, by_category: {...}, by_habit: [...]
        }
    """
    from habits.models import Habit, HabitCompletion

    habits = {h.id: h for h in Habit.objects.filter(user=user, is_archived=False)}
    completions = HabitCompletion.objects.filter(
        user=user,
        completion_date__range=(from_date, to_date),
    ).values_list("habit_id", flat=True)

    by_category: dict[str, int] = defaultdict(int)
    by_habit: dict[str, dict] = defaultdict(lambda: {"minutes": 0, "completions": 0})
    total_minutes = 0

    for habit_id in completions:
        habit = habits.get(habit_id)
        if habit is None:
            continue
        mins = habit.duration_minutes or 0
        by_category[habit.category] += mins
        by_habit[str(habit_id)]["minutes"] += mins
        by_habit[str(habit_id)]["completions"] += 1
        total_minutes += mins

    by_habit_list = [
        {
            "habit_id": hid,
            "title": habits[uuid_from_str(hid)].title if uuid_from_str(hid) in habits else "",
            "minutes": v["minutes"],
            "completions": v["completions"],
        }
        for hid, v in by_habit.items()
    ]
    by_habit_list.sort(key=lambda x: x["minutes"], reverse=True)

    return {
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "total_minutes": total_minutes,
        "by_category": dict(by_category),
        "by_habit": by_habit_list,
    }


def uuid_from_str(s: str):
    import uuid
    try:
        return uuid.UUID(s)
    except ValueError:
        return None



# ---------------------------------------------------------------------------
# RP-006 – Mood × habit correlation
# ---------------------------------------------------------------------------

def get_mood_habit_correlation(user, from_date: date, to_date: date) -> dict:
    """
    Correlate daily mood score with per-habit completion.

    Requires at least 14 days of mood data; returns
    ``{available: false, required_days: 14}`` otherwise.

    Returns::

        {
            available: true,
            correlations: [
                {
                    habit_id, name,
                    avg_mood_on_complete,
                    avg_mood_on_miss,
                    correlation: "positive"|"negative"|"neutral"
                }
            ]
        }
    """
    from habits.models import Habit, HabitCompletion
    from reflection.models import MoodLog

    mood_qs = MoodLog.objects.filter(
        user=user,
        date__range=(from_date, to_date),
    ).values("date", "score")

    mood_by_date: dict[date, int] = {row["date"]: row["score"] for row in mood_qs}

    if len(mood_by_date) < 14:
        return {"available": False, "required_days": 14}

    habits = list(Habit.objects.filter(user=user, is_archived=False))
    completions = set(
        HabitCompletion.objects.filter(
            user=user,
            completion_date__range=(from_date, to_date),
        ).values_list("habit_id", "completion_date")
    )

    correlations = []
    for habit in habits:
        complete_scores: list[int] = []
        miss_scores: list[int] = []

        for d, mood in mood_by_date.items():
            if not _is_habit_scheduled(habit, d):
                continue
            if (habit.id, d) in completions:
                complete_scores.append(mood)
            else:
                miss_scores.append(mood)

        avg_complete = (sum(complete_scores) / len(complete_scores)) if complete_scores else None
        avg_miss = (sum(miss_scores) / len(miss_scores)) if miss_scores else None

        if avg_complete is not None and avg_miss is not None:
            diff = avg_complete - avg_miss
            if diff > 0.3:
                correlation = "positive"
            elif diff < -0.3:
                correlation = "negative"
            else:
                correlation = "neutral"
        else:
            correlation = "neutral"

        correlations.append({
            "habit_id": str(habit.id),
            "name": habit.title,
            "avg_mood_on_complete": round(avg_complete, 2) if avg_complete is not None else None,
            "avg_mood_on_miss": round(avg_miss, 2) if avg_miss is not None else None,
            "correlation": correlation,
        })

    return {"available": True, "correlations": correlations}


# ---------------------------------------------------------------------------
# RP-007 – Habit co-completion matrix
# ---------------------------------------------------------------------------

def get_habit_correlation_matrix(user, from_date: date, to_date: date) -> list:
    """
    Measure how often pairs of habits are completed on the same day.

    Returns::

        [
            {
                habit_a_id, habit_a_name,
                habit_b_id, habit_b_name,
                co_completion_rate
            }
        ]
    """
    from habits.models import Habit, HabitCompletion

    habits = list(Habit.objects.filter(user=user, is_archived=False))
    if len(habits) < 2:
        return []

    # Map habit_id -> set of completion dates
    completion_qs = HabitCompletion.objects.filter(
        user=user,
        completion_date__range=(from_date, to_date),
    ).values_list("habit_id", "completion_date")

    completions_by_habit: dict = defaultdict(set)
    for habit_id, comp_date in completion_qs:
        completions_by_habit[habit_id].add(comp_date)

    # Build all-dates set
    all_dates = list(_date_range(from_date, to_date))

    result = []
    for i in range(len(habits)):
        for j in range(i + 1, len(habits)):
            ha = habits[i]
            hb = habits[j]

            dates_a = completions_by_habit.get(ha.id, set())
            dates_b = completions_by_habit.get(hb.id, set())

            # Days both were scheduled
            both_scheduled = [
                d for d in all_dates
                if _is_habit_scheduled(ha, d) and _is_habit_scheduled(hb, d)
            ]
            if not both_scheduled:
                continue

            co_completed = sum(1 for d in both_scheduled if d in dates_a and d in dates_b)
            rate = round(co_completed / len(both_scheduled), 4)

            result.append({
                "habit_a_id": str(ha.id),
                "habit_a_name": ha.title,
                "habit_b_id": str(hb.id),
                "habit_b_name": hb.title,
                "co_completion_rate": rate,
            })

    # Sort by co_completion_rate descending
    result.sort(key=lambda x: x["co_completion_rate"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# RP-008 – Failure patterns
# ---------------------------------------------------------------------------

def get_failure_patterns(user, from_date: date, to_date: date) -> dict:
    """
    Missed completions grouped by day-of-week.

    Returns::

        {
            patterns: [
                {day_of_week, miss_count, miss_rate}
            ],
            worst_day: str
        }
    """
    from habits.models import Habit, HabitCompletion

    habits = list(Habit.objects.filter(user=user, is_archived=False))
    completions = set(
        HabitCompletion.objects.filter(
            user=user,
            completion_date__range=(from_date, to_date),
        ).values_list("habit_id", "completion_date")
    )

    scheduled_by_day: dict[int, int] = defaultdict(int)
    missed_by_day: dict[int, int] = defaultdict(int)

    for d in _date_range(from_date, to_date):
        day_idx = d.weekday()
        for habit in habits:
            if _is_habit_scheduled(habit, d):
                scheduled_by_day[day_idx] += 1
                if (habit.id, d) not in completions:
                    missed_by_day[day_idx] += 1

    patterns = []
    for i in range(7):
        scheduled = scheduled_by_day[i]
        misses = missed_by_day[i]
        miss_rate = round(misses / scheduled, 4) if scheduled > 0 else 0.0
        patterns.append({
            "day_of_week": _DAY_NAMES[i],
            "miss_count": misses,
            "miss_rate": miss_rate,
        })

    worst_day = max(patterns, key=lambda p: p["miss_rate"])["day_of_week"] if patterns else ""
    return {"patterns": patterns, "worst_day": worst_day}


# ---------------------------------------------------------------------------
# Weekly report computation
# ---------------------------------------------------------------------------

def compute_weekly_report(user, week_start: date, week_end: date) -> dict:
    """
    Compute fields needed to create/update a WeeklyReport.

    Returns::

        {
            completion_rate, best_day, worst_day,
            mood_average, narrative
        }
    """
    from reflection.models import MoodLog

    # Completion breakdown by day
    dow = get_day_of_week_breakdown(user, week_start, week_end)
    completion_rate = get_completion_rate(user, week_start, week_end)["overall_rate"]

    best_day = max(dow, key=lambda k: dow[k]) if dow else ""
    worst_day = min(dow, key=lambda k: dow[k]) if dow else ""

    mood_qs = MoodLog.objects.filter(
        user=user,
        date__range=(week_start, week_end),
    ).values_list("score", flat=True)
    mood_scores = list(mood_qs)
    mood_average = round(sum(mood_scores) / len(mood_scores), 2) if mood_scores else None

    # Template-based narrative
    pct = round(completion_rate * 100)
    lines = [
        f"Week of {week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}.",
        f"You completed {pct}% of your scheduled habits this week.",
    ]
    if best_day:
        lines.append(f"Your strongest day was {best_day} and your weakest was {worst_day}.")
    if mood_average is not None:
        lines.append(f"Average mood this week: {mood_average:.1f}/5.")
    if pct >= 80:
        lines.append("Outstanding consistency — keep up the momentum!")
    elif pct >= 50:
        lines.append("Solid effort this week. Aim a little higher next week.")
    else:
        lines.append("A tough week — small steps still count. You can do better next week.")

    return {
        "completion_rate": completion_rate,
        "best_day": best_day,
        "worst_day": worst_day,
        "mood_average": mood_average,
        "narrative": " ".join(lines),
    }
