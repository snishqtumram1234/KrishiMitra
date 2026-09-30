"""Maharashtra districts -> approximate headquarters coordinates (for weather lookups).

Coordinates are district-HQ approximations, good enough for a district-level forecast.
Old and new official names are both accepted (e.g. Aurangabad / Chhatrapati Sambhajinagar).
"""

from typing import NamedTuple


class District(NamedTuple):
    name: str
    lat: float
    lon: float


_DISTRICTS = [
    District("Ahilyanagar", 19.09, 74.74),
    District("Akola", 20.71, 77.00),
    District("Amravati", 20.93, 77.75),
    District("Beed", 18.99, 75.76),
    District("Bhandara", 21.17, 79.65),
    District("Buldhana", 20.53, 76.18),
    District("Chandrapur", 19.96, 79.30),
    District("Chhatrapati Sambhajinagar", 19.88, 75.34),
    District("Dharashiv", 18.18, 76.04),
    District("Dhule", 20.90, 74.77),
    District("Gadchiroli", 20.18, 80.00),
    District("Gondia", 21.46, 80.19),
    District("Hingoli", 19.72, 77.15),
    District("Jalgaon", 21.00, 75.56),
    District("Jalna", 19.84, 75.88),
    District("Kolhapur", 16.70, 74.24),
    District("Latur", 18.40, 76.56),
    District("Mumbai City", 18.94, 72.83),
    District("Mumbai Suburban", 19.08, 72.88),
    District("Nagpur", 21.15, 79.09),
    District("Nanded", 19.15, 77.31),
    District("Nandurbar", 21.37, 74.24),
    District("Nashik", 20.00, 73.79),
    District("Palghar", 19.70, 72.77),
    District("Parbhani", 19.27, 76.77),
    District("Pune", 18.52, 73.86),
    District("Raigad", 18.64, 72.87),
    District("Ratnagiri", 16.99, 73.30),
    District("Sangli", 16.85, 74.58),
    District("Satara", 17.68, 74.00),
    District("Sindhudurg", 16.10, 73.70),
    District("Solapur", 17.66, 75.91),
    District("Thane", 19.22, 72.98),
    District("Wardha", 20.74, 78.60),
    District("Washim", 20.11, 77.13),
    District("Yavatmal", 20.39, 78.12),
]

_ALIASES = {
    "ahmednagar": "Ahilyanagar",
    "aurangabad": "Chhatrapati Sambhajinagar",
    "sambhajinagar": "Chhatrapati Sambhajinagar",
    "osmanabad": "Dharashiv",
    "mumbai": "Mumbai City",
    "bombay": "Mumbai City",
    "poona": "Pune",
}

_BY_KEY = {d.name.lower(): d for d in _DISTRICTS}


def resolve_district(name: str | None) -> District | None:
    key = " ".join((name or "").strip().lower().split())
    key = _ALIASES.get(key, key).lower()
    return _BY_KEY.get(key)


def all_districts() -> list[str]:
    return [d.name for d in _DISTRICTS]
