"""
EcoTrack - Test Suite
Tests core calculations, API endpoints, gamification logic, and challenge tracking.
All tests run without any live Google API keys using the mock environment.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import database_service as db
from app.services import calculation_service as calc
from app.services import gamification_service as gs
from app.services import challenge_service as cs
from app.services import analytics_service as analytics

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer mock_token"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_mock_db():
    """Reset the in-memory mock DB before every test to ensure isolation."""
    db._MOCK_DB.clear()
    yield
    db._MOCK_DB.clear()


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "2.0.0"


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TestAuthentication:
    def test_protected_route_without_token_returns_401(self):
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_protected_route_with_invalid_token_returns_401(self):
        response = client.get("/users/me", headers={"Authorization": "Bearer bad_token"})
        assert response.status_code == 401

    def test_mock_token_accepted_in_testing_environment(self):
        response = client.get("/users/me", headers=AUTH_HEADERS)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Carbon Calculation Service (unit tests — no HTTP)
# ---------------------------------------------------------------------------

class TestCalculationService:
    def test_driving_commute_emits_correct_co2(self):
        result = calc.calculate_commute_emissions("London", "Oxford", "driving")
        # Mock distance: len("London") + len("Oxford") = 12 → (12 % 30) + 3.5 = 15.5 km
        expected_kg = round(15.5 * calc.TRANSPORT_EMISSION_FACTORS["driving"], 4)
        assert result["carbon_emissions_kg"] == expected_kg
        assert result["distance_km"] == 15.5

    def test_cycling_commute_has_zero_emissions(self):
        result = calc.calculate_commute_emissions("A Street", "B Street", "bicycling")
        assert result["carbon_emissions_kg"] == 0.0

    def test_walking_commute_has_zero_emissions(self):
        result = calc.calculate_commute_emissions("Home", "Park", "walking")
        assert result["carbon_emissions_kg"] == 0.0

    def test_diet_beef_emits_correct_co2(self):
        emissions = calc.calculate_diet_emissions("beef", 1.0)
        assert emissions == calc.DIET_EMISSION_FACTORS["beef"]

    def test_diet_vegan_is_lowest_emission(self):
        beef = calc.calculate_diet_emissions("beef", 1.0)
        vegan = calc.calculate_diet_emissions("vegan", 1.0)
        assert vegan < beef

    def test_diet_servings_scale_linearly(self):
        single = calc.calculate_diet_emissions("chicken", 1.0)
        double = calc.calculate_diet_emissions("chicken", 2.0)
        assert round(double, 4) == round(single * 2, 4)

    def test_energy_electricity_calculation(self):
        result = calc.calculate_energy_emissions(electricity_kwh=10.0, natural_gas_cubic_meters=0.0)
        expected = round(10.0 * calc.ELECTRICITY_KG_PER_KWH, 4)
        assert result["electricity_kg_co2"] == expected
        assert result["gas_kg_co2"] == 0.0
        assert result["carbon_emissions_kg"] == expected

    def test_energy_gas_calculation(self):
        result = calc.calculate_energy_emissions(electricity_kwh=0.0, natural_gas_cubic_meters=5.0)
        expected = round(5.0 * calc.NATURAL_GAS_KG_PER_CUBIC_METER, 4)
        assert result["gas_kg_co2"] == expected

    def test_energy_combined_calculation(self):
        result = calc.calculate_energy_emissions(electricity_kwh=10.0, natural_gas_cubic_meters=5.0)
        expected = round(
            10.0 * calc.ELECTRICITY_KG_PER_KWH + 5.0 * calc.NATURAL_GAS_KG_PER_CUBIC_METER, 4
        )
        assert result["carbon_emissions_kg"] == expected

    def test_eco_action_savings_returns_positive_value(self):
        result = calc.calculate_eco_action_savings("planted_tree", 1)
        assert result["carbon_saved_kg"] > 0

    def test_eco_action_scales_with_quantity(self):
        single = calc.calculate_eco_action_savings("used_reusable_bag", 1)
        triple = calc.calculate_eco_action_savings("used_reusable_bag", 3)
        assert round(triple["carbon_saved_kg"], 4) == round(single["carbon_saved_kg"] * 3, 4)

    def test_emissions_to_driving_equivalent(self):
        kg = calc.TRANSPORT_EMISSION_FACTORS["driving"] * 10  # 10 km of driving
        km_equivalent = calc.emissions_to_driving_equivalent_km(kg)
        assert km_equivalent == 10.0

    def test_all_transport_modes_have_emission_factors(self):
        for mode in ("driving", "transit", "bicycling", "walking"):
            assert mode in calc.TRANSPORT_EMISSION_FACTORS


# ---------------------------------------------------------------------------
# Commute Logging API
# ---------------------------------------------------------------------------

class TestCommuteLogging:
    def test_log_driving_commute_returns_201(self):
        response = client.post(
            "/footprint/commute",
            json={
                "origin_address": "10 Downing Street London",
                "destination_address": "Buckingham Palace London",
                "transport_mode": "driving",
            },
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 201

    def test_log_commute_response_structure(self):
        response = client.post(
            "/footprint/commute",
            json={
                "origin_address": "Kings Cross London",
                "destination_address": "Paddington London",
                "transport_mode": "transit",
            },
            headers=AUTH_HEADERS,
        )
        data = response.json()
        assert "log_id" in data
        assert "carbon_emissions_kg" in data
        assert "distance_km" in data
        assert "xp_awarded" in data
        assert "streak_days" in data
        assert "message" in data

    def test_cycling_commute_returns_zero_emissions(self):
        response = client.post(
            "/footprint/commute",
            json={
                "origin_address": "Home",
                "destination_address": "Office",
                "transport_mode": "bicycling",
            },
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 201
        assert response.json()["carbon_emissions_kg"] == 0.0

    def test_log_commute_awards_xp(self):
        response = client.post(
            "/footprint/commute",
            json={
                "origin_address": "A", "destination_address": "B", "transport_mode": "driving"
            },
            headers=AUTH_HEADERS,
        )
        assert response.json()["xp_awarded"] > 0

    def test_invalid_transport_mode_rejected(self):
        response = client.post(
            "/footprint/commute",
            json={
                "origin_address": "A",
                "destination_address": "B",
                "transport_mode": "rocket",
            },
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Diet Logging API
# ---------------------------------------------------------------------------

class TestDietLogging:
    def test_log_beef_meal_returns_201(self):
        response = client.post(
            "/footprint/diet",
            json={"meal_type": "beef", "servings": 1.0},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 201

    def test_diet_log_response_includes_comparison(self):
        response = client.post(
            "/footprint/diet",
            json={"meal_type": "beef", "servings": 1.0},
            headers=AUTH_HEADERS,
        )
        data = response.json()
        assert "comparison" in data
        assert len(data["comparison"]) > 0

    def test_vegan_meal_has_lower_emissions_than_beef(self):
        beef_resp = client.post(
            "/footprint/diet", json={"meal_type": "beef", "servings": 1.0}, headers=AUTH_HEADERS
        )
        vegan_resp = client.post(
            "/footprint/diet", json={"meal_type": "vegan", "servings": 1.0}, headers=AUTH_HEADERS
        )
        assert vegan_resp.json()["carbon_emissions_kg"] < beef_resp.json()["carbon_emissions_kg"]

    def test_invalid_meal_type_rejected(self):
        response = client.post(
            "/footprint/diet",
            json={"meal_type": "pizza", "servings": 1.0},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 422

    def test_servings_too_high_rejected(self):
        response = client.post(
            "/footprint/diet",
            json={"meal_type": "chicken", "servings": 999.0},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Energy Logging API
# ---------------------------------------------------------------------------

class TestEnergyLogging:
    def test_log_energy_returns_201(self):
        response = client.post(
            "/footprint/energy",
            json={"electricity_kwh": 15.0, "natural_gas_cubic_meters": 3.0},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 201

    def test_energy_response_breaks_down_sources(self):
        response = client.post(
            "/footprint/energy",
            json={"electricity_kwh": 10.0, "natural_gas_cubic_meters": 5.0},
            headers=AUTH_HEADERS,
        )
        data = response.json()
        assert "electricity_kg_co2" in data
        assert "gas_kg_co2" in data
        assert "carbon_emissions_kg" in data

    def test_total_equals_sum_of_parts(self):
        response = client.post(
            "/footprint/energy",
            json={"electricity_kwh": 10.0, "natural_gas_cubic_meters": 5.0},
            headers=AUTH_HEADERS,
        )
        data = response.json()
        expected_total = round(data["electricity_kg_co2"] + data["gas_kg_co2"], 4)
        assert round(data["carbon_emissions_kg"], 4) == expected_total

    def test_negative_energy_values_rejected(self):
        response = client.post(
            "/footprint/energy",
            json={"electricity_kwh": -5.0, "natural_gas_cubic_meters": 0.0},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Eco-Actions API
# ---------------------------------------------------------------------------

class TestEcoActions:
    def test_log_eco_action_returns_201(self):
        response = client.post(
            "/eco-actions",
            json={"action_type": "used_reusable_bag", "quantity": 1},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 201

    def test_eco_action_returns_fun_fact(self):
        response = client.post(
            "/eco-actions",
            json={"action_type": "planted_tree", "quantity": 1},
            headers=AUTH_HEADERS,
        )
        data = response.json()
        assert "fun_fact" in data
        assert len(data["fun_fact"]) > 10

    def test_eco_action_returns_carbon_saved(self):
        response = client.post(
            "/eco-actions",
            json={"action_type": "planted_tree", "quantity": 1},
            headers=AUTH_HEADERS,
        )
        assert response.json()["carbon_saved_kg"] > 0

    def test_eco_action_quantity_scales_savings(self):
        r1 = client.post(
            "/eco-actions",
            json={"action_type": "used_reusable_bag", "quantity": 1},
            headers=AUTH_HEADERS,
        )
        db._MOCK_DB.clear()
        r3 = client.post(
            "/eco-actions",
            json={"action_type": "used_reusable_bag", "quantity": 3},
            headers=AUTH_HEADERS,
        )
        assert round(r3.json()["carbon_saved_kg"], 4) == round(r1.json()["carbon_saved_kg"] * 3, 4)

    def test_invalid_action_type_rejected(self):
        response = client.post(
            "/eco-actions",
            json={"action_type": "ate_a_sandwich", "quantity": 1},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# User Profile API
# ---------------------------------------------------------------------------

class TestUserProfile:
    def test_get_profile_returns_200(self):
        response = client.get("/users/me", headers=AUTH_HEADERS)
        assert response.status_code == 200

    def test_new_user_starts_at_zero_xp(self):
        response = client.get("/users/me", headers=AUTH_HEADERS)
        data = response.json()
        assert data["total_xp"] == 0
        assert data["streak_days"] == 0
        assert data["level"] == 0

    def test_profile_includes_level_name(self):
        response = client.get("/users/me", headers=AUTH_HEADERS)
        data = response.json()
        assert "level_name" in data
        assert data["level_name"] == "Seedling"

    def test_profile_includes_badges_list(self):
        response = client.get("/users/me", headers=AUTH_HEADERS)
        assert "badges" in response.json()

    def test_logging_increases_xp_on_profile(self):
        client.post(
            "/footprint/commute",
            json={"origin_address": "A", "destination_address": "B", "transport_mode": "driving"},
            headers=AUTH_HEADERS,
        )
        profile = client.get("/users/me", headers=AUTH_HEADERS).json()
        assert profile["total_xp"] > 0

    def test_update_display_name(self):
        response = client.patch(
            "/users/me/display-name?display_name=GreenHero",
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200
        assert "GreenHero" in response.json()["message"]


# ---------------------------------------------------------------------------
# Gamification Service (unit tests)
# ---------------------------------------------------------------------------

class TestGamificationService:
    def test_xp_award_increases_total(self):
        db.ensure_user_exists("test_uid", "test@test.com")
        result = gs.award_xp_and_update_streak("test_uid", 20)
        assert result["new_total_xp"] == 20

    def test_multiple_xp_awards_accumulate(self):
        db.ensure_user_exists("test_uid", "test@test.com")
        gs.award_xp_and_update_streak("test_uid", 10)
        result = gs.award_xp_and_update_streak("test_uid", 15)
        assert result["new_total_xp"] == 25

    def test_level_advances_at_threshold(self):
        db.ensure_user_exists("test_uid", "test@test.com")
        # Level 1 threshold is 100 XP
        result = gs.award_xp_and_update_streak("test_uid", 100)
        assert result["level"] >= 1

    def test_badge_earned_on_first_log(self):
        db.ensure_user_exists("test_uid", "test@test.com")
        # Simulate first log
        db.upsert_user_profile("test_uid", {"log_count": 0})
        gs.award_xp_and_update_streak("test_uid", 10)
        profile = db.get_user_profile("test_uid")
        badge_ids = [b["badge_id"] for b in profile.get("badges", [])]
        assert "first_log" in badge_ids

    def test_zero_commute_badge_awarded_for_cycling(self):
        db.ensure_user_exists("test_uid", "test@test.com")
        gs.check_zero_commute_badge("test_uid", "bicycling")
        profile = db.get_user_profile("test_uid")
        badge_ids = [b["badge_id"] for b in profile.get("badges", [])]
        assert "zero_commute" in badge_ids

    def test_zero_commute_badge_not_awarded_for_driving(self):
        db.ensure_user_exists("test_uid", "test@test.com")
        gs.check_zero_commute_badge("test_uid", "driving")
        profile = db.get_user_profile("test_uid")
        badge_ids = [b["badge_id"] for b in profile.get("badges", [])]
        assert "zero_commute" not in badge_ids

    def test_carbon_saved_accumulates(self):
        db.ensure_user_exists("test_uid", "test@test.com")
        gs.record_carbon_saved("test_uid", 5.0)
        gs.record_carbon_saved("test_uid", 3.5)
        profile = db.get_user_profile("test_uid")
        assert profile["total_carbon_saved_kg"] == 8.5


# ---------------------------------------------------------------------------
# Challenges
# ---------------------------------------------------------------------------

class TestChallenges:
    def test_challenges_endpoint_returns_200(self):
        response = client.get("/challenges", headers=AUTH_HEADERS)
        assert response.status_code == 200

    def test_challenges_response_has_expected_structure(self):
        response = client.get("/challenges", headers=AUTH_HEADERS)
        data = response.json()
        assert "active_challenges" in data
        assert "completed_challenges" in data

    def test_exactly_three_challenges_this_week(self):
        challenges = cs.get_current_week_challenges()
        assert len(challenges) == 3

    def test_challenges_have_required_fields(self):
        challenges = cs.get_current_week_challenges()
        for challenge in challenges:
            assert "challenge_id" in challenge
            assert "title" in challenge
            assert "xp_reward" in challenge
            assert "deadline_date" in challenge

    def test_challenges_are_consistent_within_week(self):
        """Same week should always return same challenges (deterministic rotation)."""
        first_call = cs.get_current_week_challenges()
        second_call = cs.get_current_week_challenges()
        assert [c["challenge_id"] for c in first_call] == [c["challenge_id"] for c in second_call]

    def test_plant_based_meals_progress_counts_vegetarian_and_vegan(self):
        # Log a vegetarian meal
        client.post(
            "/footprint/diet",
            json={"meal_type": "vegetarian", "servings": 1.0},
            headers=AUTH_HEADERS,
        )
        # Check challenge progress uses logs
        uid = "mock_user_123"
        logs = db.get_user_logs(uid, days=7)
        from app.services.challenge_service import _calculate_progress_from_logs
        progress = _calculate_progress_from_logs(logs)
        assert progress["plant_based_meal_count"] >= 1


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

class TestAnalytics:
    def test_history_returns_200(self):
        response = client.get("/history", headers=AUTH_HEADERS)
        assert response.status_code == 200

    def test_history_response_structure(self):
        response = client.get("/history", headers=AUTH_HEADERS)
        data = response.json()
        assert "daily_emissions" in data
        assert "period_total_kg" in data
        assert "period_average_daily_kg" in data
        assert "comparison_to_global_average_percent" in data

    def test_history_default_period_is_30_days(self):
        response = client.get("/history", headers=AUTH_HEADERS)
        data = response.json()
        assert len(data["daily_emissions"]) == 30

    def test_history_custom_period(self):
        response = client.get("/history?days=7", headers=AUTH_HEADERS)
        data = response.json()
        assert len(data["daily_emissions"]) == 7

    def test_empty_history_totals_zero(self):
        response = client.get("/history", headers=AUTH_HEADERS)
        data = response.json()
        assert data["period_total_kg"] == 0.0

    def test_logged_commute_appears_in_history(self):
        client.post(
            "/footprint/commute",
            json={"origin_address": "A", "destination_address": "B", "transport_mode": "driving"},
            headers=AUTH_HEADERS,
        )
        response = client.get("/history?days=7", headers=AUTH_HEADERS)
        data = response.json()
        assert data["period_total_kg"] > 0

    def test_leaderboard_returns_200(self):
        response = client.get("/users/leaderboard", headers=AUTH_HEADERS)
        assert response.status_code == 200

    def test_leaderboard_has_entries_field(self):
        response = client.get("/users/leaderboard", headers=AUTH_HEADERS)
        data = response.json()
        assert "entries" in data
        assert "current_user_rank" in data


# ---------------------------------------------------------------------------
# AI Insights
# ---------------------------------------------------------------------------

class TestAIInsights:
    def test_insights_returns_200(self):
        response = client.get("/insights", headers=AUTH_HEADERS)
        assert response.status_code == 200

    def test_insights_response_structure(self):
        response = client.get("/insights", headers=AUTH_HEADERS)
        data = response.json()
        assert "tips" in data
        assert "weekly_summary" in data
        assert "biggest_emission_source" in data
        assert "potential_savings_kg" in data
        assert "generated_at" in data

    def test_insights_tips_is_a_list(self):
        response = client.get("/insights", headers=AUTH_HEADERS)
        assert isinstance(response.json()["tips"], list)
