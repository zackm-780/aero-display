from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class CenterState:
    icao: str
    lat: float
    lon: float


class CenterStateStore:
    """Persist and load center state to a JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> Optional[CenterState]:
        if not self._path.exists():
            return None
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return CenterState(**data)
        except Exception:
            return None

    def save(self, center: CenterState) -> None:
        if not self._path.parent.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(asdict(center)), encoding="utf-8")

