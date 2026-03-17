from backend.app.icao_lookup import AirportDatabase


def test_lookup_finds_known_icao(tmp_path, monkeypatch):
    csv_path = tmp_path / "airports.csv"
    csv_path.write_text("ident,name,latitude_deg,longitude_deg\nKSFO,San Francisco Intl,37.6213,-122.3790\n")

    db = AirportDatabase(csv_path)
    lat, lon, name = db.lookup("KSFO")

    assert abs(lat - 37.6213) < 1e-6
    assert abs(lon - (-122.3790)) < 1e-6
    assert name == "San Francisco Intl"


def test_lookup_is_case_insensitive(tmp_path):
    csv_path = tmp_path / "airports.csv"
    csv_path.write_text("ident,name,latitude_deg,longitude_deg\nksfo,San Francisco Intl,37.6213,-122.3790\n")

    db = AirportDatabase(csv_path)
    lat, lon, _ = db.lookup("KSFO")

    assert abs(lat - 37.6213) < 1e-6
    assert abs(lon - (-122.3790)) < 1e-6


def test_cache_avoids_reloading_dataset(tmp_path, monkeypatch):
    csv_path = tmp_path / "airports.csv"
    csv_path.write_text("ident,name,latitude_deg,longitude_deg\nKSFO,San Francisco Intl,37.6213,-122.3790\n")

    db = AirportDatabase(csv_path)

    # First lookup populates cache
    db.lookup("KSFO")

    # Overwrite the file to simulate external change; subsequent lookups should still
    # hit the in-memory cache and not be affected.
    csv_path.write_text("ident,name,latitude_deg,longitude_deg\nKSFO,Bogus Name,0,0\n")

    lat, lon, name = db.lookup("KSFO")
    assert abs(lat - 37.6213) < 1e-6
    assert abs(lon - (-122.3790)) < 1e-6
    assert name == "San Francisco Intl"

