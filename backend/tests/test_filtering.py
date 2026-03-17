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



def test_on_ground_states_excluded_from_board_and_radar():
    center_lat = 0.0
    center_lon = 0.0

    airborne = ["air001", "AIR1", "X", None, None, 0.1, 0.1, 5000, False, 150, 45]
    ground = ["grd001", "GRD1", "X", None, None, 0.1, 0.1, 20, True, 3, 180]

    board, radar = build_flight_lists([airborne, ground], center_lat, center_lon)

    board_callsigns = [f.callsign for f in board]
    radar_callsigns = [f.callsign for f in radar]

    assert "AIR1" in board_callsigns
    assert "AIR1" in radar_callsigns
    assert "GRD1" not in board_callsigns
    assert "GRD1" not in radar_callsigns


def test_hybrid_ifr_proxy_filters_vfr_like_general_aviation():
    center_lat = 0.0
    center_lon = 0.0

    # state format includes squawk at index 14
    # [icao24, callsign, origin_country, time_position, last_contact, lon, lat, baro_alt, on_ground, velocity, true_track, vertical_rate, sensors, geo_alt, squawk]
    airline_ifr = ["ifraaa", "UAL123", "X", None, None, 0.1, 0.1, 5000, False, 180, 90, 0, None, 5100, "1200"]
    non_airline_ifr_squawk = ["ifrbbb", "N123AB", "X", None, None, 0.1, 0.1, 4500, False, 150, 120, 0, None, 4600, "2301"]
    vfr_ga = ["vfr001", "N777ZZ", "X", None, None, 0.1, 0.1, 3000, False, 110, 200, 0, None, 3100, "1200"]

    board, radar = build_flight_lists([airline_ifr, non_airline_ifr_squawk, vfr_ga], center_lat, center_lon)

    board_callsigns = [f.callsign for f in board]
    radar_callsigns = [f.callsign for f in radar]

    assert "UAL123" in board_callsigns
    assert "N123AB" in board_callsigns
    assert "N777ZZ" not in board_callsigns

    assert "UAL123" in radar_callsigns
    assert "N123AB" in radar_callsigns
    assert "N777ZZ" not in radar_callsigns
