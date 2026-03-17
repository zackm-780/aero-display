from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.http import CenterStateStore, AirportDatabase, CenterRequest, get_airport_db, get_state_store, mount_static, router


def test_post_center_updates_state_and_returns_coords(tmp_path, monkeypatch):
    # Prepare temporary state file and airports CSV
    data_dir = tmp_path / "backend" / "data"
    data_dir.mkdir(parents=True)
    state_path = data_dir / "state.json"
    airports_csv = data_dir / "airports.csv"
    airports_csv.write_text("ident,name,latitude_deg,longitude_deg\nKSFO,San Francisco Intl,37.6213,-122.3790\n")

    # Patch dependency functions to use temp paths
    def _get_state_store_override() -> CenterStateStore:
        return CenterStateStore(state_path)

    def _get_airport_db_override() -> AirportDatabase:
        return AirportDatabase(airports_csv)

    app = FastAPI()
    app.include_router(router, prefix="/api")
    mount_static(app)

    app.dependency_overrides[get_state_store] = _get_state_store_override
    app.dependency_overrides[get_airport_db] = _get_airport_db_override

    client = TestClient(app)

    resp = client.post("/api/center", json={"icao": "KSFO"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["icao"] == "KSFO"
    assert abs(data["lat"] - 37.6213) < 1e-6
    assert abs(data["lon"] - (-122.3790)) < 1e-6

