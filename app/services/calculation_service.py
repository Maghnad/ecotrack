"""
EcoTrack - Carbon Calculation Service
Single place for all emission factor math.
Sources: IPCC AR6, EPA, UK DEFRA 2023.
"""
from __future__ import annotations
from app.core.config import get_settings
from app.core.secrets import get_secret

settings = get_settings()

# ---------------------------------------------------------------------------
# Emission factors (kg CO₂e per unit)
# ---------------------------------------------------------------------------

# Transport: kg CO₂ per km per person
TRANSPORT_EMISSION_FACTORS: dict[str, float] = {
    "driving":    0.171,   # Average petrol car, DEFRA 2023
    "transit":    0.089,   # UK average bus
    "bicycling":  0.000,   # Zero operational emissions
    "walking":    0.000,
}

# Diet: kg CO₂e per serving
DIET_EMISSION_FACTORS: dict[str, float] = {
    "beef":        6.61,
    "chicken":     1.26,
    "fish":        1.34,
    "vegetarian":  0.70,
    "vegan":       0.45,
}

# Energy: kg CO₂ per unit
ELECTRICITY_KG_PER_KWH = 0.233   # UK Grid average 2023
NATURAL_GAS_KG_PER_CUBIC_METER = 2.04

# Eco actions: kg CO₂ saved per unit
ECO_ACTION_SAVINGS: dict[str, float] = {
    "used_reusable_bag":      0.033,
    "planted_tree":           21.77,   # kg CO₂ absorbed per year ÷ 12 months averaged per action
    "avoided_meat":           1.50,    # vs beef alternative
    "used_public_transport":  2.61,    # vs solo car trip avg 15 km
    "reduced_heating":        0.86,    # 1°C reduction for 8h, avg home
    "air_dried_laundry":      0.75,
}

ECO_ACTION_FUN_FACTS: dict[str, str] = {
    "used_reusable_bag":      "A cotton tote needs to be reused ~131 times to break even vs a plastic bag—you're on your way! 🌱",
    "planted_tree":           "A single mature tree absorbs up to 22 kg of CO₂ per year. You just started a new one! 🌳",
    "avoided_meat":           "Switching from beef to a plant meal just once saves more CO₂ than driving your car 15 km. 🥗",
    "used_public_transport":  "If everyone in your city commuted by bus today, CO₂ emissions would drop by millions of tonnes. 🚌",
    "reduced_heating":        "Lowering your thermostat by 1°C can cut your heating bill—and emissions—by up to 10%. ❄️",
    "air_dried_laundry":      "Tumble dryers are the 3rd biggest household energy user. Line-drying is the oldest eco-hack. ☀️",
}


def calculate_commute_emissions(
    origin_address: str,
    destination_address: str,
    transport_mode: str,
) -> dict:
    """
    Call Google Maps Distance Matrix API (or mock in testing) to get
    the route distance, then compute kg CO₂ for the given mode.
    Returns a dict with distance_km and carbon_emissions_kg.
    """
    distance_km = _get_distance_km(origin_address, destination_address, transport_mode)
    emission_factor = TRANSPORT_EMISSION_FACTORS.get(transport_mode, 0.0)
    carbon_emissions_kg = round(distance_km * emission_factor, 4)
    return {
        "distance_km": round(distance_km, 2),
        "carbon_emissions_kg": carbon_emissions_kg,
    }


def calculate_diet_emissions(meal_type: str, servings: float) -> float:
    """Returns kg CO₂e for a dietary log entry."""
    factor = DIET_EMISSION_FACTORS.get(meal_type, 0.0)
    return round(factor * servings, 4)


def calculate_energy_emissions(
    electricity_kwh: float,
    natural_gas_cubic_meters: float,
) -> dict:
    """Returns a breakdown of electricity and gas CO₂ emissions."""
    electricity_kg = round(electricity_kwh * ELECTRICITY_KG_PER_KWH, 4)
    gas_kg = round(natural_gas_cubic_meters * NATURAL_GAS_KG_PER_CUBIC_METER, 4)
    return {
        "electricity_kg_co2": electricity_kg,
        "gas_kg_co2": gas_kg,
        "carbon_emissions_kg": round(electricity_kg + gas_kg, 4),
    }


def calculate_eco_action_savings(action_type: str, quantity: int) -> dict:
    """Returns kg CO₂ saved and a fun fact for a positive eco-action."""
    saving_per_unit = ECO_ACTION_SAVINGS.get(action_type, 0.0)
    total_saved = round(saving_per_unit * quantity, 4)
    fun_fact = ECO_ACTION_FUN_FACTS.get(action_type, "Every action counts! 🌍")
    return {"carbon_saved_kg": total_saved, "fun_fact": fun_fact}


def emissions_to_driving_equivalent_km(carbon_kg: float) -> float:
    """Converts any kg CO₂ value to equivalent km driven in an average petrol car."""
    if TRANSPORT_EMISSION_FACTORS["driving"] == 0:
        return 0.0
    return round(carbon_kg / TRANSPORT_EMISSION_FACTORS["driving"], 1)


# ---------------------------------------------------------------------------
# Internal: Maps API or mock
# ---------------------------------------------------------------------------

def _get_distance_km(origin: str, destination: str, mode: str) -> float:
    """
    Calls Google Maps Distance Matrix API.
    Returns a deterministic mock distance in testing mode.
    """
    if settings.environment == "testing" or settings.google_maps_api_key == "mock_key":
        return _mock_distance(origin, destination)

    import googlemaps
    api_key = get_secret("google_maps_api_key")
    gmaps = googlemaps.Client(key=api_key)
    result = gmaps.distance_matrix(
        origins=[origin],
        destinations=[destination],
        mode=mode,
        units="metric",
    )
    element = result["rows"][0]["elements"][0]
    if element["status"] != "OK":
        raise ValueError(f"Maps API returned status: {element['status']}")
    distance_meters = element["distance"]["value"]
    return distance_meters / 1000.0


def _mock_distance(origin: str, destination: str) -> float:
    """
    Deterministic mock: returns a distance based on address string length
    so tests are repeatable without a live API key.
    """
    combined_length = len(origin) + len(destination)
    return round((combined_length % 30) + 3.5, 2)
