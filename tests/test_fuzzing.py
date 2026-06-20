from hypothesis import given, strategies as st
from app.services import calculation_service as calc


@given(
    servings=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    meal_type=st.sampled_from(["beef", "chicken", "fish", "vegetarian", "vegan"])
)
def test_fuzz_calculate_diet(servings: float, meal_type: str):
    # Fuzzing calculate_diet_emissions to ensure it never crashes on valid floats
    try:
        carbon = calc.calculate_diet_emissions(meal_type, servings)
        assert isinstance(carbon, float)
        assert carbon >= 0.0
    except ValueError:
        pass


@given(
    carbon_kg=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
)
def test_fuzz_emissions_to_driving_equivalent(carbon_kg: float):
    # Fuzzing reverse distance calculation
    distance = calc.emissions_to_driving_equivalent_km(carbon_kg)
    assert isinstance(distance, float)
    assert distance >= 0.0


@given(
    address=st.text(max_size=500)
)
def test_fuzz_sanitise_address(address: str):
    # Ensure sanitisation never crashes and always returns <= 100 chars
    safe = calc._sanitise_address(address)
    assert len(safe) <= 100
    assert isinstance(safe, str)
