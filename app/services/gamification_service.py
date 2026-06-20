"""
EcoTrack - Gamification Service
Handles XP, levelling up, streaks, and badge unlocks.
This is the engine that makes EcoTrack addictive (in a good way).
"""
from __future__ import annotations
from datetime import datetime, date, timedelta
from typing import Optional
from app.core.config import get_settings
from app.services import database_service as db
from app.models.schemas import Badge

settings = get_settings()

# ---------------------------------------------------------------------------
# Badge definitions
# Each badge has an id, unlock condition type, threshold, and display data.
# ---------------------------------------------------------------------------
BADGE_DEFINITIONS: list[dict] = [
    {
        "badge_id": "first_log",
        "name": "First Step",
        "description": "Logged your first carbon footprint.",
        "icon_emoji": "🌱",
        "condition_type": "log_count",
        "threshold": 1,
    },
    {
        "badge_id": "log_7",
        "name": "Week Warrior",
        "description": "Logged your footprint 7 times.",
        "icon_emoji": "📅",
        "condition_type": "log_count",
        "threshold": 7,
    },
    {
        "badge_id": "log_30",
        "name": "Consistent Eco-Tracker",
        "description": "Logged your footprint 30 times.",
        "icon_emoji": "🏅",
        "condition_type": "log_count",
        "threshold": 30,
    },
    {
        "badge_id": "streak_3",
        "name": "Habit Forming",
        "description": "Maintained a 3-day logging streak.",
        "icon_emoji": "🔥",
        "condition_type": "streak",
        "threshold": 3,
    },
    {
        "badge_id": "streak_7",
        "name": "Seven-Day Streak",
        "description": "7 days in a row! You're on fire. 🌿",
        "icon_emoji": "🔥🔥",
        "condition_type": "streak",
        "threshold": 7,
    },
    {
        "badge_id": "streak_30",
        "name": "Eco Obsessed",
        "description": "30-day streak. Legendary dedication.",
        "icon_emoji": "⚡",
        "condition_type": "streak",
        "threshold": 30,
    },
    {
        "badge_id": "level_3",
        "name": "Sapling",
        "description": "Reached level 3: Sapling.",
        "icon_emoji": "🌿",
        "condition_type": "level",
        "threshold": 3,
    },
    {
        "badge_id": "level_6",
        "name": "Rainforest Guardian",
        "description": "Reached level 6: Rainforest.",
        "icon_emoji": "🌳",
        "condition_type": "level",
        "threshold": 6,
    },
    {
        "badge_id": "saved_10kg",
        "name": "10 kg Saved",
        "description": "Saved 10 kg of CO₂ through eco-actions.",
        "icon_emoji": "♻️",
        "condition_type": "carbon_saved",
        "threshold": 10.0,
    },
    {
        "badge_id": "saved_100kg",
        "name": "Carbon Crusher",
        "description": "Saved 100 kg of CO₂. You're a climate hero.",
        "icon_emoji": "🦸",
        "condition_type": "carbon_saved",
        "threshold": 100.0,
    },
    {
        "badge_id": "zero_commute",
        "name": "Zero Emissions Commuter",
        "description": "Logged a walking or cycling commute.",
        "icon_emoji": "🚴",
        "condition_type": "special",
        "threshold": 1,
    },
]


def award_xp_and_update_streak(uid: str, xp_to_add: int) -> dict:
    """
    Core gamification update:
    1. Add XP to the user's total.
    2. Update the daily streak.
    3. Level them up if thresholds crossed.
    4. Check badge unlocks.
    Returns a summary dict for the API response.
    """
    profile = db.ensure_user_exists(uid, None)
    thresholds = settings.level_thresholds
    level_names = settings.level_names

    # --- XP ---
    new_total_xp = profile.get("total_xp", 0) + xp_to_add

    # --- Streak ---
    today = date.today().isoformat()
    last_log_date = profile.get("last_log_date")
    streak_days = profile.get("streak_days", 0)
    longest_streak = profile.get("longest_streak", 0)

    if last_log_date is None or last_log_date == today:
        # First log ever, or already logged today — streak unchanged
        pass
    elif last_log_date == (date.today() - timedelta(days=1)).isoformat():
        # Consecutive day: extend streak
        streak_days += 1
        xp_to_add += settings.xp_per_streak_day
    else:
        # Streak broken
        streak_days = 1

    longest_streak = max(longest_streak, streak_days)

    # --- Level ---
    new_level = _calculate_level(new_total_xp, thresholds)

    # --- Log count ---
    log_count = profile.get("log_count", 0) + 1

    updates = {
        "total_xp": new_total_xp,
        "level": new_level,
        "streak_days": streak_days,
        "longest_streak": longest_streak,
        "last_log_date": today,
        "log_count": log_count,
    }
    db.upsert_user_profile(uid, updates)

    # --- Badge evaluation ---
    earned_profile = {**profile, **updates}
    newly_earned_badges = _evaluate_badges(uid, earned_profile, [])
    if newly_earned_badges:
        all_badges = profile.get("badges", []) + newly_earned_badges
        db.upsert_user_profile(uid, {"badges": all_badges})

    xp_to_next = _xp_to_next_level(new_total_xp, thresholds)

    return {
        "new_total_xp": new_total_xp,
        "xp_awarded": xp_to_add,
        "streak_days": streak_days,
        "level": new_level,
        "level_name": level_names[new_level] if new_level < len(level_names) else "EcoChampion",
        "xp_to_next_level": xp_to_next,
        "newly_earned_badges": newly_earned_badges,
    }


def record_carbon_saved(uid: str, carbon_saved_kg: float) -> None:
    """Adds to the user's cumulative carbon savings (for eco-actions)."""
    profile = db.ensure_user_exists(uid, None)
    current_saved = profile.get("total_carbon_saved_kg", 0.0)
    db.upsert_user_profile(uid, {"total_carbon_saved_kg": round(current_saved + carbon_saved_kg, 4)})


def check_zero_commute_badge(uid: str, transport_mode: str) -> None:
    """Awards the zero-emission commuter badge for walking/cycling."""
    if transport_mode in ("bicycling", "walking"):
        profile = db.get_user_profile(uid) or {}
        existing_badges = [b["badge_id"] for b in profile.get("badges", [])]
        if "zero_commute" not in existing_badges:
            badge = _make_badge_from_definition(
                next(b for b in BADGE_DEFINITIONS if b["badge_id"] == "zero_commute")
            )
            all_badges = profile.get("badges", []) + [badge]
            db.upsert_user_profile(uid, {"badges": all_badges})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _calculate_level(total_xp: int, thresholds: list[int]) -> int:
    level = 0
    for i, threshold in enumerate(thresholds):
        if total_xp >= threshold:
            level = i
    return level


def _xp_to_next_level(total_xp: int, thresholds: list[int]) -> int:
    for threshold in thresholds:
        if total_xp < threshold:
            return threshold - total_xp
    return 0  # Max level


def _evaluate_badges(uid: str, profile: dict, extra_flags: list[str]) -> list[dict]:
    """Check all badge conditions and return any newly earned ones."""
    existing_ids = {b["badge_id"] for b in profile.get("badges", [])}
    newly_earned = []

    for defn in BADGE_DEFINITIONS:
        badge_id = defn["badge_id"]
        if badge_id in existing_ids:
            continue

        condition = defn["condition_type"]
        threshold = defn["threshold"]
        earned = False

        if condition == "log_count" and profile.get("log_count", 0) >= threshold:
            earned = True
        elif condition == "streak" and profile.get("streak_days", 0) >= threshold:
            earned = True
        elif condition == "level" and profile.get("level", 0) >= threshold:
            earned = True
        elif condition == "carbon_saved" and profile.get("total_carbon_saved_kg", 0.0) >= threshold:
            earned = True
        elif condition == "special" and badge_id in extra_flags:
            earned = True

        if earned:
            newly_earned.append(_make_badge_from_definition(defn))

    return newly_earned


def _make_badge_from_definition(defn: dict) -> dict:
    return {
        "badge_id": defn["badge_id"],
        "name": defn["name"],
        "description": defn["description"],
        "icon_emoji": defn["icon_emoji"],
        "earned_at": datetime.utcnow().isoformat(),
    }
