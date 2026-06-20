"""
EcoTrack - Analytics Service
Aggregates raw logs into per-day and per-period summaries.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from app.models.schemas import DailyEmission, HistoryResponse
from app.services import database_service as db

# Global average daily CO₂ per person (Our World in Data, 2022): ~16.1 kg/day
GLOBAL_AVERAGE_DAILY_KG = 16.1


def get_emissions_history(uid: str, days: int = 30) -> HistoryResponse:
    """
    Aggregates a user's logs over the last `days` into daily buckets.
    Compares their average to the global per-capita daily average.
    """
    logs = db.get_user_logs(uid, days=days)

    # Bucket by date and category
    daily_buckets: dict[str, dict[str, float]] = defaultdict(
        lambda: {"transport_kg": 0.0, "diet_kg": 0.0, "energy_kg": 0.0}
    )

    for log in logs:
        log_date = (log.get("logged_at") or "")[:10]
        if not log_date:
            continue
        log_type = log.get("log_type", "commute")
        emissions = log.get("carbon_emissions_kg", 0.0)

        if log_type == "commute":
            daily_buckets[log_date]["transport_kg"] += emissions
        elif log_type == "diet":
            daily_buckets[log_date]["diet_kg"] += emissions
        elif log_type == "energy":
            daily_buckets[log_date]["energy_kg"] += emissions
        # eco_action logs store carbon_saved, not emissions — excluded from totals

    # Build ordered list for the response
    daily_emissions: list[DailyEmission] = []
    today = date.today()
    for i in range(days - 1, -1, -1):
        day_str = (today - timedelta(days=i)).isoformat()
        bucket = daily_buckets.get(
            day_str, {"transport_kg": 0.0, "diet_kg": 0.0, "energy_kg": 0.0}
        )
        total = round(
            bucket["transport_kg"] + bucket["diet_kg"] + bucket["energy_kg"], 4
        )
        daily_emissions.append(
            DailyEmission(
                date=day_str,
                transport_kg=round(bucket["transport_kg"], 4),
                diet_kg=round(bucket["diet_kg"], 4),
                energy_kg=round(bucket["energy_kg"], 4),
                total_kg=total,
            )
        )

    # Period stats
    period_total = round(sum(d.total_kg for d in daily_emissions), 4)
    active_days = sum(1 for d in daily_emissions if d.total_kg > 0)
    period_average = round(period_total / active_days,
                           4) if active_days > 0 else 0.0
    comparison_pct = (
        round(
            ((period_average - GLOBAL_AVERAGE_DAILY_KG) / GLOBAL_AVERAGE_DAILY_KG)
            * 100,
            1,
        )
        if GLOBAL_AVERAGE_DAILY_KG > 0
        else 0.0
    )

    return HistoryResponse(
        daily_emissions=daily_emissions,
        period_total_kg=period_total,
        period_average_daily_kg=period_average,
        comparison_to_global_average_percent=comparison_pct,
    )


def get_leaderboard_with_user_rank(current_uid: str, limit: int = 10) -> dict:
    """
    Returns the top-N leaderboard entries with the current user's rank highlighted.
    """
    all_users = db.get_leaderboard(limit=50)

    ranked = []
    current_user_rank = None

    for rank_index, user in enumerate(all_users, start=1):
        entry = {
            "rank": rank_index,
            "uid": user.get("uid", ""),
            "display_name": user.get("display_name", "Anonymous"),
            "total_xp": user.get("total_xp", 0),
            "level_name": _uid_to_level_name(user),
            "total_carbon_saved_kg": user.get("total_carbon_saved_kg", 0.0),
        }
        if user.get("uid") == current_uid:
            current_user_rank = rank_index
        ranked.append(entry)

    top_entries = ranked[:limit]

    # If current user is outside top N, append them at their actual rank
    if current_user_rank and current_user_rank > limit:
        current_entry = next(
            (e for e in ranked if e["uid"] == current_uid), None)
        if current_entry:
            top_entries.append(current_entry)

    return {
        "entries": top_entries,
        "current_user_rank": current_user_rank,
    }


def _uid_to_level_name(user: dict) -> str:
    level = user.get("level", 0)
    level_names = [
        "Seedling",
        "Sprout",
        "Sapling",
        "Grove",
        "Forest",
        "Rainforest",
        "EcoChampion",
    ]
    return level_names[level] if level < len(level_names) else "EcoChampion"
