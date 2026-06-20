"""
EcoTrack - Footprint Logging Router
Handles commute, diet, and energy emission logging.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models.schemas import (
    CommuteLogRequest, CommuteLogResponse,
    DietLogRequest, DietLogResponse,
    EnergyLogRequest, EnergyLogResponse,
)
from app.services import calculation_service as calc
from app.services import database_service as db
from app.services import gamification_service as gs
from app.services import challenge_service as cs

router = APIRouter(prefix="/footprint", tags=["Footprint Logging"])
settings = get_settings()


@router.post("/commute", response_model=CommuteLogResponse, status_code=status.HTTP_201_CREATED)
async def log_commute(
    request: CommuteLogRequest,
    current_user: dict = Depends(get_current_user),
) -> CommuteLogResponse:
    """
    Log a commute journey. Calls Google Maps Distance Matrix to get the route
    distance, calculates CO₂ emissions, then awards XP and updates the streak.
    """
    uid = current_user["uid"]
    db.ensure_user_exists(uid, current_user.get("email"))

    try:
        emission_data = calc.calculate_commute_emissions(
            origin_address=request.origin_address,
            destination_address=request.destination_address,
            transport_mode=request.transport_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    log_entry = {
        "log_type": "commute",
        "origin_address": request.origin_address,
        "destination_address": request.destination_address,
        "transport_mode": request.transport_mode,
        "distance_km": emission_data["distance_km"],
        "carbon_emissions_kg": emission_data["carbon_emissions_kg"],
        "date": request.date,
    }
    log_id = db.save_footprint_log(uid, log_entry)

    # Award XP and update streak
    xp_result = gs.award_xp_and_update_streak(uid, settings.xp_per_footprint_log)

    # Check for zero-emission commuter badge
    gs.check_zero_commute_badge(uid, request.transport_mode)

    # Check challenge completions
    cs.check_and_award_challenge_completion(uid)

    # Build a motivational message
    message = _build_commute_message(emission_data["carbon_emissions_kg"], request.transport_mode)

    return CommuteLogResponse(
        log_id=log_id,
        distance_km=emission_data["distance_km"],
        carbon_emissions_kg=emission_data["carbon_emissions_kg"],
        transport_mode=request.transport_mode,
        xp_awarded=xp_result["xp_awarded"],
        new_total_xp=xp_result["new_total_xp"],
        streak_days=xp_result["streak_days"],
        message=message,
    )


@router.post("/diet", response_model=DietLogResponse, status_code=status.HTTP_201_CREATED)
async def log_diet(
    request: DietLogRequest,
    current_user: dict = Depends(get_current_user),
) -> DietLogResponse:
    """
    Log a meal to estimate its dietary carbon footprint.
    Provides a relatable comparison (e.g., equivalent km driven).
    """
    uid = current_user["uid"]
    db.ensure_user_exists(uid, current_user.get("email"))

    carbon_emissions_kg = calc.calculate_diet_emissions(request.meal_type, request.servings)
    driving_equivalent = calc.emissions_to_driving_equivalent_km(carbon_emissions_kg)

    log_entry = {
        "log_type": "diet",
        "meal_type": request.meal_type,
        "servings": request.servings,
        "carbon_emissions_kg": carbon_emissions_kg,
        "date": request.date,
    }
    log_id = db.save_footprint_log(uid, log_entry)

    xp_result = gs.award_xp_and_update_streak(uid, settings.xp_per_footprint_log)
    cs.check_and_award_challenge_completion(uid)

    comparison = (
        f"That's equivalent to driving approximately {driving_equivalent} km 🚗"
        if driving_equivalent > 0.5
        else "Excellent choice — very low carbon impact! 🌿"
    )

    return DietLogResponse(
        log_id=log_id,
        meal_type=request.meal_type,
        carbon_emissions_kg=carbon_emissions_kg,
        xp_awarded=xp_result["xp_awarded"],
        new_total_xp=xp_result["new_total_xp"],
        comparison=comparison,
    )


@router.post("/energy", response_model=EnergyLogResponse, status_code=status.HTTP_201_CREATED)
async def log_energy(
    request: EnergyLogRequest,
    current_user: dict = Depends(get_current_user),
) -> EnergyLogResponse:
    """
    Log home energy usage (electricity and/or natural gas).
    Breaks down the CO₂ contribution of each energy type.
    """
    uid = current_user["uid"]
    db.ensure_user_exists(uid, current_user.get("email"))

    energy_data = calc.calculate_energy_emissions(
        electricity_kwh=request.electricity_kwh,
        natural_gas_cubic_meters=request.natural_gas_cubic_meters,
    )

    log_entry = {
        "log_type": "energy",
        "electricity_kwh": request.electricity_kwh,
        "natural_gas_cubic_meters": request.natural_gas_cubic_meters,
        **energy_data,
        "date": request.date,
    }
    log_id = db.save_footprint_log(uid, log_entry)

    xp_result = gs.award_xp_and_update_streak(uid, settings.xp_per_footprint_log)
    cs.check_and_award_challenge_completion(uid)

    return EnergyLogResponse(
        log_id=log_id,
        carbon_emissions_kg=energy_data["carbon_emissions_kg"],
        electricity_kg_co2=energy_data["electricity_kg_co2"],
        gas_kg_co2=energy_data["gas_kg_co2"],
        xp_awarded=xp_result["xp_awarded"],
        new_total_xp=xp_result["new_total_xp"],
    )


def _build_commute_message(carbon_kg: float, mode: str) -> str:
    if mode in ("bicycling", "walking"):
        return "Zero emissions! 🚴 That's the gold standard — great work."
    if mode == "transit":
        return f"Smart choice! Public transport emitted just {carbon_kg:.2f} kg CO₂ — much better than driving solo. 🌿"
    if carbon_kg < 1.0:
        return f"Short trip with just {carbon_kg:.2f} kg CO₂ logged. Every bit counts! 💚"
    return f"Logged {carbon_kg:.2f} kg CO₂. Consider transit or carpooling next time to cut this in half. 🌍"
