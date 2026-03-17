# ATC Panel & Backend Wiring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire backend composition (config, HTTP API, WebSocket) and add a fixed-range (20/50/100/200 NM) terrain-aware radar view to the ATC panel, keeping the existing dark Leaflet basemap.

**Architecture:** Centralize configuration in `settings.py`, make `main.py` the clear composition root (router + static + WebSocket + dependencies), and extend the frontend map to support range presets and rings while reusing the existing payload contract from the backend.

**Tech Stack:** Python, FastAPI, httpx, Pydantic, Pytest; Vanilla JS, Leaflet.

---

### Task 1: Centralize backend configuration

**Files:**
- Modify: `backend/app/settings.py`
- Modify: `backend/app/http.py`

**Step 1: Define Settings model**

Add a `Settings` class in `backend/app/settings.py` using `pydantic.BaseSettings` with at least:
- `opensky_base_url: str = "https://opensky-network.org/api"`
- `opensky_username: str | None = None`
- `opensky_password: str | None = None`
- `default_center_icao: str = "KSFO"` (or another sensible default)
- `data_dir: Path` defaulting to the project `backend/data` directory resolved from `__file__`
- `frontend_dir: Path` defaulting to the project `frontend` directory resolved from `__file__`

Provide a `get_settings()` function that returns a cached singleton instance (e.g. using `functools.lru_cache`).

**Step 2: Wire http dependencies to settings**

In `backend/app/http.py`:
- Import `get_settings`.
- Update `get_state_store()` and `get_airport_db()` to:
  - Call `settings = get_settings()`.
  - Use `settings.data_dir / "state.json"` and `settings.data_dir / "airports.csv"` instead of hard-coded paths.

**Step 3: Wire static mounting to settings**

In `backend/app/http.py`:
- Change `mount_static(app)` to:
  - Resolve `frontend_path` via `get_settings().frontend_dir`.
  - Keep the same `StaticFiles` mounting behavior.

**Step 4: Quick verification**

- Run `pytest backend/tests/test_center_post.py -q` to ensure HTTP center behavior still passes.

---

### Task 2: Make main.py the composition root

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/__init__.py` (optional convenience)
- Test: `backend/tests` (new integration test file)

**Step 1: Include router and mount static**

In `backend/app/main.py`:
- Import `router` and `mount_static` from `backend.app.http`.
- Import `get_settings` from `backend.app.settings`.
- After creating `app = FastAPI()`,:
  - Call `settings = get_settings()`.
  - `app.include_router(router, prefix="/api")`.
  - `mount_static(app)`.

**Step 2: Expose app in package init (optional)**

In `backend/app/__init__.py`:
- Import `app` from `.main` and set `__all__ = ["app"]` so `backend.app:app` works as an entrypoint.

**Step 3: Add minimal integration smoke test**

Create `backend/tests/test_app_integration.py` that:
- Uses `from backend.app.main import app`.
- Uses `TestClient` from FastAPI to:
  - `GET("/")` and assert a 200 and that the HTML contains `"AeroDisplay"`.
  - `GET("/api/health")` and assert `{"status": "ok"}`.

Run:
- `pytest backend/tests/test_app_integration.py -q`

---

### Task 3: Implement WebSocket polling skeleton

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/opensky.py` (logging only, optional)
- Modify: `backend/app/state.py` (logging only, optional)
- Test: `backend/tests/test_ws_integration.py` (new)

**Step 1: Prepare shared dependencies**

In `backend/app/main.py`:
- After `settings = get_settings()`:
  - Construct a shared `CenterStateStore` from `settings.data_dir / "state.json"`.
  - Construct a shared `AirportDatabase` from `settings.data_dir / "airports.csv"`.
  - Construct a shared `OpenSkyClient` using `settings.opensky_base_url` and credentials.

**Step 2: Implement a simple WebSocket loop**

Replace the placeholder `/ws` implementation with:
- Accept the WebSocket.
- Resolve the current center:
  - Try `store.load()`.
  - If missing, derive from `settings.default_center_icao` and `AirportDatabase.lookup`, then persist.
- In a `while True` loop:
  - Fetch states via `OpenSkyClient.fetch_states(...)` with a bounding region that covers at least 200 NM around center (details can be refined later).
  - Use `build_flight_lists` to construct `board` and `radar` lists.
  - Use `build_payload(center_dict, board, radar, stale=False)` for the JSON payload.
  - Send payload via `await websocket.send_json(payload)`.
  - `await asyncio.sleep(poll_interval)` between iterations (e.g. 10–15 seconds).
- Catch `WebSocketDisconnect` and exit cleanly.
- For transient fetch errors:
  - Catch `OpenSkyError`, log, and send a payload with `stale=True` (or skip sending until next success).

**Step 3: Add a basic WebSocket contract test**

Create `backend/tests/test_ws_integration.py`:
- Build a minimal test app that uses:
  - The real router and static mounting.
  - A fake `OpenSkyClient` (injected or monkeypatched) that returns a small deterministic set of states.
- Use `TestClient` and `websocket_connect("/ws")` to:
  - Receive a message.
  - Assert that the JSON payload conforms to the expected keys and structure (center, boardFlights, radarFlights, meta) and that board/radar entries align with the fake data.

---

### Task 4: Add range rings and fixed zoom presets to frontend

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.js`
- (Optional) Modify: `frontend/styles.css`

**Step 1: Add range control UI**

In `frontend/index.html`:
- In the Radar pane header, add a small range control element, e.g.:
  - A `div` or `nav` with buttons for `20 nm`, `50 nm`, `100 nm`, `200 nm`.
- Give the buttons IDs or data attributes so they can be wired in `app.js`.

**Step 2: Introduce range state and helpers**

In `frontend/app.js`:
- Add:
  - `let rangeLayer;`
  - `let currentRangeNm = 50;`
  - `const RANGE_PRESETS = [20, 50, 100, 200];`
- Add helper functions:
  - `function nmToMeters(nm) { return nm * 1852; }`
  - `function zoomForRangeNm(nm) { /* simple mapping, e.g. switch or lookup */ }`
- Initialize `rangeLayer = L.layerGroup().addTo(map);` in `initMap`.

**Step 3: Draw range rings**

Add `updateRangeRings(center, activeRangeNm)` that:
- Clears `rangeLayer`.
- For each preset (20/50/100/200):
  - Adds an `L.circle` centered on `[center.lat, center.lon]` with radius `nmToMeters(value)`.
  - Styles the circle so the active range is emphasized (thicker/ brighter stroke).

Call `updateRangeRings(center, currentRangeNm)` from `updateMap` after setting the view.

**Step 4: Wire range buttons**

In `frontend/app.js`:
- Grab references to the new range buttons.
- Add click handlers that:
  - Set `currentRangeNm` to the clicked value.
  - Re-center the map with `map.setView([center.lat, center.lon], zoomForRangeNm(currentRangeNm));` using the latest known center (can be stored in a `lastCenter` variable updated by `handleMessage`).
  - Call `updateRangeRings(lastCenter, currentRangeNm)` if `lastCenter` is defined.
  - Update button styles (e.g. `active` class).

**Step 5: Quick verification**

- Run the dev server and:
  - Confirm the Radar pane shows range buttons.
  - Confirm that selecting a range updates zoom and rings (once WebSocket data is flowing).

---

### Task 5: Logging and robustness improvements (optional, after core flow works)

**Files:**
- Modify: `backend/app/opensky.py`
- Modify: `backend/app/state.py`

**Step 1: Add logging to OpenSky client**

In `opensky.py`:
- Introduce a module-level logger.
- Log:
  - Retry attempts with attempt count and status code.
  - When giving up and raising `OpenSkyError`.

**Step 2: Add logging to state persistence**

In `state.py`:
- Log warnings when:
  - State file is missing (first-run scenario).
  - State file contains invalid JSON and is ignored.

**Step 3: Run full test suite**

- Run `pytest backend/tests -q` and ensure all tests pass.

