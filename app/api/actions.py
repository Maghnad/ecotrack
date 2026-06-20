"""
EcoTrack - Eco-Actions, Challenges & AI Insights Router
Quick-log positive actions, view weekly challenges, get AI tips.
"""
from fastapi import APIRouter, Depends, Query
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models.schemas import (
    EcoActionRequest, EcoActionResponse,
    ChallengeListResponse, Challenge,
    InsightResponse, HistoryResponse,
)
from app.services import calculation_service as calc
from app.services import database_service as db
from app.services import gamification_service as gs
from app.services import challenge_service as cs
from app.services import ai_insight_service as ai
from app.services import analytics_service as analytics

router = APIRouter(tags=["Actions, Challenges & Insights"])
settings = get_settings()


# ---------------------------------------------------------------------------
# Eco-Actions
# ---------------------------------------------------------------------------

@router.post("/eco-actions", response_model=EcoActionResponse, status_code=201)
async def log_eco_action(
    request: EcoActionRequest,
    current_user: dict = Depends(get_current_user),
) -> EcoActionResponse:
    """
    Log a positive eco-friendly action (e.g., used a reusable bag, planted a tree).
    Awards XP and contributes to carbon-saving totals and challenges.
    """
    uid = current_user["uid"]
    db.ensure_user_exists(uid, current_user.get("email"))

    action_data = calc.calculate_eco_action_savings(request.action_type, request.quantity)

    log_entry = {
        "log_type": "eco_action",
        "action_type": request.action_type,
        "quantity": request.quantity,
        "carbon_saved_kg": action_data["carbon_saved_kg"],
        "carbon_emissions_kg": 0.0,  # Actions save, not emit
    }
    db.save_footprint_log(uid, log_entry)

    # Record savings toward badges and total profile
    gs.record_carbon_saved(uid, action_data["carbon_saved_kg"])

    # Award XP
    xp_result = gs.award_xp_and_update_streak(uid, settings.xp_per_footprint_log)

    # Check challenges
    cs.check_and_award_challenge_completion(uid)

    return EcoActionResponse(
        action_type=request.action_type,
        carbon_saved_kg=action_data["carbon_saved_kg"],
        xp_awarded=xp_result["xp_awarded"],
        new_total_xp=xp_result["new_total_xp"],
        fun_fact=action_data["fun_fact"],
    )


# ---------------------------------------------------------------------------
# Challenges
# ---------------------------------------------------------------------------

@router.get("/challenges", response_model=ChallengeListResponse)
async def get_challenges(
    current_user: dict = Depends(get_current_user),
) -> ChallengeListResponse:
    """
    Returns this week's active challenges and the user's progress on each.
    Challenges reset every Monday and are the same for all users.
    """
    uid = current_user["uid"]
    db.ensure_user_exists(uid, current_user.get("email"))
    status_data = cs.get_user_challenge_status(uid)
    return ChallengeListResponse(**status_data)


# ---------------------------------------------------------------------------
# AI Insights
# ---------------------------------------------------------------------------

@router.get("/insights", response_model=InsightResponse)
async def get_ai_insights(
    current_user: dict = Depends(get_current_user),
) -> InsightResponse:
    """
    Returns personalised AI-generated reduction tips based on the user's
    recent 14-day activity, powered by Google Gemini 1.5 Flash.
    """
    uid = current_user["uid"]
    db.ensure_user_exists(uid, current_user.get("email"))
    recent_logs = db.get_user_logs(uid, days=14)
    insight_data = ai.generate_ai_insights(uid, recent_logs)
    return InsightResponse(**insight_data)


# ---------------------------------------------------------------------------
# History & Analytics
# ---------------------------------------------------------------------------

@router.get("/history", response_model=HistoryResponse)
async def get_emissions_history(
    days: int = Query(default=30, ge=7, le=365, description="Number of days of history to retrieve."),
    current_user: dict = Depends(get_current_user),
) -> HistoryResponse:
    """
    Returns a daily breakdown of the user's emissions over the specified
    period, split by category (transport, diet, energy). Also provides a
    comparison to the global per-capita average.
    """
    uid = current_user["uid"]
    db.ensure_user_exists(uid, current_user.get("email"))
    return analytics.get_emissions_history(uid, days=days)
