import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import main
from backend.app.state import CenterState, CenterStateStore
from backend.app.icao_lookup import AirportDatabase


def test_websocket_picks_up_center_changes_without_reconnect(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    csv_path = data_dir / "airports.csv"
    csv_path.write_text(
        "ident,name,latitude_deg,longitude_deg,elevation_ft\n"
        "KSFO,San Francisco Intl,37.6213,-122.3790,13\n"
        "KLAX,Los Angeles Intl,33.9425,-118.4081,125\n",
        encoding="utf-8",
    )
    state_path = data_dir / "state.json"

    test_store = CenterStateStore(state_path)
    test_store.save(CenterState(icao="KSFO", lat=37.6213, lon=-122.3790))

    async def fake_fetch_states(params=None):
        return {"states": []}

    monkeypatch.setattr(main, "_state_store", test_store)
    monkeypatch.setattr(main, "_airport_db", AirportDatabase(csv_path))
    monkeypatch.setattr(main, "_fetch_states", fake_fetch_states)
    monkeypatch.setattr(main.settings, "poll_interval_seconds", 0.01)

    client = TestClient(main.app)
    with client.websocket_connect("/ws") as ws:
        first = ws.receive_json()
        assert first["center"]["icao"] == "KSFO"

        test_store.save(CenterState(icao="KLAX", lat=33.9425, lon=-118.4081))

        switched = False
        for _ in range(20):
            msg = ws.receive_json()
            if msg["center"]["icao"] == "KLAX":
                switched = True
                break
        assert switched
