from backend.app.flight_models import build_flight_lists


def test_flight_lists_radius_and_sorting():
    center_lat = 0.0
    center_lon = 0.0

    # Minimal synthetic states: [icao24, callsign, origin_country, tpos, last_contact, lon, lat, baro_alt, on_ground, velocity, true_track]
    # One close, one medium, one far
    close = ["abc123", "CLOSE", "X", None, None, 0.1, 0.1, 10000, False, 200, 90]
    medium = ["def456", "MED", "X", None, None, 1.0, 1.0, 20000, False, 250, 180]
    far = ["ghi789", "FAR", "X", None, None, 10.0, 10.0, 30000, False, 450, 270]

    board, radar = build_flight_lists([far, medium, close], center_lat, center_lon)

    # board should contain both close and medium (assuming both within 200 NM)
    callsigns_board = [f.callsign for f in board]
    assert "CLOSE" in callsigns_board
    assert "MED" in callsigns_board

    # radar should contain only the closest, assuming medium is beyond 50 NM
    callsigns_radar = [f.callsign for f in radar]
    assert callsigns_radar == ["CLOSE"]

    # and board should be sorted with CLOSE before MED (by distance)
    assert callsigns_board[0] == "CLOSE"

