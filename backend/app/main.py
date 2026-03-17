from __future__ import annotations

from typing import Any, Dict, List

import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from backend.app.flight_models import build_flight_lists
from backend.app.http import mount_static, router
from backend.app.icao_lookup import AirportDatabase
from backend.app.opensky import OpenSkyClient, OpenSkyError
from backend.app.settings import get_settings
from backend.app.state import CenterState, CenterStateStore
from backend.app.ws import build_payload


app = FastAPI()

settings = get_settings()

app.include_router(router, prefix="/api")
mount_static(app)

_state_store = CenterStateStore(settings.resolved_data_dir / "state.json")
_airport_db = AirportDatabase(settings.resolved_data_dir / "airports.csv")
if not settings.opensky_client_id or not settings.opensky_client_secret:
    raise RuntimeError("OPEN_SKY_CLIENT_ID and OPEN_SKY_CLIENT_SECRET must be set in the environment")
_opensky_client = OpenSkyClient(
    base_url=settings.opensky_base_url,
    auth_url=settings.opensky_auth_url,
    client_id=settings.opensky_client_id,
    client_secret=settings.opensky_client_secret,
)


async def _resolve_center() -> CenterState:
    center = _state_store.load()
    if center is not None:
        return center
    icao = settings.default_center_icao.upper()
    lat, lon, _name = _airport_db.lookup(icao)
    center = CenterState(icao=icao, lat=lat, lon=lon)
    _state_store.save(center)
    return center


async def _fetch_states(params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    # Run the blocking httpx call in a threadpool
    return await run_in_threadpool(_opensky_client.fetch_states, params or {})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        center = await _resolve_center()
        while True:
            stale = False
            try:
                raw = await _fetch_states()
                states = raw.get("states") or []
                board, radar = build_flight_lists(states, center.lat, center.lon)
            except OpenSkyError:
                # Treat failure as stale data; send empty lists
                board = []
                radar = []
                stale = True

            payload = build_payload(
                center={"icao": center.icao, "lat": center.lat, "lon": center.lon},
                board=board,
                radar=radar,
                stale=stale,
            )
            await websocket.send_json(payload)
            await asyncio.sleep(settings.poll_interval_seconds)
    except WebSocketDisconnect:
        return


