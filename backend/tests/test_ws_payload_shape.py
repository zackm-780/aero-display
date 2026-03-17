from backend.app.flight_models import Flight
from backend.app.ws import build_payload


def test_ws_payload_shape_basic():
    center = {"icao": "KSFO", "lat": 37.6213, "lon": -122.3790}

    board = [
        Flight(
            icao24="abc123",
            callsign="FOO123",
            airline_code="FOO",
            lat=37.7,
            lon=-122.4,
            heading=90,
            altitude=10000,
            velocity=220,
            distance_nm=10.5,
        )
    ]
    radar = [
        Flight(
            icao24="def456",
            callsign="BAR456",
            airline_code="BAR",
            lat=37.8,
            lon=-122.3,
            heading=180,
            altitude=12000,
            velocity=250,
            distance_nm=5.0,
        )
    ]

    payload = build_payload(center=center, board=board, radar=radar, stale=False)

    assert set(payload.keys()) == {"center", "boardFlights", "radarFlights", "meta"}
    assert payload["center"]["icao"] == "KSFO"
    assert isinstance(payload["boardFlights"], list)
    assert isinstance(payload["radarFlights"], list)
    assert payload["boardFlights"][0]["callsign"] == "FOO123"
    assert payload["radarFlights"][0]["distanceNm"] == 5.0
    assert payload["meta"]["stale"] is False

