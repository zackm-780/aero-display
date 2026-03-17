from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.app.flight_models import Flight
from backend.app.settings import get_settings


_settings = get_settings()


def _flight_to_dict(f: Flight) -> Dict[str, Any]:
    return {
        "icao24": f.icao24,
        "callsign": f.callsign,
        "airlineCode": f.airline_code,
        "lat": f.lat,
        "lon": f.lon,
        "heading": f.heading,
        "altitude": f.altitude,
        "velocity": f.velocity,
        "distanceNm": f.distance_nm,
    }


def build_payload(
    *,
    center: Dict[str, Any],
    board: List[Flight],
    radar: List[Flight],
    stale: bool,
) -> Dict[str, Any]:
    """Build the JSON-serializable payload pushed over WebSocket."""
    now_iso = datetime.now(timezone.utc).isoformat()
    airport_elevation_ft = center.get("elevation_ft")
    transition_altitude_ft = center.get("transition_altitude_ft", _settings.transition_altitude_ft)
    return {
        "center": {
            "icao": center["icao"],
            "lat": center["lat"],
            "lon": center["lon"],
            "updatedAt": now_iso,
        },
        "boardFlights": [_flight_to_dict(f) for f in board],
        "radarFlights": [_flight_to_dict(f) for f in radar],
        "meta": {
            "stale": stale,
            "generatedAt": now_iso,
            "airportElevationFt": airport_elevation_ft,
            "transitionAltitudeFt": transition_altitude_ft,
        },
    }

