from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_radar_sweep_overlay_exists_in_html() -> None:
    html = (_repo_root() / "frontend" / "index.html").read_text(encoding="utf-8")
    assert '<div class="radar-sweep"></div>' in html


def test_update_map_receives_meta_and_staleness_label_not_live() -> None:
    js = (_repo_root() / "frontend" / "app.js").read_text(encoding="utf-8")

    # Ensure updateMap has explicit meta input used for altitude formatting.
    assert "function updateMap(center, radarFlights, meta)" in js

    # "Live" should only represent connection state, not staleness status.
    assert 'stalenessEl.textContent = "Live";' not in js


def test_board_capacity_and_scroll_contract() -> None:
    js = (_repo_root() / "frontend" / "app.js").read_text(encoding="utf-8")

    # Board should support up to 20 visible candidates with vertical scroll interaction.
    assert "const MAX_BOARD_FLIGHTS = 20;" in js
    assert "boardRotationTimer" not in js


def test_radar_label_density_and_logo_fallback_contract() -> None:
    js = (_repo_root() / "frontend" / "app.js").read_text(encoding="utf-8")
    css = (_repo_root() / "frontend" / "styles.css").read_text(encoding="utf-8")

    # Limit dense labels to top-N nearest flights, with leader lines and upright text.
    assert "const RADAR_LABEL_LIMIT" in js
    assert "radar-leader-line" in js
    assert ".radar-leader-line" in css

    # Broken logo URLs should gracefully fall back to a code badge.
    assert "onerror=" in js or "addEventListener(\"error\"" in js


def test_radar_uses_same_airborne_filter_logic_as_board() -> None:
    js = (_repo_root() / "frontend" / "app.js").read_text(encoding="utf-8")

    # Radar and board should share airborne-threshold filtering semantics.
    assert "function isAirborneFlight" in js
    assert "isAirborneFlight(f, airportElevationFt)" in js
