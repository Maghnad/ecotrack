"""
EcoTrack - User & Gamification Router
Profile, leaderboard, XP, badges, and streaks.
"""
from fastapi import APIRouter, Depends, Query
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models.schemas import UserProfile, Badge, LeaderboardResponse, LeaderboardEntry
from app.services import database_service as db
from app.services import analytics_service as analytics

router = APIRouter(prefix="/users", tags=["Users & Gamification"])
settings = get_settings()


@router.get("/me", response_model=UserProfile)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
) -> UserProfile:
    """
    Returns the current user's full profile including XP, level,
    streak, badges, and cumulative carbon savings.
    """
    uid = current_user["uid"]
    profile = db.ensure_user_exists(uid, current_user.get("email"))

    level = profile.get("level", 0)
    thresholds = settings.level_thresholds
    level_names = settings.level_names

    xp_to_next = 0
    total_xp = profile.get("total_xp", 0)
    for threshold in thresholds:
        if total_xp < threshold:
            xp_to_next = threshold - total_xp
            break

    raw_badges = profile.get("badges", [])
    badges = [
        Badge(
            badge_id=b["badge_id"],
            name=b["name"],
            description=b["description"],
            icon_emoji=b["icon_emoji"],
            earned_at=b.get("earned_at"),
        )
        for b in raw_badges
    ]

    return UserProfile(
        uid=uid,
        email=profile.get("email"),
        display_name=profile.get("display_name"),
        total_xp=total_xp,
        level=level,
        level_name=level_names[level] if level < len(level_names) else "EcoChampion",
        xp_to_next_level=xp_to_next,
        streak_days=profile.get("streak_days", 0),
        longest_streak=profile.get("longest_streak", 0),
        total_carbon_saved_kg=profile.get("total_carbon_saved_kg", 0.0),
        badges=badges,
        created_at=profile.get("created_at"),
    )


@router.patch("/me/display-name")
async def update_display_name(
    display_name: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Update the user's display name (shown on leaderboard)."""
    uid = current_user["uid"]
    db.ensure_user_exists(uid, current_user.get("email"))
    db.upsert_user_profile(uid, {"display_name": display_name})
    return {"message": f"Display name updated to '{display_name}'."}


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    limit: int = Query(default=10, ge=1, le=50, description="Number of top users to return."),
    current_user: dict = Depends(get_current_user),
) -> LeaderboardResponse:
    """
    Returns the global XP leaderboard. Current user's rank is always included
    even if they fall outside the top N.
    """
    uid = current_user["uid"]
    leaderboard_data = analytics.get_leaderboard_with_user_rank(uid, limit=limit)

    entries = [
        LeaderboardEntry(
            rank=e["rank"],
            uid=e["uid"],
            display_name=e["display_name"],
            total_xp=e["total_xp"],
            level_name=e["level_name"],
            total_carbon_saved_kg=e["total_carbon_saved_kg"],
        )
        for e in leaderboard_data["entries"]
    ]

    return LeaderboardResponse(
        entries=entries,
        current_user_rank=leaderboard_data.get("current_user_rank"),
    )
