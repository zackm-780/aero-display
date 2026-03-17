from pathlib import Path

from backend.app.state import CenterState, CenterStateStore


def test_center_state_persists_and_loads(tmp_path):
    store_path = tmp_path / "state.json"
    store = CenterStateStore(store_path)

    original = CenterState(icao="KSFO", lat=37.6213, lon=-122.3790)
    store.save(original)

    loaded = store.load()
    assert loaded is not None
    assert loaded.icao == "KSFO"
    assert abs(loaded.lat - 37.6213) < 1e-6
    assert abs(loaded.lon - (-122.3790)) < 1e-6

