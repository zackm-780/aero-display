from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple


@dataclass
class AirportDatabase:
    """In-memory lookup of airports from a bundled CSV dataset."""

    csv_path: Path
    _cache: Dict[str, Tuple[float, float, str, float]] = field(default_factory=dict, init=False)

    def _ensure_loaded(self) -> None:
        if self._cache:
            return

        with self.csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ident = (row.get("ident") or "").strip().upper()
                if not ident:
                    continue
                try:
                    lat = float(row["latitude_deg"])
                    lon = float(row["longitude_deg"])
                    elevation_ft = float(row.get("elevation_ft") or 0.0)
                except (KeyError, ValueError):
                    continue
                name = (row.get("name") or "").strip()
                self._cache[ident] = (lat, lon, name, elevation_ft)

    def lookup(self, icao: str) -> Tuple[float, float, str]:
        """Return (lat, lon, name) for the given ICAO, or raise KeyError."""
        self._ensure_loaded()
        key = icao.strip().upper()
        if key not in self._cache:
            raise KeyError(f"Unknown ICAO: {icao}")
        lat, lon, name, _elevation_ft = self._cache[key]
        return lat, lon, name

    def lookup_with_elevation(self, icao: str) -> Tuple[float, float, str, float]:
        """Return (lat, lon, name, elevation_ft) for the given ICAO, or raise KeyError."""
        self._ensure_loaded()
        key = icao.strip().upper()
        if key not in self._cache:
            raise KeyError(f"Unknown ICAO: {icao}")
        return self._cache[key]

