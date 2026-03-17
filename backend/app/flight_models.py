from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Tuple

from backend.app.geo import haversine_nm


VFR_SQUAWKS = {"1200", "7000"}


def _looks_like_airline_callsign(callsign: str) -> bool:
    cs = (callsign or "").strip().upper()
    return len(cs) >= 3 and cs[:3].isalpha()


def _is_ifr_proxy(callsign: str, squawk: str | None) -> bool:
    # Hybrid proxy: keep flights that look like scheduled airline traffic,
    # or flights with a non-VFR squawk code.
    if _looks_like_airline_callsign(callsign):
        return True
    sq = (squawk or "").strip()
    return bool(sq) and sq not in VFR_SQUAWKS


@dataclass
class Flight:
    icao24: str
    callsign: str
    airline_code: str | None
    lat: float
    lon: float
    heading: float | None
    altitude: float | None
    velocity: float | None
    distance_nm: float


def build_flight_lists(
    states: List[list[Any]],
    center_lat: float,
    center_lon: float,
) -> Tuple[list[Flight], list[Flight]]:
    """Build board (200 NM) and radar (50 NM) lists from raw OpenSky states."""
    board: list[Flight] = []
    radar: list[Flight] = []

    for state in states:
        # OpenSky "states" format: [icao24, callsign, origin_country, time_position, last_contact,
        #   longitude, latitude, baro_altitude, on_ground, velocity, true_track, vertical_rate, ...]
        try:
            icao24 = (state[0] or "").strip()
            callsign = (state[1] or "").strip()
            lon = float(state[5])
            lat = float(state[6])
        except (IndexError, TypeError, ValueError):
            continue

        try:
            on_ground = bool(state[8])
        except (IndexError, TypeError, ValueError):
            on_ground = False

        # Exclude taxiing/parked traffic from board and radar views.
        if on_ground:
            continue

        squawk: str | None = None
        try:
            squawk = str(state[14]).strip() if state[14] is not None else None
        except (IndexError, TypeError, ValueError):
            squawk = None

        if not _is_ifr_proxy(callsign, squawk):
            continue

        distance = haversine_nm(center_lat, center_lon, lat, lon)

        velocity = None
        heading = None
        altitude = None
        try:
            altitude = float(state[7]) if state[7] is not None else None
        except (IndexError, TypeError, ValueError):
            pass
        try:
            velocity = float(state[9]) if state[9] is not None else None
        except (IndexError, TypeError, ValueError):
            pass
        try:
            heading = float(state[10]) if state[10] is not None else None
        except (IndexError, TypeError, ValueError):
            pass

        airline_code = None
        if callsign:
            airline_code = callsign[:3].strip().upper()

        flight = Flight(
            icao24=icao24,
            callsign=callsign,
            airline_code=airline_code,
            lat=lat,
            lon=lon,
            heading=heading,
            altitude=altitude,
            velocity=velocity,
            distance_nm=distance,
        )

        if distance <= 200:
            board.append(flight)
        if distance <= 50:
            radar.append(flight)

    board.sort(key=lambda f: f.distance_nm)
    radar.sort(key=lambda f: f.distance_nm)
    return board, radar

