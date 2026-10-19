"""
ai/forecasting/locations.py
===========================
Single source of truth for the dataset's city -> state / district mapping.

The source dataset (``Dataset/crime_dataset_india.csv``) records incidents by
city.  The trained GRU exposes one forecasting scope per city.  This module maps
each of those scopes to the Indian state and administrative district used by the
district-level risk API.

Only cities present in the dataset are listed.  The API filters this catalog
against the scopes actually available in the loaded model, so the dropdowns can
never offer a location the model cannot serve.
"""

from __future__ import annotations

from typing import Any, Iterable

# Verified against the 29 distinct ``City`` values in the source CSV.
CITY_GEO: dict[str, dict[str, Any]] = {
    "Mumbai": {"state": "Maharashtra", "district": "Mumbai", "lat": 19.0760, "lon": 72.8777, "zip": "400"},
    "Delhi": {"state": "Delhi", "district": "New Delhi", "lat": 28.6139, "lon": 77.2090, "zip": "110"},
    "Bangalore": {"state": "Karnataka", "district": "Bangalore Urban", "lat": 12.9716, "lon": 77.5946, "zip": "560"},
    "Hyderabad": {"state": "Telangana", "district": "Hyderabad", "lat": 17.3850, "lon": 78.4867, "zip": "500"},
    "Chennai": {"state": "Tamil Nadu", "district": "Chennai", "lat": 13.0827, "lon": 80.2707, "zip": "600"},
    "Kolkata": {"state": "West Bengal", "district": "Kolkata", "lat": 22.5726, "lon": 88.3639, "zip": "700"},
    "Pune": {"state": "Maharashtra", "district": "Pune", "lat": 18.5204, "lon": 73.8567, "zip": "411"},
    "Ahmedabad": {"state": "Gujarat", "district": "Ahmedabad", "lat": 23.0225, "lon": 72.5714, "zip": "380"},
    "Jaipur": {"state": "Rajasthan", "district": "Jaipur", "lat": 26.9124, "lon": 75.7873, "zip": "302"},
    "Lucknow": {"state": "Uttar Pradesh", "district": "Lucknow", "lat": 26.8467, "lon": 80.9462, "zip": "226"},
    "Surat": {"state": "Gujarat", "district": "Surat", "lat": 21.1702, "lon": 72.8311, "zip": "395"},
    "Kanpur": {"state": "Uttar Pradesh", "district": "Kanpur", "lat": 26.4499, "lon": 80.3319, "zip": "208"},
    "Nagpur": {"state": "Maharashtra", "district": "Nagpur", "lat": 21.1458, "lon": 79.0882, "zip": "440"},
    "Indore": {"state": "Madhya Pradesh", "district": "Indore", "lat": 22.7196, "lon": 77.8577, "zip": "452"},
    "Bhopal": {"state": "Madhya Pradesh", "district": "Bhopal", "lat": 23.2599, "lon": 77.4126, "zip": "462"},
    "Patna": {"state": "Bihar", "district": "Patna", "lat": 25.5941, "lon": 85.1376, "zip": "800"},
    "Ludhiana": {"state": "Punjab", "district": "Ludhiana", "lat": 30.9010, "lon": 75.8573, "zip": "141"},
    "Agra": {"state": "Uttar Pradesh", "district": "Agra", "lat": 27.1767, "lon": 78.0081, "zip": "282"},
    "Nashik": {"state": "Maharashtra", "district": "Nashik", "lat": 19.9975, "lon": 73.7898, "zip": "422"},
    "Faridabad": {"state": "Haryana", "district": "Faridabad", "lat": 28.4089, "lon": 77.3178, "zip": "121"},
    "Meerut": {"state": "Uttar Pradesh", "district": "Meerut", "lat": 28.9845, "lon": 77.7064, "zip": "250"},
    "Rajkot": {"state": "Gujarat", "district": "Rajkot", "lat": 22.3039, "lon": 70.8022, "zip": "360"},
    "Varanasi": {"state": "Uttar Pradesh", "district": "Varanasi", "lat": 25.3176, "lon": 82.9739, "zip": "221"},
    "Srinagar": {"state": "Jammu & Kashmir", "district": "Srinagar", "lat": 34.0837, "lon": 74.7973, "zip": "190"},
    "Visakhapatnam": {"state": "Andhra Pradesh", "district": "Visakhapatnam", "lat": 17.6868, "lon": 83.2185, "zip": "530"},
    "Thane": {"state": "Maharashtra", "district": "Thane", "lat": 19.2183, "lon": 72.9781, "zip": "400"},
    "Ghaziabad": {"state": "Uttar Pradesh", "district": "Ghaziabad", "lat": 28.6692, "lon": 77.4538, "zip": "201"},
    "Vasai": {"state": "Maharashtra", "district": "Palghar", "lat": 19.3919, "lon": 72.8397, "zip": "401"},
    "Kalyan": {"state": "Maharashtra", "district": "Thane", "lat": 19.2437, "lon": 73.1355, "zip": "421"},
}

# Thane district contains two dataset cities (Thane and Kalyan).  Keep the
# dropdown labels unique while preserving the real administrative district.
DISTRICT_DISPLAY_OVERRIDES: dict[tuple[str, str], str] = {
    ("Maharashtra", "Kalyan"): "Thane (Kalyan)",
}


def district_display_name(state: str, city: str) -> str:
    """Return the unique dropdown label for a dataset city."""
    geo = CITY_GEO[city]
    return DISTRICT_DISPLAY_OVERRIDES.get((state, city), str(geo["district"]))


def build_location_catalog(available_cities: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """Build a sorted ``state -> districts`` catalog for the given model scopes.

    ``available_cities`` is the set of city display names from the loaded GRU.
    When omitted, every city in the dataset mapping is returned.
    """
    available = None
    if available_cities is not None:
        available = {str(city).strip().casefold() for city in available_cities}

    states: dict[str, list[dict[str, str]]] = {}
    for city, geo in CITY_GEO.items():
        if available is not None and city.strip().casefold() not in available:
            continue
        state = str(geo["state"])
        states.setdefault(state, []).append(
            {
                "district": district_display_name(state, city),
                "city": city,
                "scope_key": f"city:{city}",
            }
        )

    catalog = []
    for state in sorted(states):
        districts = sorted(states[state], key=lambda item: item["district"])
        catalog.append({"state": state, "districts": districts})
    return catalog


def resolve_location(
    state: str,
    district: str,
    available_cities: Iterable[str] | None = None,
) -> dict[str, str] | None:
    """Resolve a state/district pair case-insensitively to a model city scope."""
    wanted_state = state.strip().casefold()
    wanted_district = district.strip().casefold()

    for state_entry in build_location_catalog(available_cities):
        if state_entry["state"].strip().casefold() != wanted_state:
            continue
        for entry in state_entry["districts"]:
            if (
                entry["district"].strip().casefold() == wanted_district
                or entry["city"].strip().casefold() == wanted_district
            ):
                return {"state": state_entry["state"], **entry}
            if f"{entry['district']} ({entry['city']})".strip().casefold() == wanted_district:
                return {"state": state_entry["state"], **entry}
    return None


__all__ = [
    "CITY_GEO",
    "DISTRICT_DISPLAY_OVERRIDES",
    "build_location_catalog",
    "district_display_name",
    "resolve_location",
]
