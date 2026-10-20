"""
ai/forecasting/locations.py
===========================
Single source of truth for the state/district catalogue used by the dashboard.

Two layers are combined here:

1. ``INDIA_STATE_DISTRICTS`` (``ai.forecasting.india_locations``) contains every
   officially recognised district for all 28 States and 8 Union Territories.
2. ``CITY_GEO`` maps the 29 city-level scopes present in the source dataset to
   their Indian state and administrative district.

Every district in the catalogue is therefore selectable.  Districts that are
directly represented in the dataset use their own trained model scope; the
remaining districts are transparently mapped to a representative dataset scope
(``coverage="proxy"``).  The API never invents a prediction: a proxy entry
always points at a real GRU scope, and the response says so.
"""

from __future__ import annotations

import unicodedata
from typing import Any, Iterable

from ai.forecasting.india_locations import INDIA_STATE_DISTRICTS

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

# Dataset city -> the name of that district in the official State/UT list.
# Only names that differ from ``CITY_GEO[...]["district"]`` need an entry.
DATASET_CITY_OFFICIAL_DISTRICT: dict[str, str] = {
    "Mumbai": "Mumbai City",
    "Kanpur": "Kanpur Nagar",
}

# Representative model scope for each State/UT.  Used only when a district has
# no dedicated dataset city.  States that appear in the dataset always point at
# one of their own cities; the remaining States/UTs point at a configured
# representative city that the trained model actually covers.  These are
# geographic stand-ins, not claims of local accuracy.
STATE_PROXY_CITY: dict[str, str] = {
    # States represented in the dataset.
    "Andhra Pradesh": "Visakhapatnam",
    "Bihar": "Patna",
    "Delhi": "Delhi",
    "Gujarat": "Ahmedabad",
    "Haryana": "Faridabad",
    "Jammu and Kashmir": "Srinagar",
    "Karnataka": "Bangalore",
    "Madhya Pradesh": "Bhopal",
    "Maharashtra": "Mumbai",
    "Punjab": "Ludhiana",
    "Rajasthan": "Jaipur",
    "Tamil Nadu": "Chennai",
    "Telangana": "Hyderabad",
    "Uttar Pradesh": "Lucknow",
    "West Bengal": "Kolkata",
    # States/UTs without a dedicated dataset city.
    "Andaman and Nicobar Islands": "Chennai",
    "Arunachal Pradesh": "Kolkata",
    "Assam": "Kolkata",
    "Chandigarh": "Delhi",
    "Chhattisgarh": "Nagpur",
    "Dadra and Nagar Haveli and Daman and Diu": "Surat",
    "Goa": "Pune",
    "Himachal Pradesh": "Delhi",
    "Jharkhand": "Kolkata",
    "Kerala": "Bangalore",
    "Ladakh": "Srinagar",
    "Lakshadweep": "Bangalore",
    "Manipur": "Kolkata",
    "Meghalaya": "Kolkata",
    "Mizoram": "Kolkata",
    "Nagaland": "Kolkata",
    "Odisha": "Kolkata",
    "Puducherry": "Chennai",
    "Sikkim": "Kolkata",
    "Tripura": "Kolkata",
    "Uttarakhand": "Delhi",
}

# Common spellings that should still resolve to an official State/UT.
# Keys are ``_text_key``-normalised (lowercase, letters and digits only).
STATE_ALIASES: dict[str, str] = {
    "andamanandnicobar": "Andaman and Nicobar Islands",
    "andamanandnicobarislands": "Andaman and Nicobar Islands",
    "dadraandnagarhaveli": "Dadra and Nagar Haveli and Daman and Diu",
    "nctofdelhi": "Delhi",
    "nationalcapitalterritoryofdelhi": "Delhi",
    "orissa": "Odisha",
    "pondicherry": "Puducherry",
    "uttaranchal": "Uttarakhand",
}

# Extra spellings for districts whose dataset name differs from the official
# list, or that users commonly type.  Keys are (normalised state, normalised
# alias) and values are the official district name.
DISTRICT_ALIASES: dict[tuple[str, str], str] = {
    ("karnataka", "bangalore"): "Bangalore Urban",
    ("karnataka", "bengaluru"): "Bangalore Urban",
    ("karnataka", "bengaluruurban"): "Bangalore Urban",
    ("maharashtra", "mumbai"): "Mumbai City",
    ("uttarpradesh", "kanpur"): "Kanpur Nagar",
}

# Kept for backwards compatibility with callers that used the old
# city-scope-only catalogue.  The full district catalogue is unique by design,
# so no display overrides are needed there.
DISTRICT_DISPLAY_OVERRIDES: dict[tuple[str, str], str] = {
    ("Maharashtra", "Kalyan"): "Thane (Kalyan)",
}


def _text_key(value: str) -> str:
    """Normalise text for case/accent/spacing-insensitive comparisons."""
    decomposed = unicodedata.normalize("NFKD", str(value))
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return "".join(ch for ch in ascii_text.casefold() if ch.isalnum())


def _canonical_state_key(state: str) -> str:
    cleaned = str(state).strip()
    alias = STATE_ALIASES.get(_text_key(cleaned))
    if alias:
        cleaned = alias
    return _text_key(cleaned.replace("&", " and "))


def _district_key(district: str) -> str:
    return _text_key(district)


def _direct_scope_index() -> dict[tuple[str, str], str]:
    """Map (canonical state, canonical district) -> dataset city."""
    index: dict[tuple[str, str], str] = {}
    for city, geo in CITY_GEO.items():
        state_key = _canonical_state_key(str(geo["state"]))
        official_district = DATASET_CITY_OFFICIAL_DISTRICT.get(city, str(geo["district"]))
        district_key = _district_key(official_district)
        # First city wins when two dataset cities share a district (Thane/Kalyan).
        index.setdefault((state_key, district_key), city)
    return index


def _available_set(available_cities: Iterable[str] | None) -> set[str] | None:
    if available_cities is None:
        return None
    return {str(city).strip().casefold() for city in available_cities}


def _proxy_city(state: str, available: set[str] | None) -> str | None:
    candidate = STATE_PROXY_CITY.get(state)
    if available is None:
        return candidate
    if candidate and candidate.casefold() in available:
        return candidate
    # Fall back to any scope the model can actually serve.
    for city in sorted(available):
        for known_city in CITY_GEO:
            if known_city.casefold() == city:
                return known_city
    return None


def district_display_name(state: str, city: str) -> str:
    """Return the unique dropdown label for a dataset city (legacy helper)."""
    geo = CITY_GEO[city]
    return DISTRICT_DISPLAY_OVERRIDES.get((state, city), str(geo["district"]))


def build_location_catalog(available_cities: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """Build the complete ``state -> districts`` catalogue.

    Every district in every State/UT is returned.  ``model_supported`` is true
    when the district has its own dataset city scope; otherwise the entry points
    to a real proxy scope and ``coverage`` is ``"proxy"``.

    ``available_cities`` is the set of city display names from the loaded GRU.
    When supplied, scopes that are not in the loaded model are never offered.
    """
    available = _available_set(available_cities)
    direct_index = _direct_scope_index()

    catalog: list[dict[str, Any]] = []
    for state in sorted(INDIA_STATE_DISTRICTS):
        state_key = _canonical_state_key(state)
        proxy_city = _proxy_city(state, available)
        districts: list[dict[str, Any]] = []

        for district in INDIA_STATE_DISTRICTS[state]:
            direct_city = direct_index.get((state_key, _district_key(district)))
            if direct_city and (available is None or direct_city.casefold() in available):
                districts.append(
                    {
                        "district": district,
                        "city": direct_city,
                        "scope_key": f"city:{direct_city}",
                        "model_supported": True,
                        "coverage": "dataset",
                    }
                )
            elif proxy_city:
                districts.append(
                    {
                        "district": district,
                        "city": proxy_city,
                        "scope_key": f"city:{proxy_city}",
                        "model_supported": False,
                        "coverage": "proxy",
                    }
                )

        districts.sort(key=lambda item: _district_key(item["district"]))
        if districts:
            catalog.append({"state": state, "districts": districts})
    return catalog


def resolve_location(
    state: str,
    district: str,
    available_cities: Iterable[str] | None = None,
) -> dict[str, Any] | None:
    """Resolve a state/district pair case-insensitively to a model scope."""
    wanted_state = _canonical_state_key(state)
    wanted_district = _text_key(district)
    alias = DISTRICT_ALIASES.get((wanted_state, wanted_district))
    if alias:
        wanted_district = _text_key(alias)

    for state_entry in build_location_catalog(available_cities):
        state_key = _canonical_state_key(state_entry["state"])
        if state_key != wanted_state:
            continue
        for entry in state_entry["districts"]:
            if _district_key(entry["district"]) == wanted_district:
                return {"state": state_entry["state"], **entry}
            # Accept a dataset city name only when it is the district's own
            # scope; proxy entries must not shadow the real district.
            if entry["model_supported"] and _district_key(entry["city"]) == wanted_district:
                return {"state": state_entry["state"], **entry}
    return None


__all__ = [
    "CITY_GEO",
    "DATASET_CITY_OFFICIAL_DISTRICT",
    "DISTRICT_ALIASES",
    "DISTRICT_DISPLAY_OVERRIDES",
    "STATE_ALIASES",
    "STATE_PROXY_CITY",
    "build_location_catalog",
    "district_display_name",
    "resolve_location",
]
