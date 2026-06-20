"""
EcoTrack - Weekly Challenge Service
Auto-generates weekly challenges and tracks user progress.
Challenges reset every Monday and are the same for all users (social).
"""
from __future__ import annotations
from datetime import datetime, date, timedelta
from app.core.config import get_settings
from app.services import database_service as db
from app.models.schemas import Challenge

settings = get_settings()

# ---------------------------------------------------------------------------
# Challenge catalogue — one pool rotated weekly by ISO week number
# ---------------------------------------------------------------------------
CHALLENGE_POOL: list[dict] = [
    {
        "challenge_id": "no_car_week",
        "title": "🚌 Car-Free Commuter",
        "description": "Log 5 commutes this week without using a car.",
        "icon_emoji": "🚌",
        "target_metric": "non_car_commute_count",
        "target_value": 5,
        "xp_reward": 75,
    },
    {
        "challenge_id": "low_footprint_week",
        "title": "🌱 Green Week",
        "description": "Keep your total weekly emissions under 20 kg CO₂.",
        "icon_emoji": "🌱",
        "target_metric": "weekly_total_kg",
        "target_value": 20.0,
        "xp_reward": 60,
    },
    {
        "challenge_id": "plant_based_meals",
        "title": "🥗 Plant-Based Days",
        "description": "Log 5 vegetarian or vegan meals this week.",
        "icon_emoji": "🥗",
        "target_metric": "plant_based_meal_count",
        "target_value": 5,
        "xp_reward": 50,
    },
    {
        "challenge_id": "eco_actions_5",
        "title": "♻️ Eco-Action Hero",
        "description": "Complete 5 eco-friendly actions this week.",
        "icon_emoji": "♻️",
        "target_metric": "eco_action_count",
        "target_value": 5,
        "xp_reward": 50,
    },
    {
        "challenge_id": "daily_logger",
        "title": "📅 Daily Devotion",
        "description": "Log your footprint every day this week (7 days).",
        "icon_emoji": "📅",
        "target_metric": "unique_log_days",
        "target_value": 7,
        "xp_reward": 100,
    },
    {
        "challenge_id": "bike_or_walk",
        "title": "🚴 Pedal Power",
        "description": "Log 3 cycling or walking commutes this week.",
        "icon_emoji": "🚴",
        "target_metric": "zero_emission_commute_count",
        "target_value": 3,
        "xp_reward": 60,
    },
    {
        "challenge_id": "carbon_save_5kg",
        "title": "💪 Save 5 kg of CO₂",
        "description": "Accumulate 5 kg of CO₂ savings through eco-actions.",
        "icon_emoji": "💪",
        "target_metric": "carbon_saved_kg",
        "target_value": 5.0,
        "xp_reward": 65,
    },
]


def get_current_week_challenges() -> list[dict]:
    """
    Returns the 3 active challenges for the current ISO week.
    Rotated deterministically by week number so all users see the same set.
    """
    week_number = date.today().isocalendar()[1]
    start_index = (week_number * 3) % len(CHALLENGE_POOL)
    indices = [start_index % len(CHALLENGE_POOL),
               (start_index + 1) % len(CHALLENGE_POOL),
               (start_index + 2) % len(CHALLENGE_POOL)]
    selected = [CHALLENGE_POOL[i] for i in indices]
    deadline = _get_week_end_date()
    return [{**c, "deadline_date": deadline} for c in selected]


def get_user_challenge_status(uid: str) -> dict:
    """
    Fetches this week's challenges and enriches them with the user's progress.
    """
    week_challenges = get_current_week_challenges()
    recent_logs = db.get_user_logs(uid, days=7)
    progress_map = _calculate_progress_from_logs(recent_logs)

    active = []
    completed = []

    for challenge in week_challenges:
        metric = challenge["target_metric"]
        target = challenge["target_value"]
        progress_value = progress_map.get(metric, 0.0)
        is_completed = progress_value >= target
        progress_percent = round(min(progress_value / target, 1.0) * 100, 1) if target > 0 else 0

        enriched = Challenge(
            challenge_id=challenge["challenge_id"],
            title=challenge["title"],
            description=challenge["description"],
            icon_emoji=challenge["icon_emoji"],
            target_metric=challenge["target_metric"],
            target_value=target,
            xp_reward=challenge["xp_reward"],
            deadline_date=challenge["deadline_date"],
            is_completed=is_completed,
            progress_value=round(float(progress_value), 2),
            progress_percent=progress_percent,
        )

        if is_completed:
            completed.append(enriched)
        else:
            active.append(enriched)

    return {"active_challenges": active, "completed_challenges": completed}


def check_and_award_challenge_completion(uid: str) -> list[dict]:
    """
    Called after every log — checks if any challenge just crossed its threshold.
    Awards XP for newly completed challenges.
    Returns list of newly completed challenges.
    """
    from app.services import gamification_service as gs
    status = get_user_challenge_status(uid)
    newly_completed = []

    for challenge in status["completed_challenges"]:
        # Check if we already awarded XP for this challenge this week
        week_key = f"week_{date.today().isocalendar()[1]}"
        progress = db.get_challenge_progress(uid, challenge.challenge_id)

        if not progress or not progress.get("xp_awarded"):
            # Award XP for completing the challenge
            gs.award_xp_and_update_streak(uid, challenge.xp_reward)
            db.save_challenge_progress(
                uid,
                challenge.challenge_id,
                {"completed": True, "xp_awarded": True, "week": week_key},
            )
            newly_completed.append(challenge.dict())

    return newly_completed


# ---------------------------------------------------------------------------
# Progress calculation from raw logs
# ---------------------------------------------------------------------------

def _calculate_progress_from_logs(logs: list[dict]) -> dict[str, float]:
    """Derives all possible challenge metrics from a list of log dicts."""
    metrics: dict[str, float] = {
        "non_car_commute_count": 0,
        "weekly_total_kg": 0,
        "plant_based_meal_count": 0,
        "eco_action_count": 0,
        "unique_log_days": 0,
        "zero_emission_commute_count": 0,
        "carbon_saved_kg": 0,
    }

    unique_days: set[str] = set()

    for log in logs:
        log_type = log.get("log_type", "commute")
        day = (log.get("logged_at") or "")[:10]
        if day:
            unique_days.add(day)

        emissions = log.get("carbon_emissions_kg", 0.0)
        metrics["weekly_total_kg"] += emissions

        if log_type == "commute":
            mode = log.get("transport_mode", "")
            if mode in ("transit", "bicycling", "walking"):
                metrics["non_car_commute_count"] += 1
            if mode in ("bicycling", "walking"):
                metrics["zero_emission_commute_count"] += 1

        elif log_type == "diet":
            meal = log.get("meal_type", "")
            if meal in ("vegetarian", "vegan"):
                metrics["plant_based_meal_count"] += 1

        elif log_type == "eco_action":
            metrics["eco_action_count"] += log.get("quantity", 1)
            metrics["carbon_saved_kg"] += log.get("carbon_saved_kg", 0.0)

    metrics["unique_log_days"] = float(len(unique_days))
    return metrics


def _get_week_end_date() -> str:
    """Returns next Sunday's ISO date string."""
    today = date.today()
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7
    return (today + timedelta(days=days_until_sunday)).isoformat()
