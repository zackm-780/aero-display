from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.app.icao_lookup import AirportDatabase
from backend.app.state import CenterState, CenterStateStore
from backend.app.settings import get_settings


router = APIRouter()


class CenterRequest(BaseModel):
    icao: str


def get_state_store() -> CenterStateStore:
    settings = get_settings()
    data_dir = settings.resolved_data_dir
    return CenterStateStore(data_dir / "state.json")


def get_airport_db() -> AirportDatabase:
    # In production this will point at the bundled airports dataset
    settings = get_settings()
    csv_path = settings.resolved_data_dir / "airports.csv"
    return AirportDatabase(csv_path)


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.post("/center")
async def set_center(
    body: CenterRequest,
    store: CenterStateStore = Depends(get_state_store),
    airports: AirportDatabase = Depends(get_airport_db),
) -> dict:
    try:
        lat, lon, _name = airports.lookup(body.icao)
    except KeyError:
        raise HTTPException(status_code=400, detail="Unknown ICAO code")

    center = CenterState(icao=body.icao.upper(), lat=lat, lon=lon)
    store.save(center)
    return {"icao": center.icao, "lat": center.lat, "lon": center.lon}


def mount_static(app) -> None:
    frontend_path = get_settings().resolved_frontend_dir
    # Mount the SPA under /ui so websocket traffic to /ws does not get
    # routed through StaticFiles (which only understands HTTP requests).
    app.mount("/ui", StaticFiles(directory=str(frontend_path), html=True), name="frontend")

