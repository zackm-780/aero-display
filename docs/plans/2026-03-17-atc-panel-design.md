# AeroDisplay Backend Wiring & ATC Panel Design

**Goal:** Wire the backend app composition (HTTP + WebSocket + config) and add a fixed-range terrain-aware radar map with range presets (20/50/100/200 NM) on the frontend.

---

## Architecture Overview

- **Backend**
  - `settings.py` defines a `Settings` object (likely via `pydantic.BaseSettings`) that centralizes:
    - OpenSky base URL and credentials.
    - Default center ICAO.
    - `DATA_DIR` (for `state.json`, `airports.csv`).
    - `FRONTEND_DIR` (for static files).
  - `http.py`:
    - Dependency providers `get_state_store` and `get_airport_db` derive paths from `settings.DATA_DIR` instead of hard-coded `backend/data`.
    - `mount_static(app)` mounts `settings.FRONTEND_DIR` at `/` for the SPA.
  - `main.py` is the composition root:
    - Instantiates a single `Settings` instance and constructs shared dependencies:
      - `OpenSkyClient`.
      - `CenterStateStore`.
      - `AirportDatabase`.
    - Includes the HTTP router under `/api`.
    - Calls `mount_static(app)`.
    - Hosts the WebSocket endpoint which:
      - Resolves the current center (from persisted state or default ICAO).
      - Polls OpenSky at an interval with backoff.
      - Uses `build_flight_lists` + `build_payload` to shape data.
      - Pushes payloads to clients until disconnect.

- **Frontend**
  - Continues to use Leaflet with a dark Carto/OSM basemap for terrain context.
  - Adds a **range control** for fixed presets: 20 NM, 50 NM (default), 100 NM, 200 NM.
  - Adds **range rings** (L.circle overlays) centered on the current radar center:
    - All four rings can be rendered, but the active range is visually emphasized.
  - The map zoom level is derived from the active range via a simple mapping:
    - Example mapping (tunable): 20→10, 50→9, 100→8, 200→7.
    - This keeps the active range circle roughly filling the map viewport without complex math.

---

## Data Flow

1. **Center selection**
   - User chooses an ICAO in the settings modal.
   - `/api/center`:
     - Looks up the ICAO in `AirportDatabase` to get lat/lon.
     - Persists it via `CenterStateStore`.
   - WebSocket loop:
     - Reads `CenterState` on connection (or derives from default ICAO if unset).

2. **Polling & transformation**
   - For each iteration of the WS loop:
     - Compute a bounding region around the center (sufficient to cover at least 200 NM).
     - Use `OpenSkyClient.fetch_states(...)` to retrieve raw state vectors.
     - Use `build_flight_lists` to split flights into:
       - Board flights (≤200 NM, sorted by proximity).
       - Radar flights (≤50 NM).
     - Use `build_payload(center, board, radar, stale)` to shape the JSON contract expected by the frontend.
     - Send payload via `websocket.send_json(payload)`.

3. **Frontend consumption**
   - On each message:
     - Update the map center and markers based on `center` and `radarFlights`.
     - Render the board list from `boardFlights`.
     - Update the staleness indicator from `meta.stale`.
     - Apply the active range (20/50/100/200 NM) to:
       - Set the map zoom (`zoomForRangeNm(activeRangeNm)`).
       - Redraw range rings.

---

## Components

- **Backend**
  - `backend/app/settings.py`
    - Defines `Settings` with fields for OpenSky configuration, default center, data paths, and frontend path.
  - `backend/app/http.py`
    - Uses `Settings` for data paths in DI providers.
    - `mount_static(app, settings)` mounts static frontend at `/`.
  - `backend/app/main.py`
    - Creates `app = FastAPI()`.
    - Instantiates `Settings` (possibly via a `get_settings()` helper with caching).
    - Builds shared dependencies (state store, airport DB, OpenSky client).
    - Includes API router under `/api`.
    - Calls `mount_static`.
    - Implements `/ws` endpoint that:
      - Accepts WebSocket.
      - Resolves center.
      - Runs a polling loop until disconnect.

- **Frontend**
  - `frontend/index.html`
    - May gain a small UI element near the Radar header showing a “Range” control.
  - `frontend/app.js`
    - Adds:
      - A `rangeLayer` (`L.layerGroup`) separate from `radarLayer`.
      - State for `currentRangeNm` (default 50).
      - `nmToMeters(nm)` helper.
      - `zoomForRangeNm(nm)` helper with a simple mapping.
      - `updateRangeRings(center, activeRangeNm)` to manage four distance rings.
      - Event handlers for the range control buttons that:
        - Update `currentRangeNm`.
        - Recenter map at zoom derived from range.
        - Redraw range rings.

---

## Error Handling & Observability

- Backend:
  - `OpenSkyClient` logs retry attempts, response status codes, and failures before raising `OpenSkyError`.
  - `CenterStateStore.load` logs malformed/corrupt JSON instead of silently dropping state.
  - WebSocket loop:
    - Catches transient errors in polling, marks payload as `stale=True`, and continues when appropriate.
    - Cleanly exits on `WebSocketDisconnect`.

- Frontend:
  - WebSocket JSON parse errors are surfaced via `console.error` (not silently swallowed).
  - Settings errors use existing inline error text and can later be extended with subtle styling if needed.

---

## Testing Strategy

- **Unit tests**
  - Existing tests for geo/filtering/backoff/payload remain unchanged.
  - New tests for:
    - `get_state_store` / `get_airport_db` honoring configuration paths.

- **Integration tests**
  - FastAPI app test:
    - Asserts that `/` serves the index HTML and `/api/center` works with DI overrides.
  - WebSocket contract test:
    - Overrides OpenSky client with a fake that returns deterministic states.
    - Connects to `/ws` via `TestClient.websocket_connect`.
    - Asserts that payloads match the expected shape (reusing `test_ws_payload_shape_basic` logic as a guide).

