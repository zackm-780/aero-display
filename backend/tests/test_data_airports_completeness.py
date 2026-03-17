from pathlib import Path

from backend.app.icao_lookup import AirportDatabase


def test_seed_airports_dataset_contains_known_regional_and_major_icao() -> None:
    csv_path = Path(__file__).resolve().parents[1] / "data" / "airports.csv"
    db = AirportDatabase(csv_path)

    # Regression guard: users reported these should resolve.
    lat1, lon1, _name1 = db.lookup("KOTH")
    lat2, lon2, _name2 = db.lookup("KLAX")

    assert isinstance(lat1, float) and isinstance(lon1, float)
    assert isinstance(lat2, float) and isinstance(lon2, float)
