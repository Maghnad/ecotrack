"""
EcoTrack - Application Configuration
Loads and validates all environment variables using pydantic-settings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    project_id: str = "ecotrack-default-project"
    environment: str = "testing"
    google_maps_api_key: str = "mock_key"
    gemini_api_key: str = "mock_key"

    # --- Gamification Config ---
    # XP awarded per action
    xp_per_footprint_log: int = 10
    xp_per_tip_viewed: int = 2
    xp_per_challenge_completed: int = 50
    xp_per_streak_day: int = 5
    # Level thresholds
    level_thresholds: list[int] = [0, 100, 250, 500, 1000, 2000, 5000]
    level_names: list[str] = ["Seedling", "Sprout", "Sapling", "Grove", "Forest", "Rainforest", "EcoChampion"]

    # --- Challenge Config ---
    weekly_challenge_day: int = 0  # 0 = Monday

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
