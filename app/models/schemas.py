"""
EcoTrack - Pydantic Schemas
Single source of truth for all request/response shapes.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Footprint Logging
# ---------------------------------------------------------------------------


class CommuteLogRequest(BaseModel):
    """A single commute entry to log and calculate emissions for."""

    origin_address: str = Field(..., max_length=200,
                                description="Starting point of the commute.")
    destination_address: str = Field(..., max_length=200,
                                     description="End point of the commute.")
    transport_mode: Literal["driving", "transit", "bicycling", "walking", "flight"] = Field(
        ..., description="Mode of transport used for this commute."
    )
    date: Optional[str] = Field(
        None, description="ISO date string (YYYY-MM-DD). Defaults to today."
    )


class CommuteLogResponse(BaseModel):
    log_id: str
    distance_km: float
    carbon_emissions_kg: float
    transport_mode: str
    xp_awarded: int
    new_total_xp: int
    streak_days: int
    message: str


# ---------------------------------------------------------------------------
# Activity Categories (new: diet, energy, shopping)
# ---------------------------------------------------------------------------


class DietLogRequest(BaseModel):
    """Log dietary choices to estimate food-related carbon footprint."""

    meal_type: Literal["beef", "chicken", "fish", "vegetarian", "vegan"] = Field(
        ..., description="Primary protein category of the meal."
    )
    servings: float = Field(
        1.0, ge=0.1, le=10.0, description="Number of servings (portions)."
    )
    date: Optional[str] = None


class DietLogResponse(BaseModel):
    log_id: str
    meal_type: str
    carbon_emissions_kg: float
    xp_awarded: int
    new_total_xp: int
    comparison: str  # e.g. "Equivalent to driving 3.2 km"


class EnergyLogRequest(BaseModel):
    """Log home energy consumption."""

    electricity_kwh: float = Field(
        0.0, ge=0.0, description="Electricity consumed in kWh."
    )
    natural_gas_cubic_meters: float = Field(
        0.0, ge=0.0, description="Natural gas in cubic metres."
    )
    date: Optional[str] = None


class EnergyLogResponse(BaseModel):
    log_id: str
    carbon_emissions_kg: float
    electricity_kg_co2: float
    gas_kg_co2: float
    xp_awarded: int
    new_total_xp: int


# ---------------------------------------------------------------------------
# User Profile & Gamification
# ---------------------------------------------------------------------------


class UserProfile(BaseModel):
    uid: str
    email: Optional[str]
    display_name: Optional[str]
    total_xp: int
    level: int
    level_name: str
    xp_to_next_level: int
    streak_days: int
    longest_streak: int
    total_carbon_saved_kg: float
    badges: list[Badge]
    created_at: Optional[str]


class Badge(BaseModel):
    badge_id: str
    name: str
    description: str
    icon_emoji: str
    earned_at: Optional[str] = None


class LeaderboardEntry(BaseModel):
    rank: int
    uid: str
    display_name: str
    total_xp: int
    level_name: str
    total_carbon_saved_kg: float


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]
    current_user_rank: Optional[int]


# ---------------------------------------------------------------------------
# Challenges
# ---------------------------------------------------------------------------


class Challenge(BaseModel):
    challenge_id: str
    title: str
    description: str
    icon_emoji: str
    target_metric: str  # e.g. "carbon_emissions_kg"
    target_value: float
    xp_reward: int
    deadline_date: str
    is_completed: bool = False
    progress_value: float = 0.0
    progress_percent: float = 0.0


class ChallengeListResponse(BaseModel):
    active_challenges: list[Challenge]
    completed_challenges: list[Challenge]


# ---------------------------------------------------------------------------
# AI Insights
# ---------------------------------------------------------------------------


class InsightResponse(BaseModel):
    tips: list[str]
    weekly_summary: str
    biggest_emission_source: str
    potential_savings_kg: float
    generated_at: str


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's natural language message to the AI chatbot.")


class ChatResponse(BaseModel):
    reply: str
    carbon_emissions_kg: float
    message: str


class BaselineRequest(BaseModel):
    diet_type: Literal["vegan", "vegetarian", "pescatarian", "meat_average", "meat_heavy"]
    commute_method: Literal["driving", "transit", "cycling", "walking", "remote"]
    home_energy: Literal["renewable", "grid_average", "coal_heavy"]


class BaselineResponse(BaseModel):
    baseline_yearly_kg: float
    message: str
    xp_awarded: int
    new_total_xp: int


# ---------------------------------------------------------------------------
# Carbon History & Analytics
# ---------------------------------------------------------------------------


class DailyEmission(BaseModel):
    date: str
    transport_kg: float
    diet_kg: float
    energy_kg: float
    total_kg: float


class HistoryResponse(BaseModel):
    daily_emissions: list[DailyEmission]
    period_total_kg: float
    period_average_daily_kg: float
    comparison_to_global_average_percent: float  # vs 16.1 kg/day global avg


# ---------------------------------------------------------------------------
# Eco Actions (quick-log positive actions)
# ---------------------------------------------------------------------------


class EcoActionRequest(BaseModel):
    action_type: Literal[
        "used_reusable_bag",
        "planted_tree",
        "avoided_meat",
        "used_public_transport",
        "reduced_heating",
        "air_dried_laundry",
    ]
    quantity: int = Field(1, ge=1, le=100)


class EcoActionResponse(BaseModel):
    action_type: str
    carbon_saved_kg: float
    xp_awarded: int
    new_total_xp: int
    fun_fact: str


# ---------------------------------------------------------------------------
# Social / Friends
# ---------------------------------------------------------------------------


class FriendInviteRequest(BaseModel):
    friend_email: str = Field(..., max_length=200, description="Email of the friend to invite.")


class FriendComparisonResponse(BaseModel):
    your_weekly_kg: float
    friend_weekly_kg: float
    friend_display_name: str
    you_are_better_by_kg: float  # negative means friend is greener
    message: str
